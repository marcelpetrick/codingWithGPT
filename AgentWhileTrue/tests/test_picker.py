"""Tests for the session picker."""

from __future__ import annotations

from pathlib import Path

from agent_watch.picker import (
    Candidate,
    NumberedPicker,
    PickerState,
    discover,
    pick_with_fzf,
    preselected,
    render,
)
from tests import harness as harness_module


def _candidates(tmp_path: Path) -> list[Candidate]:
    kit = harness_module.build(tmp_path)
    claude = kit.inspector.add_claude(15102, tty="pts/3")
    codex = kit.inspector.add_codex(15591, tty="pts/5")
    shell = kit.inspector.add_shell(15201, tty="pts/4")
    kit.terminal.add("/Sessions/1", shell_pid=1, foreground_pid=claude.identity.pid)
    kit.terminal.add("/Sessions/2", shell_pid=2, foreground_pid=codex.identity.pid)
    kit.terminal.add("/Sessions/3", shell_pid=3, foreground_pid=shell.identity.pid)
    return discover(kit.terminal, kit.inspector)


def test_discovery_classifies_every_session(tmp_path: Path) -> None:
    found = _candidates(tmp_path)
    assert [candidate.provider for candidate in found] == ["claude", "codex", None]


def test_only_agents_are_preselected(tmp_path: Path) -> None:
    found = _candidates(tmp_path)
    chosen = preselected(found)
    assert len(chosen) == 2
    # The plain shell is never ticked by default.
    assert found[2].key not in chosen


def test_a_shell_cannot_be_toggled_on(tmp_path: Path) -> None:
    state = PickerState(candidates=_candidates(tmp_path))
    assert not state.toggle(3)
    assert state.selected == set()


def test_toggling_an_agent_works_both_ways(tmp_path: Path) -> None:
    found = _candidates(tmp_path)
    state = PickerState(candidates=found)
    assert state.toggle(1)
    assert state.selected == {found[0].key}
    assert state.toggle(1)
    assert state.selected == set()


def test_out_of_range_index_is_ignored(tmp_path: Path) -> None:
    state = PickerState(candidates=_candidates(tmp_path))
    assert not state.toggle(0)
    assert not state.toggle(99)


def test_render_shows_why_a_session_is_ineligible(tmp_path: Path) -> None:
    state = PickerState(candidates=_candidates(tmp_path))
    text = render(state)
    assert "idle-shell" in text
    assert "pts/3" in text
    assert "PID 15102" in text


def test_render_survives_an_empty_discovery() -> None:
    assert "no Konsole sessions found" in render(PickerState(candidates=[]))


def test_enter_accepts_the_preselection(tmp_path: Path) -> None:
    found = _candidates(tmp_path)
    picker = NumberedPicker(read=lambda prompt: "", write=lambda text: None)
    chosen = picker.run(found)
    assert chosen is not None
    assert {candidate.provider for candidate in chosen} == {"claude", "codex"}


def test_quit_returns_nothing(tmp_path: Path) -> None:
    picker = NumberedPicker(read=lambda prompt: "q", write=lambda text: None)
    assert picker.run(_candidates(tmp_path)) is None


def test_a_closed_stdin_is_not_consent(tmp_path: Path) -> None:
    def closed(prompt: str) -> str:
        raise EOFError

    picker = NumberedPicker(read=closed, write=lambda text: None)
    assert picker.run(_candidates(tmp_path)) is None


def test_select_none_then_pick_one(tmp_path: Path) -> None:
    found = _candidates(tmp_path)
    answers = iter(["n", "2", ""])
    picker = NumberedPicker(read=lambda prompt: next(answers), write=lambda text: None)
    chosen = picker.run(found)
    assert chosen is not None
    assert [candidate.provider for candidate in chosen] == ["codex"]


def test_select_all_agents_after_clearing(tmp_path: Path) -> None:
    found = _candidates(tmp_path)
    answers = iter(["n", "a", ""])
    picker = NumberedPicker(read=lambda prompt: next(answers), write=lambda text: None)
    chosen = picker.run(found)
    assert chosen is not None
    assert len(chosen) == 2


def test_rescan_drops_selections_for_sessions_that_vanished(tmp_path: Path) -> None:
    found = _candidates(tmp_path)
    answers = iter(["r", ""])
    picker = NumberedPicker(read=lambda prompt: next(answers), write=lambda text: None)
    chosen = picker.run(found, rescan=lambda: found[1:])
    assert chosen is not None
    assert [candidate.provider for candidate in chosen] == ["codex"]


def test_fzf_is_optional(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("agent_watch.picker.fzf_available", lambda: False)
    assert pick_with_fzf(_candidates(tmp_path)) is None
