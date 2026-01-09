#!/usr/bin/env python3
"""
gitlab-activity-daily.py

Fetch a GitLab user's Activity Stream ("events") for a given time window,
bucket the events into UTC day blocks (00:00–24:00), and print to stdout in an
LLM-friendly format (Markdown) or structured JSON.

This script is intentionally designed as a data-extraction stage you can pipe
into later processing (e.g., LLM summarization).

Features
--------
- Auth via Personal Access Token (PAT) using python-gitlab
- User selection:
  - Default: current authenticated user
  - Optional: --user <username>
- Time window:
  - --start / --end (ISO-8601)
  - Default: last 10 days ending "now" (UTC)
- Output:
  - --format llm-md (default): Markdown blocks per day
  - --format json: grouped JSON object

Notes on time handling
----------------------
- All timestamps are normalized to UTC.
- Buckets are UTC calendar days: [YYYY-MM-DD 00:00:00Z, next-day 00:00:00Z).

Compatibility
-------------
GitLab and python-gitlab versions differ in which query parameters the Events API
accepts (e.g., "after", "before"). This script attempts server-side filtering when
possible and always enforces the window client-side.

Example
-------
python3 main.py \
  --base-url https://git.example.com \
  --token "$GITLAB_TOKEN" \
  --user mpetrick \
  --start 2026-01-01T00:00:00Z \
  --end   2026-01-11T00:00:00Z \
  --format llm-md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import gitlab  # type: ignore
except ImportError:  # pragma: no cover
    print(
        "This script requires 'python-gitlab'. Install it with: pip install python-gitlab",
        file=sys.stderr,
    )
    raise


PRINT_LOCK = threading.Lock()


def eprint(msg: str) -> None:
    """Print a message to stderr in a thread-safe manner."""
    with PRINT_LOCK:
        print(msg, file=sys.stderr, flush=True)


def die(msg: str, code: int = 2) -> None:
    """Exit the program with an error message."""
    eprint(msg)
    raise SystemExit(code)


def safe_get(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely traverse nested dicts.

    Parameters
    ----------
    d:
        Root dictionary.
    *keys:
        Path of keys to traverse.
    default:
        Value returned if any key is missing.

    Returns
    -------
    Any
        The nested value, or default.
    """
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """
    Parse an ISO-8601 datetime into a timezone-aware UTC datetime.

    Accepts timestamps ending in 'Z' and offsets like '+01:00'.

    Returns None if parsing fails.
    """
    if not value:
        return None

    s = value.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            # Treat naive input as UTC to avoid ambiguity.
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def fmt_utc(dt: datetime) -> str:
    """Format a datetime as ISO-8601 in UTC with 'Z' suffix."""
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def day_start_utc(dt: datetime) -> datetime:
    """Return the UTC day start (00:00:00) for the date of dt."""
    u = dt.astimezone(timezone.utc)
    return datetime(u.year, u.month, u.day, 0, 0, 0, tzinfo=timezone.utc)


def human_td(delta: timedelta) -> str:
    """Render a timedelta into a short human-friendly string."""
    seconds = int(abs(delta.total_seconds()))
    parts: List[str] = []
    for unit, div in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= div:
            parts.append(f"{seconds // div}{unit}")
            seconds %= div
    parts.append(f"{seconds}s")
    return "".join(parts)


@dataclass(frozen=True)
class TimeWindow:
    """A half-open time window [start, end) in UTC."""
    start: datetime
    end: datetime

    def validate(self) -> None:
        """Validate window integrity."""
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("TimeWindow must be timezone-aware.")
        if self.end <= self.start:
            raise ValueError("End must be after start.")

    def contains(self, dt: datetime) -> bool:
        """Return True if dt is in [start, end)."""
        u = dt.astimezone(timezone.utc)
        return self.start <= u < self.end


def build_client(base_url: str, token: str, verbose: bool = False) -> "gitlab.Gitlab":
    """
    Authenticate and return a python-gitlab client.

    Parameters
    ----------
    base_url:
        GitLab instance URL, e.g. https://git.example.com
    token:
        Personal Access Token.
    verbose:
        Whether to log details to stderr.

    Returns
    -------
    gitlab.Gitlab
        Authenticated client.
    """
    gl = gitlab.Gitlab(url=base_url, private_token=token)
    gl.auth()

    if verbose:
        me = gl.user
        eprint(f"Authenticated as: {getattr(me, 'username', '?')} ({getattr(me, 'name', '?')})")

    return gl


def resolve_user(gl: "gitlab.Gitlab", username: Optional[str], verbose: bool = False) -> Tuple[int, str, str]:
    """
    Resolve the target user.

    If username is None, use the authenticated user. Otherwise look up by username.

    Returns
    -------
    (user_id, username, display_name)
    """
    if not username:
        me = gl.user
        uid = int(getattr(me, "id"))
        uname = str(getattr(me, "username", "unknown"))
        name = str(getattr(me, "name", uname))
        if verbose:
            eprint(f"Using current user: {uname} (id={uid})")
        return uid, uname, name

    # Lookup by username. python-gitlab supports list(username=...).
    users = gl.users.list(username=username)  # type: ignore[attr-defined]
    if not users:
        die(f"User not found for --user '{username}'. Consider verifying the username or adding a user-id option.")
    u = users[0]
    uid = int(getattr(u, "id"))
    uname = str(getattr(u, "username", username))
    name = str(getattr(u, "name", uname))
    if verbose:
        eprint(f"Resolved user: {uname} (id={uid})")
    return uid, uname, name


def iter_user_events(
    gl: "gitlab.Gitlab",
    user_id: int,
    window: TimeWindow,
    verbose: bool = False,
) -> Iterable[Dict[str, Any]]:
    """
    Iterate raw event dicts for the given user, best-effort applying server-side filtering.

    The GitLab Events API frequently returns events in reverse chronological order.
    We stop early once we are clearly past the start boundary (based on created_at).

    Yields
    ------
    Dict[str, Any]
        Raw event attributes from python-gitlab.
    """
    user = gl.users.get(user_id)  # type: ignore[attr-defined]

    # Attempt server-side time filtering if supported by the target GitLab/python-gitlab combo.
    # If not supported, fall back to client-side filtering only.
    params: Dict[str, Any] = {"per_page": 100, "iterator": True}

    # These are known in many GitLab versions, but not universal.
    # We keep them as date-only (YYYY-MM-DD) in accordance with GitLab conventions.
    after_date = window.start.date().isoformat()
    before_date = window.end.date().isoformat()

    # Try to pass after/before; if python-gitlab rejects them, we retry without.
    def _list_events(extra: Dict[str, Any]) -> Iterable[Any]:
        return user.events.list(**extra)  # type: ignore[no-any-return]

    for attempt in (1, 2):
        try:
            extra = dict(params)
            extra.update({"after": after_date})
            events_iter = _list_events(extra)
            if verbose:
                eprint(f"Listing events with server-side filter after={after_date} (no before)")
            break
        except TypeError:
            if attempt == 2:
                raise
            if verbose:
                eprint("Events API does not accept after; using client-side filtering only.")
            events_iter = _list_events(params)
            break
        except Exception as ex:
            if verbose:
                eprint(f"Server-side filter attempt failed ({ex}); using client-side filtering only.")
            events_iter = _list_events(params)
            break

    # Client-side enforce time window and stop early if possible.
    # Many GitLab instances return newest first; if so we can stop once created_at < window.start.
    saw_any = False
    newest_first_assumed = True

    for ev in events_iter:
        saw_any = True
        raw = ev._attrs if hasattr(ev, "_attrs") else dict(ev)  # type: ignore[arg-type]
        created = parse_iso8601(raw.get("created_at"))

        if not created:
            # If there's no timestamp, yield it (rare) but it won't bucket nicely.
            yield raw
            continue

        created_u = created.astimezone(timezone.utc)

        # Enforce [start, end)
        if created_u < window.start:
            if newest_first_assumed:
                # We are past the range; stop early.
                break
            continue
        if created_u >= window.end:
            # Too new (should be rare if "end=now"), skip it.
            continue

        yield raw

    if verbose and not saw_any:
        eprint("No events returned by API call (empty stream or insufficient permissions).")


def normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a GitLab event payload into a stable schema.

    Parameters
    ----------
    raw:
        Raw event dict from python-gitlab.

    Returns
    -------
    Dict[str, Any]
        Normalized event.
    """
    created = parse_iso8601(raw.get("created_at"))
    created_s = fmt_utc(created) if created else None

    author_username = safe_get(raw, "author", "username", default=None)
    author_name = safe_get(raw, "author", "name", default=None)
    author_id = safe_get(raw, "author", "id", default=None)

    project_id = safe_get(raw, "project_id", default=None) or safe_get(raw, "project", "id", default=None)
    project_path = safe_get(raw, "project", "path_with_namespace", default=None) or safe_get(raw, "project", "path", default=None)

    # GitLab events fields vary; try common ones.
    action_name = raw.get("action_name") or raw.get("action") or raw.get("push_action") or raw.get("event_type")
    target_type = raw.get("target_type") or raw.get("object_kind")
    target_title = raw.get("target_title") or raw.get("note") or raw.get("title") or raw.get("target_name")
    target_id = raw.get("target_id") or raw.get("id")  # target_id is common; fallback id is imperfect
    target_iid = raw.get("target_iid")

    # Some events include a target URL or noteable URL; keep best effort.
    url = raw.get("url") or raw.get("target_url") or raw.get("noteable_url") or safe_get(raw, "target", "web_url", default=None)

    return {
        "event_id": raw.get("id"),
        "created_at": created_s,
        "author": {"id": author_id, "username": author_username, "name": author_name},
        "action": action_name,
        "target": {
            "type": target_type,
            "id": target_id,
            "iid": target_iid,
            "title": target_title,
        },
        "project": {
            "id": project_id,
            "path_with_namespace": project_path,
        },
        "url": url,
    }


def bucket_by_day(
    events: List[Dict[str, Any]],
    window: TimeWindow,
) -> List[Dict[str, Any]]:
    """
    Bucket normalized events into UTC day blocks within the given window.

    Returns a list of day objects:
      {
        "date": "YYYY-MM-DD",
        "start": "...Z",
        "end": "...Z",
        "count": N,
        "events": [...]
      }
    """
    window.validate()

    # Build all day buckets covering the window
    first_day = day_start_utc(window.start)
    last_day = day_start_utc(window.end - timedelta(microseconds=1))

    buckets: Dict[str, Dict[str, Any]] = {}

    d = first_day
    while d <= last_day:
        nxt = d + timedelta(days=1)
        key = d.date().isoformat()
        buckets[key] = {
            "date": key,
            "start": fmt_utc(d),
            "end": fmt_utc(nxt),
            "count": 0,
            "events": [],
        }
        d = nxt

    # Assign events to buckets
    for ev in events:
        created = parse_iso8601(ev.get("created_at"))
        if not created:
            # If no timestamp, skip bucketing (or attach to a special bucket).
            continue
        if not window.contains(created):
            continue
        key = created.astimezone(timezone.utc).date().isoformat()
        bucket = buckets.get(key)
        if bucket is None:
            continue
        bucket["events"].append(ev)

    # Sort events within each bucket by created_at ascending for chronological readability
    for b in buckets.values():
        b["events"].sort(key=lambda x: x.get("created_at") or "")

        b["count"] = len(b["events"])

    # Return buckets in ascending date order
    return [buckets[k] for k in sorted(buckets.keys())]


def render_llm_md(meta: Dict[str, Any], days: List[Dict[str, Any]]) -> None:
    """
    Render day buckets as LLM-friendly Markdown to stdout.
    """
    print("# GitLab Activity Stream (Daily Buckets)")
    print()
    print(f"- User: {meta.get('user_username')} ({meta.get('user_name')})")
    print(f"- Host: {meta.get('base_url')}")
    print(f"- Window (UTC): {meta.get('start')} — {meta.get('end')}")
    print(f"- Generated at (UTC): {meta.get('generated_at')}")
    print()

    for day in days:
        print(f"## {day['date']} (UTC)")
        print(f"Window: {day['start']} — {day['end']}")
        if day["count"] == 0:
            print()
            print("_No events._")
            print()
            continue

        print()
        for ev in day["events"]:
            created = ev.get("created_at") or ""
            t = ""
            if created.endswith("Z") and "T" in created:
                t = created.split("T", 1)[1].replace("Z", "Z")
            action = ev.get("action") or "-"
            target = ev.get("target") or {}
            target_type = target.get("type") or "-"
            title = (target.get("title") or "").strip()
            project = ev.get("project") or {}
            proj = project.get("path_with_namespace") or "-"
            url = ev.get("url") or ""

            # A concise, stable line for LLM ingestion:
            # - HH:MM:SSZ | TargetType | action | project/path | title | url
            # Truncate title lightly to keep lines manageable.
            if len(title) > 180:
                title = title[:177] + "..."
            print(f"- {t:>9} | {target_type} | {action} | {proj} | {title} | {url}")

        print()
        print(f"Count: {day['count']}")
        print()


def render_json(meta: Dict[str, Any], days: List[Dict[str, Any]]) -> None:
    """
    Render the full result as JSON to stdout.
    """
    out = {"meta": meta, "days": days}
    print(json.dumps(out, indent=2, sort_keys=False))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(
        description="Fetch GitLab user activity events and bucket into UTC day blocks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    p.add_argument(
        "--base-url",
        default=os.environ.get("GITLAB_URL") or os.environ.get("CI_SERVER_URL"),
        help="GitLab base URL, e.g. https://git.example.com (env: GITLAB_URL or CI_SERVER_URL)",
    )
    p.add_argument(
        "--token",
        default=os.environ.get("GITLAB_TOKEN"),
        help="Personal Access Token (env: GITLAB_TOKEN)",
    )
    p.add_argument(
        "--user",
        default=None,
        help="GitLab username (default: current authenticated user)",
    )

    p.add_argument(
        "--start",
        default=None,
        help="Start time (ISO-8601). If omitted, defaults to end - 10 days.",
    )
    p.add_argument(
        "--end",
        default=None,
        help="End time (ISO-8601). If omitted, defaults to now (UTC).",
    )
    p.add_argument(
        "--days",
        type=int,
        default=10,
        help="Default lookback in days if --start/--end are not provided (used with end=now).",
    )

    p.add_argument(
        "--format",
        choices=["llm-md", "json"],
        default="llm-md",
        help="Output format",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging to stderr",
    )

    # Optional heartbeat similar to your existing pattern (kept minimal).
    p.add_argument(
        "--heartbeat-secs",
        type=int,
        default=0,
        help="If >0, periodically print 'still working' to stderr.",
    )

    return p.parse_args(argv)


def start_heartbeat(interval_secs: int) -> threading.Event:
    """
    Start a heartbeat thread that prints periodically to stderr.
    Returns the stop event.

    This is intentionally simple: it is helpful if the GitLab instance is slow.
    """
    stop = threading.Event()
    if interval_secs <= 0:
        return stop

    start_ts = time.time()

    def _run() -> None:
        while not stop.wait(timeout=interval_secs):
            elapsed = human_td(timedelta(seconds=int(time.time() - start_ts)))
            eprint(f"[heartbeat] still working… elapsed {elapsed}")

    t = threading.Thread(target=_run, name="heartbeat", daemon=True)
    t.start()
    return stop


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point."""
    args = parse_args(argv)

    if not args.base_url:
        die("Error: --base-url or GITLAB_URL/CI_SERVER_URL must be provided.")
    if not args.token:
        die("Error: --token or GITLAB_TOKEN must be provided.")

    # Resolve window
    end = parse_iso8601(args.end) if args.end else datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    end = end.astimezone(timezone.utc).replace(microsecond=0)

    start = parse_iso8601(args.start) if args.start else None
    if start is None:
        start = end - timedelta(days=max(1, int(args.days)))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    start = start.astimezone(timezone.utc).replace(microsecond=0)

    window = TimeWindow(start=start, end=end)
    try:
        window.validate()
    except ValueError as ex:
        die(f"Invalid time window: {ex}")

    stop_hb = start_heartbeat(int(args.heartbeat_secs))

    try:
        gl = build_client(args.base_url, args.token, verbose=args.verbose)
        user_id, user_username, user_name = resolve_user(gl, args.user, verbose=args.verbose)

        raw_events: List[Dict[str, Any]] = []
        for raw in iter_user_events(gl, user_id, window, verbose=args.verbose):
            raw_events.append(raw)

        # Normalize & enforce window again on normalized created_at (defensive)
        normalized: List[Dict[str, Any]] = []
        for r in raw_events:
            ev = normalize_event(r)
            created = parse_iso8601(ev.get("created_at"))
            if created and window.contains(created):
                normalized.append(ev)

        # Sort globally by created_at ascending for stable output
        normalized.sort(key=lambda x: x.get("created_at") or "")

        days = bucket_by_day(normalized, window)

        meta = {
            "base_url": args.base_url,
            "user_id": user_id,
            "user_username": user_username,
            "user_name": user_name,
            "start": fmt_utc(window.start),
            "end": fmt_utc(window.end),
            "timezone": "UTC",
            "generated_at": fmt_utc(datetime.now(timezone.utc)),
            "format": args.format,
        }

        if args.format == "json":
            render_json(meta, days)
        else:
            render_llm_md(meta, days)

        return 0

    except gitlab.exceptions.GitlabAuthenticationError as ex:
        die(f"Authentication failed: {ex}", code=1)
    except gitlab.exceptions.GitlabHttpError as ex:
        die(f"GitLab HTTP error: {ex}", code=1)
    finally:
        stop_hb.set()


if __name__ == "__main__":
    raise SystemExit(main())
