"""
gitlab-milestone-burndown.py

Generate a Jira-style burndown chart (PNG) for a GitLab milestone.

Inputs
------
- Either:
  * --milestone-url https://git.example.com/group/project/-/milestones/12
  OR
  * --project group/project --milestone-iid 12

Auth
----
- --base-url and --token (or env GITLAB_URL / CI_SERVER_URL and GITLAB_TOKEN)

What it does
------------
- Reads milestone start/end from milestone.start_date / milestone.due_date.
  If missing, it falls back to:
    * start = earliest issue created_at (date)
    * end   = latest of (milestone due_date, today, or last activity) (date)
- Fetches all issues currently assigned to the milestone.
- Reconstructs daily totals (UTC day buckets):
    remaining = sum over issues of:
        0 if closed (as-of that day)
        else max(estimate_seconds - spent_seconds, 0)
- Uses system notes to track estimate/spent changes over time.
- Uses resource_state_events (if accessible) to track close/reopen over time.

Outputs
-------
- PNG at --output (default: burndown.png)
- Also prints a short textual summary to stdout.

Limitations (explicit)
----------------------
- This uses issues *currently* in the milestone; it does not reliably detect historical
  add/remove-to-milestone scope changes unless your GitLab instance emits those events
  in a parseable way for issues (varies by version/config).
- Time tracking parsing depends on GitLab’s system note phrasing (stable in recent versions,
  but not guaranteed across heavily customized deployments).

"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import gitlab  # type: ignore
except ImportError:
    print("Missing dependency: python-gitlab (pip install python-gitlab)", file=sys.stderr)
    raise

# Matplotlib is intentionally imported lazily in render() so headless environments behave better.


# ----------------------------
# Utility: time & parsing
# ----------------------------

UTC = timezone.utc


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = value.strip()
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
    """
    Parse GitLab-ish duration strings like:
      "1h", "2h 30m", "3d", "1w 2d 4h", "45m"
    into seconds.
    """
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


# ----------------------------
# GitLab parsing: milestone URL
# ----------------------------

@dataclass(frozen=True)
class MilestoneRef:
    project_path: str  # e.g. group/subgroup/project
    milestone_iid: int  # from URL tail


def parse_milestone_url(url: str) -> MilestoneRef:
    """
    Expect URL like:
      https://git.example.com/group/project/-/milestones/12
      https://git.example.com/group/subgroup/project/-/milestones/12

    Returns (project_path, milestone_iid)
    """
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        die(f"Invalid URL: {url}")

    # Path pattern: /<project_path>/-/milestones/<iid>
    # Split on "/-/" first.
    path = p.path.strip("/")
    if "/-/" not in path:
        die("Milestone URL does not contain '/-/' segment; cannot parse project path.")
    left, right = path.split("/-/", 1)
    # right should start with milestones/<iid>
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


# ----------------------------
# GitLab: fetch & timeline reconstruction
# ----------------------------

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
    # Typical system notes in GitLab:
    # "changed time estimate to 2h"
    re.compile(r"\bchanged time estimate to\b\s*(?P<dur>.+)$", re.IGNORECASE),
    # "removed time estimate"
    re.compile(r"\bremoved time estimate\b", re.IGNORECASE),
    # "set time estimate to 1h" (older/variant phrasing)
    re.compile(r"\bset time estimate to\b\s*(?P<dur>.+)$", re.IGNORECASE),
]

_SPENT_PATTERNS = [
    # "added 1h of time spent"
    re.compile(r"\badded\b\s*(?P<dur>.+?)\s*\bof time spent\b", re.IGNORECASE),
    # "subtracted 30m of time spent"
    re.compile(r"\bsubtracted\b\s*(?P<dur>.+?)\s*\bof time spent\b", re.IGNORECASE),
    # "removed time spent"
    re.compile(r"\bremoved time spent\b", re.IGNORECASE),
]


def build_client(base_url: str, token: str) -> "gitlab.Gitlab":
    gl = gitlab.Gitlab(url=base_url, private_token=token)
    gl.auth()
    return gl


def safe_iter(iterator_or_list: Iterable[Any]) -> Iterable[Any]:
    # python-gitlab returns either a list or a generator depending on iterator=True/all=True.
    for x in iterator_or_list:
        yield x


def fetch_milestone_and_issues(
    gl: "gitlab.Gitlab",
    project_path: str,
    milestone_iid: int,
    verbose: bool = False,
) -> Tuple[Any, List[Any], Any]:
    project = gl.projects.get(project_path)
    milestone = project.milestones.get(milestone_iid)

    # GitLab Issues API uses milestone title for filtering in many versions.
    # The milestone object has .title; use that for listing issues.
    issues = list(
        safe_iter(
            project.issues.list(milestone=milestone.title, all=True, iterator=True)
        )
    )

    if verbose:
        print(f"[info] Project: {project_path}", file=sys.stderr)
        print(f"[info] Milestone: {milestone_iid} — {milestone.title}", file=sys.stderr)
        print(f"[info] Issues fetched: {len(issues)}", file=sys.stderr)

    return milestone, issues, project


def milestone_dates_utc(milestone: Any, issues: List[Any]) -> Tuple[date, date]:
    """
    Determine start/end dates for the burndown horizon.
    Prefer milestone.start_date / milestone.due_date (date strings, YYYY-MM-DD).
    Fallbacks are conservative but deterministic.
    """
    start_d: Optional[date] = None
    end_d: Optional[date] = None

    # Milestone provides date strings
    if getattr(milestone, "start_date", None):
        try:
            start_d = datetime.fromisoformat(milestone.start_date).date()
        except Exception:
            start_d = None

    if getattr(milestone, "due_date", None):
        try:
            end_d = datetime.fromisoformat(milestone.due_date).date()
        except Exception:
            end_d = None

    # Fallbacks
    if not start_d:
        # earliest issue created_at
        created_dates: List[date] = []
        for iss in issues:
            dt = parse_iso8601(getattr(iss, "created_at", None))
            if dt:
                created_dates.append(to_utc_day(dt))
        start_d = min(created_dates) if created_dates else datetime.now(UTC).date()

    if not end_d:
        # at least through today; optionally extend to last updated issue day
        today = datetime.now(UTC).date()
        updated_dates: List[date] = [today]
        for iss in issues:
            dt = parse_iso8601(getattr(iss, "updated_at", None))
            if dt:
                updated_dates.append(to_utc_day(dt))
        end_d = max(updated_dates)

    # Ensure sane ordering
    if end_d < start_d:
        end_d = start_d
    return start_d, end_d


def collect_issue_timeline(project: Any, issue: Any, verbose: bool = False) -> IssueTimeline:
    iid = int(issue.iid)
    title = str(getattr(issue, "title", f"Issue {iid}"))
    web_url = str(getattr(issue, "web_url", ""))
    created_at = parse_iso8601(getattr(issue, "created_at", None)) or datetime.now(UTC)

    events: List[ChangeEvent] = []

    # 1) Estimate/spent changes from notes (system notes are key)
    # Notes are usually in reverse chronological; we sort later.
    try:
        notes = list(safe_iter(issue.notes.list(all=True, iterator=True)))
    except Exception as ex:
        notes = []
        if verbose:
            print(f"[warn] Could not fetch notes for issue !{iid}: {ex}", file=sys.stderr)

    for n in notes:
        body = str(getattr(n, "body", "") or "")
        created = parse_iso8601(getattr(n, "created_at", None))
        if not created:
            continue

        # We only parse likely system notes; but some instances omit the "system" flag.
        # So: if system attribute exists, require it; else parse anyway.
        system_flag = getattr(n, "system", None)
        if system_flag is False:
            continue

        # Estimate
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

        # Spent
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

    # 2) State changes (closed/reopened) from resource_state_events if possible
    # This is more accurate than only closed_at.
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
        # Fallback: closed_at only (cannot detect reopen)
        closed_at = parse_iso8601(getattr(issue, "closed_at", None))
        if closed_at:
            events.append(ChangeEvent(at=closed_at, kind="state", value="closed"))

    tl = IssueTimeline(issue_iid=iid, title=title, web_url=web_url, created_at=created_at, events=events)
    tl.sort()
    return tl


def compute_daily_burndown(
    timelines: List[IssueTimeline],
    start_d: date,
    end_d: date,
) -> Tuple[List[date], List[float], List[float]]:
    """
    Returns:
      days: list of dates (inclusive)
      remaining_hours: remaining work at end-of-day (hours)
      scope_hours: total estimated scope at end-of-day (hours) (useful as reference)
    """
    days = daterange_inclusive(start_d, end_d)

    remaining_hours: List[float] = []
    scope_hours: List[float] = []

    for d in days:
        cutoff = day_start_utc(d) + timedelta(days=1)  # end of day (exclusive)

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

            # Remaining definition (pragmatic):
            # - closed => 0 from that day onward
            # - open   => max(est - spent, 0)
            total_scope_sec += max(est, 0)
            if state == "closed":
                total_remaining_sec += 0
            else:
                total_remaining_sec += max(est - spent, 0)

        remaining_hours.append(seconds_to_hours(total_remaining_sec))
        scope_hours.append(seconds_to_hours(total_scope_sec))

    return days, remaining_hours, scope_hours


# ----------------------------
# Rendering: CGA style PNG
# ----------------------------

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
    import matplotlib.pyplot as plt  # noqa
    from matplotlib.ticker import MaxNLocator  # noqa

    # CGA-inspired palette (classic 16-color feel; tuned for dark background)
    # Primary chart colors:
    C_BG = "#000000"
    C_GRID = "#303030"
    C_TEXT = "#FFFFFF"
    C_REMAIN = "#55FFFF"  # bright cyan
    C_IDEAL = "#FF55FF"   # bright magenta
    C_SCOPE = "#FFFF55"   # bright yellow

    # Size
    figsize = (width_px / dpi, height_px / dpi)

    fig = plt.figure(figsize=figsize, dpi=dpi, facecolor=C_BG)
    ax = fig.add_subplot(1, 1, 1, facecolor=C_BG)

    # X axis labels
    x = list(range(len(days)))
    x_labels = [d.isoformat() for d in days]

    # Ideal line: from initial remaining to 0 over the horizon
    if remaining_hours:
        ideal_start = remaining_hours[0]
    else:
        ideal_start = 0.0
    n = max(1, len(days) - 1)
    ideal = [ideal_start * (1 - i / n) for i in range(len(days))]

    # Plot
    ax.step(x, remaining_hours, where="post", linewidth=3.0, label="Remaining", color=C_REMAIN)
    ax.plot(x, ideal, linewidth=2.0, linestyle="--", label="Ideal", color=C_IDEAL)
    ax.plot(x, scope_hours, linewidth=2.0, linestyle=":", label="Scope (est.)", color=C_SCOPE)

    # Title & styling
    ax.set_title(title, color=C_TEXT, fontsize=20, fontfamily="DejaVu Sans Mono", pad=16)
    ax.set_xlabel("Day (UTC)", color=C_TEXT, fontsize=14, fontfamily="DejaVu Sans Mono", labelpad=10)
    ax.set_ylabel("Hours", color=C_TEXT, fontsize=14, fontfamily="DejaVu Sans Mono", labelpad=10)

    ax.grid(True, which="major", linestyle="-", linewidth=0.8, color=C_GRID, alpha=0.8)

    for spine in ax.spines.values():
        spine.set_color(C_TEXT)

    ax.tick_params(axis="x", colors=C_TEXT, labelsize=10)
    ax.tick_params(axis="y", colors=C_TEXT, labelsize=12)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=10, integer=False))

    # Reduce x labels to something readable
    if len(x) > 24:
        step = max(1, len(x) // 12)
    else:
        step = 1
    shown = set(range(0, len(x), step))
    ax.set_xticks([i for i in x if i in shown])
    ax.set_xticklabels([x_labels[i] for i in x if i in shown], rotation=45, ha="right", fontfamily="DejaVu Sans Mono")

    # Legend
    leg = ax.legend(loc="upper right", frameon=True, fontsize=12)
    leg.get_frame().set_facecolor(C_BG)
    leg.get_frame().set_edgecolor(C_TEXT)
    for text in leg.get_texts():
        text.set_color(C_TEXT)
        text.set_fontfamily("DejaVu Sans Mono")

    fig.tight_layout()
    fig.savefig(output_path, facecolor=C_BG)
    plt.close(fig)


# ----------------------------
# CLI
# ----------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a CGA-styled burndown chart PNG for a GitLab milestone.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    p.add_argument("--base-url", default=os.environ.get("GITLAB_URL") or os.environ.get("CI_SERVER_URL"),
                   help="GitLab base URL, e.g. https://git.example.com (env: GITLAB_URL or CI_SERVER_URL)")
    p.add_argument("--token", default=os.environ.get("GITLAB_TOKEN"),
                   help="Personal Access Token (env: GITLAB_TOKEN)")

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--milestone-url", help="Milestone URL like https://.../group/project/-/milestones/12")
    g.add_argument("--project", help="Project path like group/project (use with --milestone-iid)")

    p.add_argument("--milestone-iid", type=int, default=None,
                   help="Milestone IID (required if --project is used)")

    p.add_argument("--output", default="burndown.png", help="Output PNG path")
    p.add_argument("--width", type=int, default=2400, help="PNG width in pixels")
    p.add_argument("--height", type=int, default=1350, help="PNG height in pixels")
    p.add_argument("--dpi", type=int, default=200, help="PNG DPI")
    p.add_argument("--verbose", action="store_true", help="Verbose stderr logging")

    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if not args.base_url:
        die("Error: --base-url (or GITLAB_URL/CI_SERVER_URL) must be provided.")
    if not args.token:
        die("Error: --token (or GITLAB_TOKEN) must be provided.")

    if args.milestone_url:
        ref = parse_milestone_url(args.milestone_url)
        project_path = ref.project_path
        milestone_iid = ref.milestone_iid
    else:
        if not args.project or not args.milestone_iid:
            die("When using --project, you must also provide --milestone-iid.")
        project_path = args.project
        milestone_iid = int(args.milestone_iid)

    gl = build_client(args.base_url, args.token)
    milestone, issues, project = fetch_milestone_and_issues(gl, project_path, milestone_iid, verbose=args.verbose)

    start_d, end_d = milestone_dates_utc(milestone, issues)

    if args.verbose:
        print(f"[info] Horizon: {start_d.isoformat()} → {end_d.isoformat()} (UTC dates)", file=sys.stderr)

    timelines: List[IssueTimeline] = []
    for iss in issues:
        # Ensure we have a full issue object (python-gitlab list items are often partial)
        full = project.issues.get(iss.iid)
        timelines.append(collect_issue_timeline(project, full, verbose=args.verbose))

    days, remaining_hours, scope_hours = compute_daily_burndown(timelines, start_d, end_d)

    # Title
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

    # Minimal stdout summary (useful for pipes/CI logs)
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
