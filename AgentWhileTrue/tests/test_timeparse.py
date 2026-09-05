"""Tests for reset-time parsing."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agent_watch.providers.timeparse import parse_reset

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 9, 5, 19, 31, tzinfo=BERLIN)


def test_clock_time_with_zone() -> None:
    parsed = parse_reset("You've hit your session limit · resets 8:10pm (Europe/Berlin)", NOW)
    assert parsed == datetime(2026, 9, 5, 20, 10, tzinfo=BERLIN)


def test_clock_time_already_past_rolls_to_tomorrow() -> None:
    parsed = parse_reset("resets 7:00am", NOW)
    assert parsed == datetime(2026, 9, 6, 7, 0, tzinfo=BERLIN)


def test_midnight_is_not_confused_with_noon() -> None:
    assert parse_reset("resets 12:00am", NOW) == datetime(2026, 9, 6, 0, 0, tzinfo=BERLIN)
    assert parse_reset("resets 12:30pm", NOW) == datetime(2026, 9, 6, 12, 30, tzinfo=BERLIN)


def test_weekday_form() -> None:
    # 2026-09-05 is a Saturday; the next Monday is the 7th.
    parsed = parse_reset("You've hit your weekly limit · resets Mon 12:00am", NOW)
    assert parsed == datetime(2026, 9, 7, 0, 0, tzinfo=BERLIN)


def test_relative_form() -> None:
    assert parse_reset("resets in 4h51m", NOW) == NOW + timedelta(hours=4, minutes=51)


def test_relative_minutes_only() -> None:
    assert parse_reset("resets in 90m", NOW) == NOW + timedelta(minutes=90)


def test_codex_try_again_at() -> None:
    parsed = parse_reset("You've hit your usage limit. Try again at 8:10 PM.", NOW)
    assert parsed == datetime(2026, 9, 5, 20, 10, tzinfo=BERLIN)


@pytest.mark.parametrize(
    "text",
    [
        "You've hit your session limit",
        "resets soon",
        "resets 25:99",
        "",
    ],
)
def test_unparseable_text_returns_none(text: str) -> None:
    # A None reset means "wait for a provider signal", never "resume now".
    assert parse_reset(text, NOW) is None


def test_unknown_timezone_falls_back_to_local_rather_than_failing() -> None:
    parsed = parse_reset("resets 8:10pm (Mars/Olympus)", NOW)
    assert parsed == datetime(2026, 9, 5, 20, 10, tzinfo=BERLIN)
