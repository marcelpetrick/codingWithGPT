# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Assertions added after mutation testing (see docs/mutation_testing.md)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from mrreview import evaluate, textutil
from mrreview.bizhours import BusinessCalendar


def test_equal_start_and_end_hours_are_refused() -> None:
    with pytest.raises(ValueError, match="hours"):
        BusinessCalendar(tz=ZoneInfo("UTC"), start_hour=9, end_hour=9)


def test_calendar_uses_its_own_timezone_not_the_machine_one() -> None:
    # 2026-11-23 20:00 UTC is Tuesday 09:00 in Auckland (UTC+13) and Monday evening in Europe.
    cal = BusinessCalendar(tz=ZoneInfo("Pacific/Auckland"))
    start = datetime(2026, 11, 23, 20, 0, tzinfo=UTC)
    end = datetime(2026, 11, 23, 22, 0, tzinfo=UTC)
    assert cal.seconds(start, end) == 2 * 3600
    # Friday 17:00 Auckland is Friday 04:00 UTC; Monday 09:00 Auckland is Sunday 20:00 UTC.
    fri = datetime(2026, 11, 27, 4, 0, tzinfo=UTC)
    mon = datetime(2026, 11, 29, 20, 0, tzinfo=UTC)
    assert cal.seconds(fri, mon) == 2 * 3600


def test_censoring_boundary_is_inclusive() -> None:
    assert evaluate.censoring("open", "opened", "2026-11-06T12:00:00+00:00",
                              "2026-11-20T12:00:00+00:00", 14) == "recent"


def test_truncate_to_one_grapheme() -> None:
    assert textutil.truncate("abc", 1) == "…"
    assert textutil.truncate("a", 1) == "a"


def test_routine_word_limit() -> None:
    assert textutil.is_routine("ok ok ok ok ok ok ok ok")
    assert not textutil.is_routine("ok ok ok ok ok ok ok ok ok")


def test_span_keeps_fractions() -> None:
    cal = BusinessCalendar(ZoneInfo("UTC"))
    obs = evaluate._span(cal, "2026-11-23T09:00:00+00:00", "2026-11-23T09:20:00+00:00",
                         "2026-11-24T00:00:00+00:00")
    assert obs == {"state": "observed", "wall_h": 0.333, "biz_h": 0.333}
    pend = evaluate._span(cal, "2026-11-23T09:00:00+00:00", None, "2026-11-23T09:20:00+00:00")
    assert pend == {"state": "pending", "open_h": 0.33}
