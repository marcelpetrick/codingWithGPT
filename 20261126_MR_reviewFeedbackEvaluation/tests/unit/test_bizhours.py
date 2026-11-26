# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the business-time calendar (REQ-TIME-1)."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from mrreview.bizhours import BusinessCalendar

BERLIN = ZoneInfo("Europe/Berlin")
CAL = BusinessCalendar(tz=BERLIN, start_hour=8, end_hour=18)


def b(*args: int) -> datetime:
    return datetime(*args, tzinfo=BERLIN)  # type: ignore[misc]


def test_same_day_inside_hours() -> None:
    assert CAL.seconds(b(2026, 11, 23, 9), b(2026, 11, 23, 11, 30)) == 2.5 * 3600


def test_clips_before_and_after_hours() -> None:
    assert CAL.seconds(b(2026, 11, 23, 6), b(2026, 11, 23, 20)) == 10 * 3600


def test_overnight_counts_only_business_hours() -> None:
    assert CAL.seconds(b(2026, 11, 23, 17), b(2026, 11, 24, 9)) == 2 * 3600


def test_weekend_is_excluded() -> None:
    # Friday 17:00 to Monday 09:00 is two business hours.
    assert CAL.seconds(b(2026, 11, 27, 17), b(2026, 11, 30, 9)) == 2 * 3600
    assert CAL.seconds(b(2026, 11, 28, 10), b(2026, 11, 29, 12)) == 0


def test_holidays_are_excluded() -> None:
    cal = BusinessCalendar(tz=BERLIN, holidays=frozenset({date(2026, 12, 25)}))
    assert cal.seconds(b(2026, 12, 24, 17), b(2026, 12, 28, 9)) == 2 * 3600


def test_dst_transition_days() -> None:
    # 2026-03-29 is a Sunday (spring forward); 2026-10-25 also a Sunday (fall back).
    assert CAL.seconds(b(2026, 3, 27, 17), b(2026, 3, 30, 9)) == 2 * 3600
    assert CAL.seconds(b(2026, 10, 23, 17), b(2026, 10, 26, 9)) == 2 * 3600
    # A full business day is ten hours on both sides of the change.
    assert CAL.seconds(b(2026, 3, 30, 0), b(2026, 3, 31, 0)) == 10 * 3600


def test_utc_input_is_converted() -> None:
    start = datetime(2026, 11, 23, 8, 0, tzinfo=UTC)  # 09:00 Berlin
    assert CAL.seconds(start, start + timedelta(hours=1)) == 3600


def test_zero_and_errors() -> None:
    t = b(2026, 11, 23, 9)
    assert CAL.seconds(t, t) == 0
    with pytest.raises(ValueError, match="before"):
        CAL.seconds(t, t - timedelta(seconds=1))
    with pytest.raises(ValueError, match="timezone"):
        CAL.seconds(datetime(2026, 1, 1), t)
    with pytest.raises(ValueError, match="hours"):
        BusinessCalendar(tz=BERLIN, start_hour=18, end_hour=8)


def test_multi_week_span() -> None:
    assert CAL.seconds(b(2026, 11, 23, 0), b(2026, 12, 7, 0)) == 10 * 10 * 3600
