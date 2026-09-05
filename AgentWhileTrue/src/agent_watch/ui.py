"""Rendering for the running watcher.

Plain text, no curses, no ANSI beyond an optional clear. The vision explicitly
says the MVP does not need a TUI framework, and plain output has the practical
advantage of being pipe-able, greppable and readable in a test failure.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

from agent_watch.config import Config
from agent_watch.fsm import SupervisedSession
from agent_watch.quota import Availability, QuotaSnapshot
from agent_watch.states import SessionState
from agent_watch.version import __version__

CLEAR_SCREEN = "\x1b[H\x1b[2J"

_HEADERS = ("ID", "TYPE", "STATE", "PROMPT", "QUOTA", "Q.RESET", "PID", "SESSION")
_WIDTHS = (4, 8, 20, 8, 10, 8, 8, 0)


def format_reset(reset_at: datetime | None, now: datetime) -> str:
    """Render a reset instant as a local wall-clock time, or a relative hint.

    Beyond a day out, a bare clock time is misleading, so the day count is
    shown instead.
    """
    if reset_at is None:
        return "-"
    delta = reset_at - now
    if delta.days >= 1:
        return f"+{delta.days}d"
    if delta.total_seconds() < 0:
        return "due"
    return reset_at.astimezone().strftime("%H:%M")


def _row(values: Sequence[str]) -> str:
    parts = []
    for value, width in zip(values, _WIDTHS, strict=True):
        parts.append(value if width == 0 else f"{value:<{width}}")
    return " ".join(parts).rstrip()


def quota_state(snapshot: QuotaSnapshot, now: datetime) -> str:
    """Render availability without presenting stale data as authoritative."""
    if snapshot.availability is not Availability.UNKNOWN and snapshot.is_stale(now):
        return "STALE"
    return snapshot.availability.value


def render_quota(snapshot: QuotaSnapshot, *, now: datetime, identity: str = "") -> str:
    """Render a provider snapshot for the ``quota`` query command."""
    lines = [
        f"{snapshot.provider.title()} {identity}".rstrip(),
        f"  availability: {quota_state(snapshot, now)}",
        f"  source:       {snapshot.source}",
    ]
    if snapshot.note:
        lines.append(f"  detail:       {snapshot.note}")
    if not snapshot.windows:
        lines.append("  windows:      no usable data")
    for window in snapshot.windows:
        lines.append(
            f"  {window.scope:<12} {window.used_percent:>6.1f}%  "
            f"reset {format_reset(window.resets_at, now)}"
        )
    return "\n".join(lines)


def render_status(
    sessions: Iterable[SupervisedSession],
    *,
    now: datetime,
    config: Config,
    last_event: str = "",
) -> str:
    """Render the running watcher's status table."""
    listed = list(sessions)
    lines = [
        f"Agent Watch {__version__}   mode={config.mode.value}   watching {len(listed)} session(s)",
        "",
        _row(_HEADERS),
        "-" * 72,
    ]
    for index, session in enumerate(listed, start=1):
        lines.append(
            _row(
                (
                    str(index),
                    session.provider_name.title(),
                    session.state.value,
                    format_reset(session.reset_at, now),
                    quota_state(session.quota, now),
                    format_reset(session.quota.next_reset, now),
                    str(session.identity.pid),
                    session.title or session.ref.session_id,
                )
            )
        )
    if not listed:
        lines.append("  (nothing selected)")
    lines.append("")
    if last_event:
        lines.append(f" Last: {last_event}")
    lines.append(" Sessions rescan automatically; Ctrl-C stops the watcher")
    return "\n".join(lines)


def render_line(session: SupervisedSession, now: datetime) -> str:
    """One-line observe-mode output, in the shape the vision sketches."""
    stamp = now.astimezone().strftime("%H:%M:%S")
    suffix = ""
    if session.state in {SessionState.LIMIT_BLOCKED, SessionState.WAITING_FOR_RESET}:
        suffix = f" until {format_reset(session.reset_at, now)}"
    return (
        f"[{stamp}] {session.provider_name} {session.identity.tty}: {session.state.value}{suffix}"
        f" quota={quota_state(session.quota, now)}"
        f" quota_reset={format_reset(session.quota.next_reset, now)}"
    )
