"""Tests for provider quota sources.

The fixtures are trimmed copies of real documents: a Codex session rollout event
as written by Codex CLI 0.153.2, and the status-line payload Claude Code hands
its status-line command.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_watch import quota
from agent_watch.quota import (
    Availability,
    ClaudeStatuslineSource,
    CodexRolloutSource,
    NullSource,
    QuotaSnapshot,
    QuotaWindow,
)

NOW = datetime(2026, 9, 5, 20, 50, tzinfo=UTC)

CODEX_EVENT = {
    "timestamp": "2026-09-05T20:50:00.073Z",
    "type": "event_msg",
    "payload": {
        "type": "token_count",
        "rate_limits": {
            "limit_id": "codex",
            "primary": {"used_percent": 20.0, "window_minutes": 300, "resets_at": 1788527587},
            "secondary": {"used_percent": 72.0, "window_minutes": 10080, "resets_at": 1788776333},
            "credits": {"has_credits": False, "unlimited": False, "balance": "0"},
            "plan_type": "plus",
            "rate_limit_reached_type": None,
        },
    },
}

CLAUDE_STATUSLINE = {
    "source": "claude",
    "updated_at": 1788641342,
    "five_hour": {"used_percentage": 57.0, "resets_at": 1788657600},
    "seven_day": {"used_percentage": 40.0, "resets_at": 1788674400},
}


def _write_rollout(tmp_path: Path, *events: dict) -> Path:
    path = tmp_path / "rollout-2026-09-05T20-00-00-abc.jsonl"
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    return path


def test_codex_rollout_is_parsed_into_windows(tmp_path: Path, monkeypatch) -> None:
    path = _write_rollout(tmp_path, CODEX_EVENT)
    monkeypatch.setattr(quota, "find_codex_rollout", lambda pid: path)
    snapshot = CodexRolloutSource().snapshot(pid=123)
    assert snapshot.availability is Availability.AVAILABLE
    assert {window.scope for window in snapshot.windows} == {"session", "weekly"}
    assert snapshot.exhausted_scopes == frozenset()


def test_codex_newest_event_wins(tmp_path: Path, monkeypatch) -> None:
    older = json.loads(json.dumps(CODEX_EVENT))
    newer = json.loads(json.dumps(CODEX_EVENT))
    newer["payload"]["rate_limits"]["primary"]["used_percent"] = 100.0
    path = _write_rollout(tmp_path, older, newer)
    monkeypatch.setattr(quota, "find_codex_rollout", lambda pid: path)
    snapshot = CodexRolloutSource().snapshot(pid=123)
    assert snapshot.availability is Availability.EXHAUSTED
    assert snapshot.exhausted_scopes == {"session"}


def test_codex_reached_type_forces_exhausted(tmp_path: Path, monkeypatch) -> None:
    # The provider says a limit was reached even though no window reads 100%.
    # The provider's own verdict wins.
    event = json.loads(json.dumps(CODEX_EVENT))
    event["payload"]["rate_limits"]["rate_limit_reached_type"] = "usage_limit_reached"
    path = _write_rollout(tmp_path, event)
    monkeypatch.setattr(quota, "find_codex_rollout", lambda pid: path)
    assert CodexRolloutSource().snapshot(pid=123).availability is Availability.EXHAUSTED


def test_codex_partial_first_line_after_a_tail_seek_is_tolerated(
    tmp_path: Path, monkeypatch
) -> None:
    path = _write_rollout(tmp_path, CODEX_EVENT)
    path.write_text('{"truncated": tru\n' + path.read_text(), encoding="utf-8")
    monkeypatch.setattr(quota, "find_codex_rollout", lambda pid: path)
    assert CodexRolloutSource().snapshot(pid=123).availability is Availability.AVAILABLE


def test_codex_without_a_rollout_is_unknown_not_available(monkeypatch) -> None:
    monkeypatch.setattr(quota, "find_codex_rollout", lambda pid: None)
    snapshot = CodexRolloutSource().snapshot(pid=123)
    assert snapshot.availability is Availability.UNKNOWN
    assert snapshot.note == "no-rollout-file"


def test_codex_source_without_a_pid_is_unknown() -> None:
    assert CodexRolloutSource().snapshot().availability is Availability.UNKNOWN


def test_a_broken_source_returns_unknown_rather_than_raising(tmp_path: Path, monkeypatch) -> None:
    def explode(pid: int):
        raise OSError("bus error")

    monkeypatch.setattr(quota, "find_codex_rollout", explode)
    snapshot = CodexRolloutSource().snapshot(pid=1)
    assert snapshot.availability is Availability.UNKNOWN
    assert snapshot.note.startswith("error:")


def test_claude_statusline_is_parsed(tmp_path: Path) -> None:
    path = tmp_path / "claude.json"
    path.write_text(json.dumps(CLAUDE_STATUSLINE), encoding="utf-8")
    snapshot = ClaudeStatuslineSource(path=path).snapshot()
    assert snapshot.availability is Availability.AVAILABLE
    assert {window.scope for window in snapshot.windows} == {"session", "weekly"}


def test_claude_statusline_accepts_the_utilization_spelling(tmp_path: Path) -> None:
    path = tmp_path / "claude.json"
    path.write_text(
        json.dumps({"updated_at": 1788641342, "five_hour": {"utilization": 100}}), encoding="utf-8"
    )
    snapshot = ClaudeStatuslineSource(path=path).snapshot()
    assert snapshot.exhausted_scopes == {"session"}


def test_missing_statusline_file_is_unknown(tmp_path: Path) -> None:
    snapshot = ClaudeStatuslineSource(path=tmp_path / "absent.json").snapshot()
    assert snapshot.availability is Availability.UNKNOWN


def test_corrupt_statusline_file_is_unknown(tmp_path: Path) -> None:
    path = tmp_path / "claude.json"
    path.write_text("{not json", encoding="utf-8")
    assert ClaudeStatuslineSource(path=path).snapshot().availability is Availability.UNKNOWN


def test_next_reset_is_the_last_exhausted_window() -> None:
    early = datetime(2026, 9, 5, 21, 0, tzinfo=UTC)
    late = datetime(2026, 9, 11, 10, 0, tzinfo=UTC)
    snapshot = QuotaSnapshot(
        provider="claude",
        availability=Availability.EXHAUSTED,
        source="test",
        observed_at=NOW,
        windows=(
            QuotaWindow("session", 100.0, early),
            QuotaWindow("weekly", 100.0, late),
        ),
    )
    # A five-hour reset must not unblock a spent weekly window.
    assert snapshot.next_reset == late


def test_a_healthy_window_does_not_extend_the_reset() -> None:
    snapshot = QuotaSnapshot(
        provider="claude",
        availability=Availability.EXHAUSTED,
        source="test",
        observed_at=NOW,
        windows=(
            QuotaWindow("session", 100.0, datetime(2026, 9, 5, 21, 0, tzinfo=UTC)),
            QuotaWindow("weekly", 12.0, datetime(2026, 9, 11, 10, 0, tzinfo=UTC)),
        ),
    )
    assert snapshot.next_reset == datetime(2026, 9, 5, 21, 0, tzinfo=UTC)


def test_staleness_is_detected() -> None:
    snapshot = QuotaSnapshot(
        provider="claude",
        availability=Availability.AVAILABLE,
        source="test",
        observed_at=NOW - timedelta(hours=2),
    )
    assert snapshot.is_stale(NOW)
    assert not snapshot.is_stale(NOW - timedelta(hours=2))


def test_a_snapshot_without_a_timestamp_is_stale() -> None:
    snapshot = QuotaSnapshot(provider="claude", availability=Availability.UNKNOWN, source="test")
    assert snapshot.is_stale(NOW)


def test_null_source_is_always_unknown() -> None:
    assert NullSource().snapshot(pid=1).availability is Availability.UNKNOWN


def test_default_sources_cover_both_providers(tmp_path: Path) -> None:
    sources = quota.default_sources(tmp_path)
    assert set(sources) == {"codex", "claude"}
