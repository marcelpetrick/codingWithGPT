"""Tests for the event log.

The central property is negative: terminal content must not be able to reach the
log file, no matter what the screen contained.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agent_watch.logging_setup import EventLogger, fingerprint, format_event, read_history, setup

SECRET_SCREEN = [
    "You've hit your session limit · resets 8:10pm (Europe/Berlin)",
    "export ANTHROPIC_API_KEY=sk-ant-super-secret-value",
    "password: hunter2",
]


def test_fingerprint_is_stable_and_short() -> None:
    assert fingerprint(SECRET_SCREEN) == fingerprint(SECRET_SCREEN)
    assert len(fingerprint(SECRET_SCREEN)) == 12


def test_fingerprint_ignores_trailing_whitespace_redraws() -> None:
    padded = [line + "   " for line in SECRET_SCREEN]
    assert fingerprint(padded) == fingerprint(SECRET_SCREEN)


def test_fingerprint_changes_when_the_prompt_changes() -> None:
    other = [*SECRET_SCREEN[:-1], "Usage limit has reset · press enter to continue"]
    assert fingerprint(other) != fingerprint(SECRET_SCREEN)


def test_fingerprint_does_not_contain_the_content() -> None:
    digest = fingerprint(SECRET_SCREEN)
    assert "hunter2" not in digest
    assert "sk-ant" not in digest


def test_event_log_records_the_fingerprint_not_the_screen(tmp_path: Path) -> None:
    log_file = tmp_path / "agent-watch.log"
    log = setup(log_file)
    log.info(
        "limit_detected",
        provider="claude",
        session="/Sessions/2",
        pid=15102,
        screen=fingerprint(SECRET_SCREEN),
    )
    logging.getLogger("agent_watch").handlers[0].flush()
    written = log_file.read_text()
    assert "limit_detected" in written
    assert fingerprint(SECRET_SCREEN) in written
    assert "hunter2" not in written
    assert "sk-ant" not in written
    assert "session limit" not in written


def test_log_file_is_owner_only(tmp_path: Path) -> None:
    log_file = tmp_path / "nested" / "agent-watch.log"
    setup(log_file)
    assert log_file.stat().st_mode & 0o777 == 0o600
    assert log_file.parent.stat().st_mode & 0o077 == 0


def test_format_event_quotes_values_containing_spaces() -> None:
    line = format_event("state_change", {"session": "/Sessions/1", "note": "two words"})
    assert line == 'event=state_change session=/Sessions/1 note="two words"'


def test_format_event_renders_none_and_bools_readably() -> None:
    line = format_event("check", {"reset": None, "allowed": True, "refused": False})
    assert line == "event=check reset=- allowed=true refused=false"


def test_event_logger_has_no_free_text_method() -> None:
    # Free text is how terminal content reaches a log file by accident.
    assert not hasattr(EventLogger, "message")
    assert not hasattr(EventLogger, "log")


def test_rotation_is_configured(tmp_path: Path) -> None:
    log_file = tmp_path / "agent-watch.log"
    setup(log_file, max_bytes=128, backups=2)
    handler = logging.getLogger("agent_watch").handlers[0]
    assert handler.maxBytes == 128
    assert handler.backupCount == 2


def test_read_history_returns_only_the_newest_rows(tmp_path: Path) -> None:
    log_file = tmp_path / "agent-watch.log"
    log_file.write_text("first\nsecond\nthird\n", encoding="utf-8")
    assert read_history(log_file, limit=2) == ["second", "third"]


def test_read_history_tolerates_missing_files_and_zero_limit(tmp_path: Path) -> None:
    log_file = tmp_path / "missing.log"
    assert read_history(log_file) == []
    assert read_history(log_file, limit=0) == []
