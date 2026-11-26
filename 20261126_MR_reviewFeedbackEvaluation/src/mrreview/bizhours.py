# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Estimated business time between two instants (REQ-TIME-1).

The calendar is Monday to Friday, start_hour to end_hour, in one timezone, minus optional
holidays. It is an estimate: personal schedules, leave and workload are unknown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SATURDAY = 5


@dataclass(frozen=True)
class BusinessCalendar:
    """A weekly business-hours calendar in one timezone."""

    tz: ZoneInfo
    start_hour: int = 8
    end_hour: int = 18
    holidays: frozenset[date] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not 0 <= self.start_hour < self.end_hour <= 24:
            raise ValueError("business hours must satisfy 0 <= start < end <= 24")

    def _window(self, day: date) -> tuple[datetime, datetime]:
        start = datetime.combine(day, time(self.start_hour), tzinfo=self.tz)
        if self.end_hour == 24:
            end = datetime.combine(day + timedelta(days=1), time(0), tzinfo=self.tz)
        else:
            end = datetime.combine(day, time(self.end_hour), tzinfo=self.tz)
        return start, end

    def seconds(self, start: datetime, end: datetime) -> float:
        """Business seconds in [start, end]. Both must be timezone-aware."""
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("datetimes must carry a timezone")
        if end < start:
            raise ValueError("end is before start")
        total = 0.0
        day = start.astimezone(self.tz).date()
        last = end.astimezone(self.tz).date()
        while day <= last:
            if day.weekday() < SATURDAY and day not in self.holidays:
                w_start, w_end = self._window(day)
                lo = max(start, w_start)
                hi = min(end, w_end)
                if hi > lo:
                    total += (hi - lo).total_seconds()
            day += timedelta(days=1)
        return total
