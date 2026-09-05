"""Parse the reset times that the agent CLIs print.

Machine-readable provider state is always preferred (vision DANGER 12), and this
module is the fallback for when none is available. It is deliberately strict:
anything it cannot parse with confidence returns ``None``, and a ``None`` reset
time means the supervisor waits for a provider signal instead of guessing.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

#: "resets 8:10pm (Europe/Berlin)" / "Try again at 8:10 PM"
_CLOCK_RE = re.compile(
    r"(?P<hour>\d{1,2})[:.](?P<minute>\d{2})\s*(?P<meridiem>am|pm)?"
    r"(?:\s*\((?P<tz>[A-Za-z_]+/[A-Za-z_+-]+)\))?",
    re.IGNORECASE,
)
#: "resets Mon 12:00am"
_WEEKDAY_RE = re.compile(
    r"\b(?P<weekday>mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\b", re.IGNORECASE
)
#: "resets in 4h51m" / "resets in 90m" / "resets in 45s"
_RELATIVE_RE = re.compile(
    r"\bin\s+(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m(?!s))?\s*(?:(?P<seconds>\d+)\s*s)?",
    re.IGNORECASE,
)

_WEEKDAYS = {
    "mon": 0,
    "tue": 1,
    "tues": 1,
    "wed": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

DAYS_PER_WEEK = 7
NOON = 12
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60


def _zone(name: str | None, fallback: datetime) -> ZoneInfo | None:
    if not name:
        return fallback.tzinfo if isinstance(fallback.tzinfo, ZoneInfo) else None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _apply_meridiem(hour: int, meridiem: str | None) -> int | None:
    if meridiem is None:
        return hour if 0 <= hour < HOURS_PER_DAY else None
    lowered = meridiem.lower()
    if not 1 <= hour <= NOON:
        return None
    if lowered == "am":
        return 0 if hour == NOON else hour
    return hour if hour == NOON else hour + NOON


def parse_relative(text: str, now: datetime) -> datetime | None:
    """Parse ``resets in 4h51m`` style text into an absolute instant."""
    match = _RELATIVE_RE.search(text)
    if match is None or not any(match.group(name) for name in ("hours", "minutes", "seconds")):
        return None
    delta = timedelta(
        hours=int(match.group("hours") or 0),
        minutes=int(match.group("minutes") or 0),
        seconds=int(match.group("seconds") or 0),
    )
    if delta == timedelta(0):
        return None
    return now + delta


def parse_reset(text: str, now: datetime) -> datetime | None:
    """Parse a reset instant out of one line of provider output.

    Handles the three shapes the CLIs actually emit:

    - ``resets 8:10pm (Europe/Berlin)`` - a clock time, optionally with a zone;
    - ``resets Mon 12:00am`` - a clock time on the next occurrence of a weekday;
    - ``resets in 4h51m`` - a relative offset.

    A parsed time that has already passed today is rolled forward to tomorrow,
    because these CLIs only ever name a reset in the future.
    """
    if (relative := parse_relative(text, now)) is not None:
        return relative

    clock = _CLOCK_RE.search(text)
    if clock is None:
        return None
    hour = _apply_meridiem(int(clock.group("hour")), clock.group("meridiem"))
    minute = int(clock.group("minute"))
    if hour is None or minute >= MINUTES_PER_HOUR:
        return None

    zone = _zone(clock.group("tz"), now)
    reference = now.astimezone(zone) if zone is not None else now
    candidate = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)

    weekday = _WEEKDAY_RE.search(text)
    if weekday is not None:
        target = _WEEKDAYS[weekday.group("weekday").lower()]
        ahead = (target - candidate.weekday()) % DAYS_PER_WEEK
        if ahead == 0 and candidate <= reference:
            ahead = DAYS_PER_WEEK
        candidate += timedelta(days=ahead)
    elif candidate <= reference:
        candidate += timedelta(days=1)

    return candidate.astimezone(now.tzinfo)
