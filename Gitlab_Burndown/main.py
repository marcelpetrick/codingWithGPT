"""
gitlab-milestone-burndown.py

Generate a Jira-style burndown chart (PNG) for a GitLab milestone.

Inputs
------
- Either:
  * --milestone-url https://git.example.com/group/project/-/milestones/12
  OR
  * --base-url https://git.example.com --project group/project --milestone-iid 12

Auth
----
- --token (or env GITLAB_TOKEN) is required.

Base URL behavior
-----------------
- If --milestone-url is provided and --base-url is not, base URL is inferred from milestone URL.
- If --project mode is used, --base-url (or env GITLAB_URL / CI_SERVER_URL) is required.

Important GitLab nuance
-----------------------
- The milestone URL shows the milestone IID (project-scoped, e.g. "/milestones/1").
  The GitLab API "GET /projects/:id/milestones/:milestone_id" expects the milestone *ID*,
  not the IID. Therefore we resolve the milestone by listing milestones and matching iid.

What it does
------------
- Reads milestone start/end from milestone.start_date / milestone.due_date.
  If missing, it falls back to:
    * start = earliest issue created_at (UTC date)
    * end   = max(today, latest issue updated_at) (UTC date)
- Fetches all issues currently assigned to the milestone.
- Reconstructs daily totals (UTC day buckets):
    remaining = sum over issues of:
        0 if closed (as-of that day)
        else max(estimate_seconds - spent_seconds, 0)
- Uses system notes to track estimate/spent changes over time.
- Uses resource_state_events (if accessible) to track close/reopen over time; falls back to closed_at.

Outputs
-------
- PNG at --output (default: burndown.png)
- Also prints a short textual summary to stdout.

Limitations (explicit)
----------------------
- Uses issues currently in the milestone; historical add/remove scope changes are not reliably reconstructed.
- Time tracking parsing depends on GitLab system note phrasing (generally stable, but not guaranteed).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, List, Optional, Tuple
from urllib.parse import quote, urlparse

try:
    import gitlab  # type: ignore
except ImportError:
    print("Missing dependency: python-gitlab (pip install python-gitlab)", file=sys.stderr)
    raise

UTC = timezone.utc


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr, flush=True)
    raise SystemExit(code)


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


def to_utc_day(d: datetime) -> date:
    return d.astimezone(UTC).date()


def day_start_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=UTC)


def daterange_inclusive(start_d: date, end_d: date) -> List[date]:
    if end_d < start_d:
        return []
    out: List[date] = []
    cur = start_d
    while cur <= end_d:
        out.append(cur)
        cur = cur + timedelta(days=1)
    return out


_DURATION_TOKEN = re.compile(r"(?P<num>\d+)\s*(?P<unit>w|d|h|m|s)\b", re.IGNORECASE)


def parse_duration_to_seconds(text: str) -> Optional[int]:
    if not text:
        return None
    total = 0
    found = False
    for m in _DURATION_TOKEN.finditer(text):
        found = True
        num = int(m.group("num"))
        unit = m.group("unit").lower()
        if unit == "w":
            total += num * 7 * 24 * 3600
        elif unit == "d":
            total += num * 24 * 3600
        elif unit == "h":
            total += num * 3600
        elif unit == "m":
            total += num * 60
        elif unit == "s":
            total += num
    return total if found else None


def seconds_to_hours(sec: float) -> float:
    return sec / 3600.0


@dataclass(frozen=True)
class MilestoneRef:
    project_path: str
    milestone_iid: int


def parse_milestone_url(url: str) -> MilestoneRef:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        die(f"Invalid URL: {url}")

    path = p.path.strip("/")
    if "/-/" not in path:
        die("Milestone URL does not contain '/-/' segment; cannot parse project path.")
    left, right = path.split("/-/", 1)
    parts = right.split("/")
    if len(parts) < 2 or parts[0] != "milestones":
        die("Milestone URL does not look like .../-/milestones/<iid>")

    try:
        iid = int(parts[1])
    except ValueError:
        die(f"Could not parse milestone IID from URL tail: {parts[1]}")

    project_path = left
    if not project_path:
        die("Could not parse project path from milestone URL.")
    return MilestoneRef(project_path=project_path, milestone_iid=iid)


def infer_base_url_from_any_url(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        die(f"Cannot infer base URL from invalid URL: {url}")
    return f"{p.scheme}://{p.netloc}"


@dataclass
class ChangeEvent:
    at: datetime
    kind: str  # "estimate_set", "spent_add", "spent_sub", "spent_set", "state"
    value: Any


@dataclass
class IssueTimeline:
    issue_iid: int
    title: str
    web_url: str
    created_at: datetime
    events: List[ChangeEvent]

    def sort(self) -> None:
        self.events.sort(key=lambda e: e.at)


_ESTIMATE_SET_PATTERNS = [
    re.compile(r"\bchanged time estimate to\b\s*(?P<dur>.+)$", re.IGNORECASE),
    re.compile(r"\bremoved time estimate\b", re.IGNORECASE),
    re.compile(r"\bset time estimate to\b\s*(?P<dur>.+)$", re.IGNORECASE),
]

_SPENT_PATTERNS = [
    re.compile(r"\badded\b\s*(?P<dur>.+?)\s*\bof time spent\b", re.IGNORECASE),
    re.compile(r"\bsubtracted\b\s*(?P<dur>.+?)\s*\bof time spent\b", re.IGNORECASE),
    re.compile(r"\bremoved time spent\b", re.IGNORECASE),
]


def build_client(base_url: str, token: str) -> "gitlab.Gitlab":
    gl = gitlab.Gitlab(url=base_url, private_token=token)
    gl.auth()
    return gl


def safe_iter(it: Iterable[Any]) -> Iterable[Any]:
    for x in it:
        yield x


def resolve_project(gl: "gitlab.Gitlab", project_path: str, verbose: bool = False) -> Any:
    """
    Resolve a project robustly across python-gitlab / GitLab variants:
    - Try direct path
    - Try URL-encoded path (GitLab API expects this)
    - Fallback: search and exact-match path_with_namespace
    """
    try:
        return gl.projects.get(project_path)
    except gitlab.exceptions.GitlabGetError as ex:
        if getattr(ex, "response_code", None) != 404:
            raise

    encoded = quote(project_path, safe="")
    try:
        return gl.projects.get(encoded)
    except gitlab.exceptions.GitlabGetError as ex:
        if getattr(ex, "response_code", None) != 404:
            raise

    # Fallback search
    needle = project_path.split("/")[-1]
    candidates = gl.projects.list(search=needle, simple=True, all=True, iterator=True)
    for p in safe_iter(candidates):
        pwn = getattr(p, "path_with_namespace", None)
        if pwn and str(pwn) == project_path:
            # Refetch full project by id for consistency
            return gl.projects.get(getattr(p, "id"))
    die(f"Project not found or not accessible: {project_path}")


def resolve_milestone_by_iid(project: Any, milestone_iid: int) -> Any:
    """
    Milestone URL uses IID, but the API get() uses milestone ID.
    Resolve by listing milestones and matching iid.
    """
    for ms in safe_iter(project.milestones.list(all=True, iterator=True)):
        try:
            if int(getattr(ms, "iid")) == int(milestone_iid):
                # Fetch full milestone object by ID to ensure fields are present
                ms_id = int(getattr(ms, "id"))
                return project.milestones.get(ms_id)
        except Exception:
            continue
    die(f"Milestone IID not found in project (or not accessible): iid={milestone_iid}")


def fetch_milestone_and_issues(
    gl: "gitlab.Gitlab",
    project_path: str,
    milestone_iid: int,
    verbose: bool = False,
) -> Tuple[Any, List[Any], Any]:
    project = resolve_project(gl, project_path, verbose=verbose)
    milestone = resolve_milestone_by_iid(project, milestone_iid)

    issues = list(
        safe_iter(
            project.issues.list(milestone=milestone.title, all=True, iterator=True)
        )
    )

    if verbose:
        print(f"[info] Project: {project_path}", file=sys.stderr, flush=True)
        print(f"[info] Milestone: iid={milestone_iid} — {milestone.title}", file=sys.stderr, flush=True)
        print(f"[info] Issues fetched: {len(issues)}", file=sys.stderr, flush=True)

    return milestone, issues, project


def milestone_dates_utc(milestone: Any, issues: List[Any]) -> Tuple[date, date]:
    start_d: Optional[date] = None
    end_d: Optional[date] = None

    if getattr(milestone, "start_date", None):
        try:
            start_d = datetime.fromisoformat(str(milestone.start_date)).date()
        except Exception:
            start_d = None

    if getattr(milestone, "due_date", None):
        try:
            end_d = datetime.fromisoformat(str(milestone.due_date)).date()
        except Exception:
            end_d = None

    if not start_d:
        created_dates: List[date] = []
        for iss in issues:
            dt = parse_iso8601(getattr(iss, "created_at", None))
            if dt:
                created_dates.append(to_utc_day(dt))
        start_d = min(created_dates) if created_dates else datetime.now(UTC).date()

    if not end_d:
        today = datetime.now(UTC).date()
        updated_dates: List[date] = [today]
        for iss in issues:
            dt = parse_iso8601(getattr(iss, "updated_at", None))
            if dt:
                updated_dates.append(to_utc_day(dt))
        end_d = max(updated_dates)

    if end_d < start_d:
        end_d = start_d
    return start_d, end_d


def collect_issue_timeline(project: Any, issue: Any, verbose: bool = False) -> IssueTimeline:
    iid = int(issue.iid)
    title = str(getattr(issue, "title", f"Issue {iid}"))
    web_url = str(getattr(issue, "web_url", ""))
    created_at = parse_iso8601(getattr(issue, "created_at", None)) or datetime.now(UTC)

    events: List[ChangeEvent] = []

    try:
        notes = list(safe_iter(issue.notes.list(all=True, iterator=True)))
    except Exception as ex:
        notes = []
        if verbose:
            print(f"[warn] Could not fetch notes for issue #{iid}: {ex}", file=sys.stderr, flush=True)

    for n in notes:
        body = str(getattr(n, "body", "") or "")
        created = parse_iso8601(getattr(n, "created_at", None))
        if not created:
            continue

        system_flag = getattr(n, "system", None)
        if system_flag is False:
            continue

        matched_est = False
        for pat in _ESTIMATE_SET_PATTERNS:
            m = pat.search(body)
            if not m:
                continue
            matched_est = True
            if "removed time estimate" in body.lower():
                events.append(ChangeEvent(at=created, kind="estimate_set", value=0))
            else:
                dur = (m.groupdict().get("dur") or "").strip()
                sec = parse_duration_to_seconds(dur)
                if sec is not None:
                    events.append(ChangeEvent(at=created, kind="estimate_set", value=sec))
            break

        if matched_est:
            continue

        for pat in _SPENT_PATTERNS:
            m = pat.search(body)
            if not m:
                continue
            low = body.lower()
            if "removed time spent" in low:
                events.append(ChangeEvent(at=created, kind="spent_set", value=0))
            elif low.startswith("added") or " added " in low:
                dur = (m.groupdict().get("dur") or "").strip()
                sec = parse_duration_to_seconds(dur)
                if sec is not None:
                    events.append(ChangeEvent(at=created, kind="spent_add", value=sec))
            elif low.startswith("subtracted") or " subtracted " in low:
                dur = (m.groupdict().get("dur") or "").strip()
                sec = parse_duration_to_seconds(dur)
                if sec is not None:
                    events.append(ChangeEvent(at=created, kind="spent_sub", value=sec))
            break

    try:
        rse = list(safe_iter(issue.resource_state_events.list(all=True, iterator=True)))
        for ev in rse:
            created = parse_iso8601(getattr(ev, "created_at", None))
            if not created:
                continue
            state = str(getattr(ev, "state", "") or "")
            if state in ("opened", "closed"):
                events.append(ChangeEvent(at=created, kind="state", value=state))
    except Exception:
        closed_at = parse_iso8601(getattr(issue, "closed_at", None))
        if closed_at:
            events.append(ChangeEvent(at=closed_at, kind="state", value="closed"))

    tl = IssueTimeline(
        issue_iid=iid,
        title=title,
        web_url=web_url,
        created_at=created_at,
        events=events,
    )
    tl.sort()
    return tl


def compute_daily_burndown(
    timelines: List[IssueTimeline],
    start_d: date,
    end_d: date,
) -> Tuple[List[date], List[float], List[float]]:
    days = daterange_inclusive(start_d, end_d)
    remaining_hours: List[float] = []
    scope_hours: List[float] = []

    for d in days:
        cutoff = day_start_utc(d) + timedelta(days=1)

        total_remaining_sec = 0
        total_scope_sec = 0

        for tl in timelines:
            est = 0
            spent = 0
            state = "opened"

            for ev in tl.events:
                if ev.at >= cutoff:
                    break
                if ev.kind == "estimate_set":
                    est = int(ev.value)
                elif ev.kind == "spent_set":
                    spent = int(ev.value)
                elif ev.kind == "spent_add":
                    spent += int(ev.value)
                elif ev.kind == "spent_sub":
                    spent -= int(ev.value)
                    if spent < 0:
                        spent = 0
                elif ev.kind == "state":
                    state = str(ev.value)

            total_scope_sec += max(est, 0)
            if state == "closed":
                total_remaining_sec += 0
            else:
                total_remaining_sec += max(est - spent, 0)

        remaining_hours.append(seconds_to_hours(total_remaining_sec))
        scope_hours.append(seconds_to_hours(total_scope_sec))

    return days, remaining_hours, scope_hours


def render_png(
    days: List[date],
    remaining_hours: List[float],
    scope_hours: List[float],
    title: str,
    output_path: str,
    width_px: int,
    height_px: int,
    dpi: int,
) -> None:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import MaxNLocator  # type: ignore

    C_BG = "#000000"
    C_GRID = "#303030"
    C_TEXT = "#FFFFFF"
    C_REMAIN = "#55FFFF"
    C_IDEAL = "#FF55FF"
    C_SCOPE = "#FFFF55"

    figsize = (width_px / dpi, height_px / dpi)

    fig = plt.figure(figsize=figsize, dpi=dpi, facecolor=C_BG)
    ax = fig.add_subplot(1, 1, 1, facecolor=C_BG)

    x = list(range(len(days)))
    x_labels = [d.isoformat() for d in days]

    ideal_start = remaining_hours[0] if remaining_hours else 0.0
    n = max(1, len(days) - 1)
    ideal = [ideal_start * (1 - i / n) for i in range(len(days))]

    ax.step(x, remaining_hours, where="post", linewidth=3.0, label="Remaining", color=C_REMAIN)
    ax.plot(x, ideal, linewidth=2.0, linestyle="--", label="Ideal", color=C_IDEAL)
    ax.plot(x, scope_hours, linewidth=2.0, linestyle=":", label="Scope (est.)", color=C_SCOPE)

    ax.set_title(title, color=C_TEXT, fontsize=20, fontfamily="DejaVu Sans Mono", pad=16)
    ax.set_xlabel("Day (UTC)", color=C_TEXT, fontsize=14, fontfamily="DejaVu Sans Mono", labelpad=10)
    ax.set_ylabel("Hours", color=C_TEXT, fontsize=14, fontfamily="DejaVu Sans Mono", labelpad=10)

    ax.grid(True, which="major", linestyle="-", linewidth=0.8, color=C_GRID, alpha=0.8)

    for spine in ax.spines.values():
        spine.set_color(C_TEXT)

    ax.tick_params(axis="x", colors=C_TEXT, labelsize=10)
    ax.tick_params(axis="y", colors=C_TEXT, labelsize=12)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=10, integer=False))

    if len(x) > 24:
        step = max(1, len(x) // 12)
    else:
        step = 1
    shown = set(range(0, len(x), step))
    ax.set_xticks([i for i in x if i in shown])
    ax.set_xticklabels(
        [x_labels[i] for i in x if i in shown],
        rotation=45,
        ha="right",
        fontfamily="DejaVu Sans Mono",
    )

    leg = ax.legend(loc="upper right", frameon=True, fontsize=12)
    leg.get_frame().set_facecolor(C_BG)
    leg.get_frame().set_edgecolor(C_TEXT)
    for text in leg.get_texts():
        text.set_color(C_TEXT)
        text.set_fontfamily("DejaVu Sans Mono")

    fig.tight_layout()
    fig.savefig(output_path, facecolor=C_BG)
    plt.close(fig)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a CGA-styled burndown chart PNG for a GitLab milestone.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    p.add_argument(
        "--base-url",
        default=os.environ.get("GITLAB_URL") or os.environ.get("CI_SERVER_URL"),
        help="GitLab base URL, e.g. https://git.example.com (env: GITLAB_URL or CI_SERVER_URL). "
             "Not required if --milestone-url is used.",
    )
    p.add_argument(
        "--token",
        default=os.environ.get("GITLAB_TOKEN"),
        help="Personal Access Token (env: GITLAB_TOKEN)",
    )

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--milestone-url", help="Milestone URL like https://.../group/project/-/milestones/12")
    g.add_argument("--project", help="Project path like group/project (use with --milestone-iid)")

    p.add_argument("--milestone-iid", type=int, default=None, help="Milestone IID (required if --project is used)")

    p.add_argument("--output", default="burndown.png", help="Output PNG path")
    p.add_argument("--width", type=int, default=2400, help="PNG width in pixels")
    p.add_argument("--height", type=int, default=1350, help="PNG height in pixels")
    p.add_argument("--dpi", type=int, default=200, help="PNG DPI")
    p.add_argument("--verbose", action="store_true", help="Verbose stderr logging")

    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if not args.token:
        die("Error: --token (or GITLAB_TOKEN) must be provided.")

    base_url = args.base_url
    project_path: str
    milestone_iid: int

    if args.milestone_url:
        base_url = base_url or infer_base_url_from_any_url(args.milestone_url)
        ref = parse_milestone_url(args.milestone_url)
        project_path = ref.project_path
        milestone_iid = ref.milestone_iid
    else:
        if not base_url:
            die("Error: --base-url (or GITLAB_URL/CI_SERVER_URL) must be provided when not using --milestone-url.")
        if not args.project or not args.milestone_iid:
            die("When using --project, you must also provide --milestone-iid.")
        project_path = args.project
        milestone_iid = int(args.milestone_iid)

    gl = build_client(base_url, args.token)
    milestone, issues, project = fetch_milestone_and_issues(gl, project_path, milestone_iid, verbose=args.verbose)

    start_d, end_d = milestone_dates_utc(milestone, issues)

    if args.verbose:
        print(f"[info] Base URL: {base_url}", file=sys.stderr, flush=True)
        print(f"[info] Horizon: {start_d.isoformat()} → {end_d.isoformat()} (UTC dates)", file=sys.stderr, flush=True)

    timelines: List[IssueTimeline] = []
    for iss in issues:
        full = project.issues.get(iss.iid)
        timelines.append(collect_issue_timeline(project, full, verbose=args.verbose))

    days, remaining_hours, scope_hours = compute_daily_burndown(timelines, start_d, end_d)

    ms_title = str(getattr(milestone, "title", f"Milestone {milestone_iid}"))
    chart_title = f"Burndown — {project_path} — {ms_title}"

    render_png(
        days=days,
        remaining_hours=remaining_hours,
        scope_hours=scope_hours,
        title=chart_title,
        output_path=args.output,
        width_px=int(args.width),
        height_px=int(args.height),
        dpi=int(args.dpi),
    )

    print(f"project: {project_path}")
    print(f"milestone: {milestone_iid} — {ms_title}")
    print(f"horizon_utc: {start_d.isoformat()} .. {end_d.isoformat()} (inclusive)")
    print(f"issues: {len(issues)}")
    if remaining_hours:
        print(f"remaining_hours_start: {remaining_hours[0]:.2f}")
        print(f"remaining_hours_end:   {remaining_hours[-1]:.2f}")
    print(f"png: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
