"""Tests for interactive dashboard state without touching a real terminal."""

from agent_watch.tui import INTERVALS, DashboardState


def test_refresh_keys_follow_btop_interval_direction() -> None:
    state = DashboardState.from_interval(2)
    state.handle("+")
    assert state.interval == 3
    state.handle("-")
    assert state.interval == 2


def test_dashboard_keys_toggle_state_and_quit() -> None:
    state = DashboardState.from_interval(1)
    assert not state.handle("p")
    assert state.paused
    state.handle("h")
    assert state.help_visible
    state.handle("r")
    assert state.rescan_requested
    state.handle("t")
    assert state.theme == "vivid"
    assert state.handle("q")


def test_refresh_ladder_clamps_at_both_ends() -> None:
    state = DashboardState.from_interval(INTERVALS[0])
    state.handle("-")
    assert state.interval == INTERVALS[0]
    state.interval_index = len(INTERVALS) - 1
    state.handle("+")
    assert state.interval == INTERVALS[-1]
