# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""The live terminal loop: keys, refresh cadence, resize, and clean teardown."""

import os
import select
import signal
import sys
import termios
import time
import tty
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Protocol, TextIO

from tokenusage2.aggregate import GroupBy, Metric, Period, Snapshot, build_snapshot, periods_back
from tokenusage2.ingest import ScanReport
from tokenusage2.live import Source
from tokenusage2.render import THEME_NAMES, View, layout, render, render_message

PERIOD_KEYS = {
    "d": Period.DAY,
    "1": Period.DAY,
    "w": Period.WEEK,
    "2": Period.WEEK,
    "m": Period.MONTH,
    "3": Period.MONTH,
}
MAX_BUCKETS = {Period.DAY: 120, Period.WEEK: 52, Period.MONTH: 36}
MIN_BUCKETS = {Period.DAY: 14, Period.WEEK: 8, Period.MONTH: 6}
INTERVALS = (0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
GROUPS = (GroupBy.ACCOUNT, GroupBy.TOOL, GroupBy.BACKEND, GroupBy.MODEL, GroupBy.PROJECT)
DETAILS = (GroupBy.MODEL, GroupBy.PROJECT, GroupBy.BACKEND, GroupBy.ACCOUNT, GroupBy.TOOL)
SEQUENCES = {
    "\x1b[D": "left",
    "\x1bOD": "left",
    "\x1b[C": "right",
    "\x1bOC": "right",
    "\x1b[A": "up",
    "\x1b[B": "down",
    "\x1b[H": "home",
    "\x1bOH": "home",
    "\x1b[1~": "home",
    "\x1b[7~": "home",
    "\x1b[F": "end",
    "\x1bOF": "end",
    "\x1b[4~": "end",
    "\x1b[8~": "end",
    "\x1b[5~": "pgup",
    "\x1b[6~": "pgdn",
    "\x1bOP": "f1",
    "\x1b[11~": "f1",
}
_BY_LENGTH = sorted(SEQUENCES.items(), key=lambda item: -len(item[0]))


def decode_keys(data: str) -> list[str]:
    keys, index = [], 0
    while index < len(data):
        if data[index] != "\x1b":
            keys.append(data[index])
            index += 1
            continue
        for sequence, name in _BY_LENGTH:
            if data.startswith(sequence, index):
                keys.append(name)
                index += len(sequence)
                break
        else:
            if data.startswith("\x1b[", index):
                index += 2
                while index < len(data) and not "@" <= data[index] <= "~":
                    index += 1
                index += 1
            else:
                keys.append("esc")
                index += 1
    return keys


def _cycle[T](options: Sequence[T], current: T) -> T:
    position = options.index(current) if current in options else -1
    return options[(position + 1) % len(options)]


@dataclass(slots=True)
class Controller:
    view: View

    def handle(self, key: str, accounts: Sequence[str], page: int = 10) -> str | None:
        """Apply one key to the view; return ``quit`` or ``rescan`` when asked."""
        view = self.view
        if key in {"q", "Q", "\x03"}:
            return "quit"
        if key == "r":
            return "rescan"
        if key == "esc":
            view.help = view.sources = False
        elif key in {"?", "f1"}:
            view.help, view.sources = not view.help, False
        elif key == "s":
            view.sources, view.help = not view.sources, False
        elif key in PERIOD_KEYS:
            if PERIOD_KEYS[key] is not view.period:
                view.period, view.cursor = PERIOD_KEYS[key], 0
        elif key in {"left", "[", ","}:
            view.cursor += 1
        elif key in {"right", "]", "."}:
            view.cursor = max(0, view.cursor - 1)
        elif key == "pgup":
            view.cursor += page
        elif key == "pgdn":
            view.cursor = max(0, view.cursor - page)
        elif key == "home":
            view.cursor = 10**6
        elif key == "end":
            view.cursor = 0
        elif key == "g":
            view.group = _cycle(GROUPS, view.group)
        elif key == "b":
            view.detail = _cycle(DETAILS, view.detail)
        elif key == "v":
            view.metric = _cycle(tuple(Metric), view.metric)
        elif key == "a":
            view.account = _cycle((None, *accounts), view.account)
        elif key == "h":
            view.heatmap = not view.heatmap
        elif key == "t":
            view.theme = _cycle(THEME_NAMES, view.theme)
        elif key == "x":
            view.redact = not view.redact
        elif key == "p":
            view.paused = not view.paused
        elif key in {"+", "="}:
            view.interval = next((i for i in INTERVALS if i > view.interval), INTERVALS[-1])
        elif key in {"-", "_"}:
            view.interval = next(
                (i for i in reversed(INTERVALS) if i < view.interval), INTERVALS[0]
            )
        return None


def take_snapshot(source: Source, view: View, *, now: float, tz: tzinfo, count: int) -> Snapshot:
    """Build the frame's snapshot, first clamping the cursor to the loaded history."""
    span = data_span(source, view, now, tz)
    view.cursor = min(view.cursor, max(0, (span or 1) - 1))
    return build_snapshot(
        source.events(),
        source.accounts(),
        source.quotas(),
        now=now,
        tz=tz,
        period=view.period,
        group=view.group,
        metric=view.metric,
        detail=view.detail,
        cursor=view.cursor,
        count=count,
        account_filter=view.account,
        archived=source.archived(),
        running=source.running(),
        backend=source.backend_of,
        lifetimes=source.lifetimes(),
    )


def data_span(source: Source, view: View, now: float, tz: tzinfo) -> int | None:
    """How many buckets the loaded history covers, oldest event to now."""
    events = source.events()
    if not events:
        return None
    return (
        periods_back(
            view.period,
            datetime.fromtimestamp(events[0].ts, tz).date(),
            datetime.fromtimestamp(now, tz).date(),
        )
        + 1
    )


def bucket_count(
    view: View, width: int, height: int, accounts: int, span: int | None = None
) -> int:
    """Buckets to show: as many as fit, but no more than the history covers."""
    wanted = MAX_BUCKETS[view.period] if span is None else max(MIN_BUCKETS[view.period], span)
    capacity = layout(width, height, accounts).capacity
    return max(1, min(capacity, MAX_BUCKETS[view.period], wanted))


def status_text(report: ScanReport, source: Source, view: View) -> str:
    refresh = "paused" if view.paused else f"every {view.interval:g}s"
    return (
        f"{len(source.events()):,} events · scan {report.seconds * 1000:.0f} ms · refresh {refresh}"
    )


class Screen(Protocol):
    def size(self) -> tuple[int, int]: ...
    def draw(self, lines: Sequence[str]) -> None: ...
    def read_keys(self, timeout: float) -> list[str]: ...


def _terminate(signum: int, frame: object) -> None:
    raise SystemExit(128 + signum)


class Terminal:
    """Alternate screen, cbreak input, hidden cursor, no autowrap — all restored on exit."""

    def __init__(self, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self.fd = stdin.fileno()
        self.saved: list | None = None

    def __enter__(self) -> Terminal:
        self.saved = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.previous = signal.signal(signal.SIGTERM, _terminate)
        self.stdout.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[2J")
        self.stdout.flush()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stdout.write("\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l")
        self.stdout.flush()
        signal.signal(signal.SIGTERM, self.previous)
        if self.saved is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)

    def size(self) -> tuple[int, int]:
        size = os.get_terminal_size(self.stdout.fileno())
        return size.columns, size.lines

    def draw(self, lines: Sequence[str]) -> None:
        self.stdout.write("\x1b[H" + "\r\n".join(lines))
        self.stdout.flush()

    def read_keys(self, timeout: float) -> list[str]:
        ready, _, _ = select.select([self.fd], [], [], timeout)
        if not ready:
            return []
        return decode_keys(os.read(self.fd, 64).decode(errors="ignore"))


def run(
    source: Source,
    view: View,
    tz: tzinfo,
    *,
    screen: Screen | None = None,
    clock: Callable[[], float] = time.time,
) -> int:
    if screen is None:
        try:
            with Terminal() as terminal:
                return _loop(source, view, tz, terminal, clock)
        except KeyboardInterrupt:
            return 0
    return _loop(source, view, tz, screen, clock)


def _loop(
    source: Source, view: View, tz: tzinfo, screen: Screen, clock: Callable[[], float]
) -> int:
    controller = Controller(view)
    width, height = screen.size()

    def progress(done: int, total: int) -> None:
        screen.draw(
            render_message(
                width,
                height,
                [
                    "tokenUsage2",
                    f"indexing {done:,} / {total:,} files",
                    "the first run builds the archive — later starts are instant",
                ],
                view.theme,
            )
        )

    screen.draw(
        render_message(width, height, ["tokenUsage2", "discovering agent homes…"], view.theme)
    )
    report = source.scan(progress)
    next_scan = clock() + view.interval
    memo: tuple | None = None
    snapshot: Snapshot | None = None
    drawn_second = -1
    dirty = True
    while True:
        now = clock()
        if screen.size() != (width, height):
            width, height = screen.size()
            dirty = True
        if not view.paused and now >= next_scan:
            report = source.scan()
            next_scan = now + view.interval
            dirty = dirty or report.changed
        accounts = source.accounts()
        count = bucket_count(view, width, height, len(accounts), data_span(source, view, now, tz))
        quotas = tuple((q.account, q.window, q.observed_at) for q in source.quotas())
        key = (
            source.generation(),
            quotas,
            view.period,
            view.group,
            view.metric,
            view.detail,
            view.cursor,
            view.account,
            count,
            tuple(sorted(source.running().items())),
            len(accounts),
            int(now // 5),
        )
        if key != memo or snapshot is None:
            snapshot = take_snapshot(source, view, now=now, tz=tz, count=count)
            memo = key
            dirty = True
        else:
            snapshot.now = now
        if dirty or int(now) != drawn_second:
            screen.draw(
                render(
                    snapshot,
                    view,
                    width,
                    height,
                    tz=tz,
                    status=status_text(report, source, view),
                    sources=source.sources() if view.sources else (),
                    mode="PAUSED" if view.paused else source.mode,
                )
            )
            drawn_second, dirty = int(now), False
        for pressed in screen.read_keys(0.2):
            action = controller.handle(pressed, [account.id for account in accounts], count)
            if action == "quit":
                return 0
            if action == "rescan":
                source.rediscover()
                report = source.scan()
                next_scan = clock() + view.interval
            dirty = True
