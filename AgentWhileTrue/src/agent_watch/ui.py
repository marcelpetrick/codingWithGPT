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
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"

_DARK = {
    "structure": "\x1b[36m",
    "healthy": "\x1b[32m",
    "warning": "\x1b[33m",
    "danger": "\x1b[31m",
    "claude": "\x1b[35m",
    "codex": "\x1b[34m",
    "dim": "\x1b[2m",
}
_VIVID = {
    "structure": "\x1b[38;5;45m",
    "healthy": "\x1b[38;5;48m",
    "warning": "\x1b[38;5;214m",
    "danger": "\x1b[38;5;196m",
    "claude": "\x1b[38;5;213m",
    "codex": "\x1b[38;5;75m",
    "dim": "\x1b[38;5;244m",
}
_RESET = "\x1b[0m"

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


def _paint(text: str, role: str, *, color: bool, theme: str) -> str:
    if not color or theme == "plain":
        return text
    palette = _VIVID if theme == "vivid" else _DARK
    return f"{palette[role]}{text}{_RESET}"


def _rule(title: str, width: int, *, color: bool, theme: str) -> str:
    prefix = f"┌─ {title} "
    plain = prefix + "─" * max(3, width - len(prefix) - 1) + "┐"
    return _paint(plain, "structure", color=color, theme=theme)


def _state_role(value: str) -> str:
    if value in {"ACTIVE", "AVAILABLE", "READY_TO_RESUME"}:
        return "healthy"
    if value in {"UNSAFE", "PROCESS_GONE", "EXHAUSTED"}:
        return "danger"
    return "warning"


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
    refresh_interval: float | None = None,
    paused: bool = False,
    show_help: bool = False,
    color: bool = False,
    theme: str = "dark",
    width: int = 100,
) -> str:
    """Render the running watcher's status table."""
    listed = list(sessions)
    title = f"Agent While True {__version__}"
    interval = refresh_interval if refresh_interval is not None else config.scan_interval
    pause_badge = "   PAUSED — press p to resume" if paused else ""
    lines = [
        _rule(title, width, color=color, theme=theme)
        + _paint(pause_badge, "warning", color=color, theme=theme),
        (
            f"  {now.astimezone().strftime('%Y-%m-%d %H:%M:%S')}   every {interval:g}s   "
            "[+ slower  - faster  r rescan  p pause  t theme  h help  q quit]"
        ),
        (f"  mode={config.mode.value}   watching {len(listed)} session(s)   theme={theme}"),
        "",
        _paint("  SESSIONS", "structure", color=color, theme=theme),
        _paint(_row(_HEADERS), "dim", color=color, theme=theme),
        _paint("─" * min(width, 100), "structure", color=color, theme=theme),
    ]
    for index, session in enumerate(listed, start=1):
        row = _row(
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
        role = _state_role(session.quota.availability.value)
        lines.append(_paint(row, role, color=color, theme=theme))
    if not listed:
        lines.append("  (nothing selected)")
    lines.append("")
    if last_event:
        lines.append(_paint("  EVENTS", "structure", color=color, theme=theme))
        lines.append(f"    {last_event}")
    if show_help:
        lines.extend(
            (
                "",
                _paint("  KEYS", "structure", color=color, theme=theme),
                "    - / +   refresh faster / slower (0.25, 0.5, 1, 2, 3, 5, 10, 30, 60s)",
                "    p       pause/resume; paused means no terminal or quota polling",
                "    r       rediscover Konsole sessions now",
                "    t       cycle dark, vivid and plain themes",
                "    h / ?   close this help",
                "    q       quit cleanly",
            )
        )
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
