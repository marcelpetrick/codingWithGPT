"""Tests for status rendering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent_watch.config import Config, Mode
from agent_watch.fsm import SupervisedSession
from agent_watch.proc import ProcessIdentity
from agent_watch.states import SessionState
from agent_watch.terminal.base import SessionRef
from agent_watch.ui import format_reset, render_line, render_status

NOW = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
REF = SessionRef("konsole", "org.kde.konsole-1", "/Sessions/2")
IDENTITY = ProcessIdentity(pid=15102, start_time=1, tty="pts/3", exe="/opt/claude")


def _session(**overrides) -> SupervisedSession:
    base = {
        "ref": REF,
        "identity": IDENTITY,
        "provider_name": "claude",
        "title": "beta : claude",
        "state": SessionState.WAITING_FOR_RESET,
        "reset_at": NOW + timedelta(hours=1),
    }
    return SupervisedSession(**{**base, **overrides})


def test_status_lists_each_session() -> None:
    text = render_status([_session()], now=NOW, config=Config(mode=Mode.AUTO))
    assert "WAITING_FOR_RESET" in text
    assert "15102" in text
    assert "mode=auto" in text
    assert "watching 1 session" in text


def test_status_handles_nothing_selected() -> None:
    text = render_status([], now=NOW, config=Config())
    assert "(nothing selected)" in text


def test_reset_beyond_a_day_is_not_shown_as_a_clock_time() -> None:
    # "12:00" for something three days out would be actively misleading.
    assert format_reset(NOW + timedelta(days=3), NOW) == "+3d"


def test_a_passed_reset_reads_as_due() -> None:
    assert format_reset(NOW - timedelta(minutes=1), NOW) == "due"


def test_no_reset_renders_as_a_dash() -> None:
    assert format_reset(None, NOW) == "-"


def test_observe_line_shape() -> None:
    line = render_line(_session(state=SessionState.LIMIT_BLOCKED), NOW)
    assert "claude pts/3: LIMIT_BLOCKED" in line
    assert "until" in line


def test_observe_line_for_an_active_session_has_no_until() -> None:
    line = render_line(_session(state=SessionState.ACTIVE, reset_at=None), NOW)
    assert "ACTIVE" in line
    assert "until" not in line
