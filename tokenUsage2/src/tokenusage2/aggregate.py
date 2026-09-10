# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Everything the dashboard shows, computed from the event list. No I/O.

Bucket edges are local midnights computed with ``zoneinfo``, so days that are
23 or 25 hours long around DST changes are still exactly one bucket.
"""

from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
from enum import StrEnum
from pathlib import PurePath

from tokenusage2.model import Account, Event, QuotaWindow, Tool, Usage

WINDOW_SECONDS = {"5h": 5 * 3600, "week": 7 * 86400}
#: Keeps date arithmetic in range however far back a cursor is pushed.
MAX_CURSOR = 5000


class Period(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class GroupBy(StrEnum):
    ACCOUNT = "account"
    TOOL = "tool"
    BACKEND = "backend"
    MODEL = "model"
    PROJECT = "project"


class Metric(StrEnum):
    TOTAL = "total"
    FRESH = "fresh"
    OUTPUT = "output"


DEFAULT_BUCKETS = {Period.DAY: 30, Period.WEEK: 16, Period.MONTH: 12}
METRIC_HELP = {
    Metric.TOTAL: "all tokens incl. cache",
    Metric.FRESH: "fresh input + output",
    Metric.OUTPUT: "output tokens",
}


@dataclass(slots=True)
class Tally:
    calls: int = 0
    input: int = 0
    cache_read: int = 0
    cache_write: int = 0
    output: int = 0
    reasoning: int = 0
    unsplit: int = 0

    def add(self, usage: Usage) -> None:
        if not usage.unsplit:
            self.calls += 1
        self.input += usage.input
        self.cache_read += usage.cache_read
        self.cache_write += usage.cache_write
        self.output += usage.output
        self.reasoning += usage.reasoning
        self.unsplit += usage.unsplit

    @property
    def total(self) -> int:
        return self.input + self.cache_read + self.cache_write + self.output + self.unsplit

    @property
    def cache_share(self) -> float:
        prompt = self.input + self.cache_read + self.cache_write
        return self.cache_read / prompt if prompt else 0.0

    def value(self, metric: Metric) -> int:
        if metric is Metric.FRESH:
            return self.input + self.output
        if metric is Metric.OUTPUT:
            return self.output
        return self.total

    def hatched(self, metric: Metric) -> int:
        """The part of ``value`` that comes from retained, unsplit totals."""
        return self.unsplit if metric is Metric.TOTAL else 0


def usage_value(usage: Usage, metric: Metric) -> int:
    if metric is Metric.FRESH:
        return usage.fresh
    if metric is Metric.OUTPUT:
        return usage.output
    return usage.total


def period_start(period: Period, day: date) -> date:
    if period is Period.WEEK:
        return day - timedelta(days=day.weekday())
    if period is Period.MONTH:
        return day.replace(day=1)
    return day


def shift(period: Period, start: date, steps: int) -> date:
    if period is Period.DAY:
        return start + timedelta(days=steps)
    if period is Period.WEEK:
        return start + timedelta(weeks=steps)
    months = start.year * 12 + start.month - 1 + steps
    return date(months // 12, months % 12 + 1, 1)


def periods_back(period: Period, earlier: date, later: date) -> int:
    """How many whole periods separate the buckets of ``earlier`` and ``later``."""
    first, last = period_start(period, earlier), period_start(period, later)
    if period is Period.MONTH:
        return (last.year * 12 + last.month) - (first.year * 12 + first.month)
    days = (last - first).days
    return days // 7 if period is Period.WEEK else days


def midnight(day: date, tz: tzinfo) -> float:
    return datetime.combine(day, time(0), tzinfo=tz).timestamp()


def labels(period: Period, start: date) -> tuple[str, str]:
    """(short axis label, long title label) for a bucket."""
    if period is Period.WEEK:
        week = start.isocalendar().week
        return f"W{week:02d}", f"week {week} · {start:%d %b} - {start + timedelta(days=6):%d %b}"
    if period is Period.MONTH:
        return f"{start:%b}", f"{start:%B %Y}"
    return f"{start:%d}", f"{start:%a %d %b %Y}"


def project_name(path: str) -> str:
    if not path:
        return "(unknown)"
    if path.startswith("("):
        return path
    return PurePath(path).name or path


@dataclass(slots=True)
class Bucket:
    start: date
    start_ts: float
    end_ts: float
    short: str
    long: str
    groups: dict[str, Tally] = field(default_factory=dict)
    total: Tally = field(default_factory=Tally)


@dataclass(slots=True)
class QuotaView:
    window: str
    used: float
    resets_at: float | None
    observed_at: float
    source: str
    rolled: bool


@dataclass(slots=True)
class AccountRow:
    id: str
    label: str
    tool: Tool
    identity: str | None
    plan: str | None
    archived: bool
    today: Tally = field(default_factory=Tally)
    week: Tally = field(default_factory=Tally)
    month: Tally = field(default_factory=Tally)
    all: Tally = field(default_factory=Tally)
    hourly: list[int] = field(default_factory=lambda: [0] * 24)
    rate: float = 0.0
    last_ts: float | None = None
    running: int = 0
    quotas: list[QuotaView] = field(default_factory=list)


@dataclass(slots=True)
class BreakdownRow:
    name: str
    extra: str
    tally: Tally


@dataclass(slots=True)
class Snapshot:
    now: float
    period: Period
    group: GroupBy
    metric: Metric
    detail: GroupBy
    buckets: list[Bucket]
    groups: list[str]
    selected: int
    breakdown: list[BreakdownRow]
    accounts: list[AccountRow]
    today: Tally
    week: Tally
    month: Tally
    all: Tally
    rate: float
    recent: list[Event]
    heatmap: list[list[int]]
    first_ts: float | None
    last_ts: float | None
    account_filter: str | None = None

    @property
    def selected_bucket(self) -> Bucket | None:
        return self.buckets[self.selected] if self.buckets else None

    @property
    def has_hatched(self) -> bool:
        return self.metric is Metric.TOTAL and any(b.total.unsplit for b in self.buckets)


def group_key(event: Event, group: GroupBy, names: Mapping[str, str]) -> str:
    if group is GroupBy.ACCOUNT:
        return names.get(event.account, event.account)
    if group is GroupBy.TOOL:
        return str(event.tool)
    if group is GroupBy.BACKEND:
        return event.backend
    if group is GroupBy.MODEL:
        return event.model
    return project_name(event.project)


def quota_view(quota: QuotaWindow, now: float) -> QuotaView:
    rolled = quota.resets_at is not None and quota.resets_at <= now
    return QuotaView(
        window=quota.window,
        used=0.0 if rolled else quota.used_percent,
        resets_at=None if rolled else quota.resets_at,
        observed_at=quota.observed_at,
        source=quota.source,
        rolled=rolled,
    )


def _slice(timestamps: Sequence[float], start: float, end: float) -> range:
    return range(bisect_left(timestamps, start), bisect_left(timestamps, end))


def build_snapshot(
    events: Sequence[Event],
    accounts: Sequence[Account],
    quotas: Iterable[QuotaWindow],
    *,
    now: float,
    tz: tzinfo,
    period: Period = Period.DAY,
    group: GroupBy = GroupBy.ACCOUNT,
    metric: Metric = Metric.TOTAL,
    detail: GroupBy = GroupBy.MODEL,
    cursor: int = 0,
    count: int | None = None,
    account_filter: str | None = None,
    recent: int = 30,
    archived: Iterable[str] = (),
    running: Mapping[str, int] | None = None,
) -> Snapshot:
    """Aggregate ``events`` (sorted by ``ts``) for one dashboard frame.

    ``cursor`` selects the bucket that many periods before the current one;
    the visible window scrolls only when the cursor leaves it.
    """
    if account_filter is not None:
        events = [event for event in events if event.account == account_filter]
    timestamps = [event.ts for event in events]
    names = {account.id: account.label for account in accounts}
    today = datetime.fromtimestamp(now, tz).date()
    count = count or DEFAULT_BUCKETS[period]
    cursor = min(max(0, cursor), MAX_CURSOR)
    window_back = max(0, cursor - (count - 1))
    newest = shift(period, period_start(period, today), -window_back)
    starts = [shift(period, newest, step) for step in range(-(count - 1), 2)]
    edges = [midnight(day, tz) for day in starts]

    buckets = []
    for index, start in enumerate(starts[:-1]):
        short, long = labels(period, start)
        buckets.append(Bucket(start, edges[index], edges[index + 1], short, long))
    for position in _slice(timestamps, edges[0], edges[-1]):
        event = events[position]
        bucket = buckets[bisect_right(edges, event.ts) - 1]
        key = group_key(event, group, names)
        bucket.groups.setdefault(key, Tally()).add(event.usage)
        bucket.total.add(event.usage)

    weights: dict[str, int] = {}
    for bucket in buckets:
        for key, tally in bucket.groups.items():
            weights[key] = weights.get(key, 0) + tally.value(metric)
    groups = [
        key for key, weight in sorted(weights.items(), key=lambda kv: (-kv[1], kv[0])) if weight > 0
    ]

    selected = count - 1 - (cursor - window_back)
    breakdown_rows: dict[str, BreakdownRow] = {}
    if buckets:
        chosen = buckets[selected]
        for position in _slice(timestamps, chosen.start_ts, chosen.end_ts):
            event = events[position]
            key = group_key(event, detail, names)
            row = breakdown_rows.get(key)
            if row is None:
                extra = {GroupBy.MODEL: event.backend, GroupBy.ACCOUNT: str(event.tool)}.get(
                    detail, ""
                )
                row = breakdown_rows[key] = BreakdownRow(key, extra, Tally())
            row.tally.add(event.usage)
    breakdown = sorted(
        breakdown_rows.values(), key=lambda row: (-row.tally.value(metric), row.name)
    )

    day_start = midnight(today, tz)
    week_start = midnight(period_start(Period.WEEK, today), tz)
    month_start = midnight(period_start(Period.MONTH, today), tz)
    archived_ids = set(archived)
    live = running or {}
    rows = {
        account.id: AccountRow(
            account.id,
            account.label,
            account.tool,
            account.identity,
            account.plan,
            account.id in archived_ids,
            running=live.get(account.id, 0),
        )
        for account in accounts
        if account_filter is None or account.id == account_filter
    }
    overall = {"today": Tally(), "week": Tally(), "month": Tally(), "all": Tally()}
    for event in events:
        row = rows.get(event.account)
        targets = [overall["all"]] + ([row.all] if row else [])
        if event.ts >= month_start:
            targets += [overall["month"]] + ([row.month] if row else [])
        if event.ts >= week_start:
            targets += [overall["week"]] + ([row.week] if row else [])
        if event.ts >= day_start:
            targets += [overall["today"]] + ([row.today] if row else [])
        for tally in targets:
            tally.add(event.usage)
        if row is not None and not event.usage.unsplit:
            row.last_ts = event.ts

    rate_total = 0
    for position in _slice(timestamps, now - 24 * 3600, now + 1):
        event = events[position]
        row = rows.get(event.account)
        hours_ago = int((now - event.ts) // 3600)
        if row is not None and 0 <= hours_ago < 24 and not event.usage.unsplit:
            row.hourly[23 - hours_ago] += usage_value(event.usage, metric)
        if now - event.ts <= 300 and not event.usage.unsplit:
            rate_total += event.usage.total
            if row is not None:
                row.rate += event.usage.total / 5.0

    for quota in quotas:
        row = rows.get(quota.account)
        if row is not None:
            row.quotas.append(quota_view(quota, now))
    for row in rows.values():
        row.quotas.sort(key=lambda view: WINDOW_SECONDS.get(view.window, 10**9))

    heat_days = [today - timedelta(days=offset) for offset in range(27, -2, -1)]
    heat_edges = [midnight(day, tz) for day in heat_days]
    heatmap = [[0] * 24 for _ in range(7)]
    for position in _slice(timestamps, heat_edges[0], heat_edges[-1]):
        event = events[position]
        if event.usage.unsplit:
            continue
        day_index = bisect_right(heat_edges, event.ts) - 1
        hour = min(23, int((event.ts - heat_edges[day_index]) // 3600))
        heatmap[heat_days[day_index].weekday()][hour] += usage_value(event.usage, metric)

    latest = [event for event in reversed(events[-(recent * 4) :]) if not event.usage.unsplit]
    return Snapshot(
        now=now,
        period=period,
        group=group,
        metric=metric,
        detail=detail,
        buckets=buckets,
        groups=groups,
        selected=selected,
        breakdown=breakdown,
        accounts=list(rows.values()),
        today=overall["today"],
        week=overall["week"],
        month=overall["month"],
        all=overall["all"],
        rate=rate_total / 5.0,
        recent=latest[:recent],
        heatmap=heatmap,
        first_ts=timestamps[0] if timestamps else None,
        last_ts=timestamps[-1] if timestamps else None,
        account_filter=account_filter,
    )
