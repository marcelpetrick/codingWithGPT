"""Tests for persistent action state."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_watch.state_store import ActionRecord, StateStore
from agent_watch.states import ActionState

KEY = "abc123"


def _store(tmp_path: Path) -> StateStore:
    return StateStore.in_directory(tmp_path).load()


def test_a_planned_action_survives_a_restart(tmp_path: Path) -> None:
    # DANGER 13: the crash happens between sending and recording. Recording
    # first means the restart sees PLANNED and refuses.
    store = _store(tmp_path)
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    reloaded = _store(tmp_path)
    assert KEY in reloaded.already_actioned()
    assert reloaded.records[KEY].state is ActionState.PLANNED


def test_lifecycle_transitions_are_recorded(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    store.mark(KEY, ActionState.SENT)
    store.mark(KEY, ActionState.VERIFIED, result="resumed")
    record = _store(tmp_path).records[KEY]
    assert record.state is ActionState.VERIFIED
    assert record.result == "resumed"
    assert record.is_settled


def test_attempts_increment_only_on_send(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    assert store.attempts_for(KEY) == 0
    store.mark(KEY, ActionState.SENT)
    store.mark(KEY, ActionState.FAILED, result="prompt-still-visible")
    assert store.attempts_for(KEY) == 1
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    store.mark(KEY, ActionState.SENT)
    assert store.attempts_for(KEY) == 2


def test_a_failed_action_is_not_blocked_from_retrying(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    store.mark(KEY, ActionState.SENT)
    store.mark(KEY, ActionState.FAILED)
    assert KEY not in store.already_actioned()


def test_writes_are_atomic_and_leave_no_temporary_files(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    names = {path.name for path in tmp_path.iterdir()}
    assert names == {"state.json"}


def test_state_file_is_owner_only(tmp_path: Path) -> None:
    store = StateStore.in_directory(tmp_path / "nested").load()
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    assert store.path.stat().st_mode & 0o777 == 0o600


def test_a_corrupt_state_file_starts_empty_rather_than_refusing_to_run(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json at all")
    assert _store(tmp_path).records == {}


def test_a_state_file_from_a_future_version_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 99, "actions": [{"key": "x"}]}))
    assert _store(tmp_path).records == {}


def test_stale_records_are_dropped_on_load(tmp_path: Path) -> None:
    # Yesterday's prompt fingerprint cannot be today's screen.
    old = ActionRecord(
        key=KEY,
        provider="claude",
        session="/Sessions/1",
        process="15102:987",
        state=ActionState.VERIFIED,
        updated_at=(datetime.now(UTC) - timedelta(days=3)).isoformat(timespec="seconds"),
    )
    store = StateStore.in_directory(tmp_path)
    store.records = {KEY: old}
    store.save()
    assert _store(tmp_path).records == {}


def test_malformed_records_are_skipped_not_fatal(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"version": 1, "actions": [{"key": "x"}, {"nonsense": True}]}))
    assert _store(tmp_path).records == {}


def test_forget_removes_a_record(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.plan(KEY, provider="claude", session="/Sessions/1", process="15102:987")
    store.forget(KEY)
    assert _store(tmp_path).records == {}
