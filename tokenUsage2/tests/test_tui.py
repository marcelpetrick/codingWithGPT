# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

import fcntl
import itertools
import os
import select
import struct
import termios
import time
from collections.abc import Sequence

import pytest

from conftest import BERLIN, NOW
from tokenusage2.aggregate import GroupBy, Metric, Period
from tokenusage2.demo import DemoSource
from tokenusage2.render import View
from tokenusage2.tui import (
    Controller,
    Terminal,
    _terminate,
    bucket_count,
    decode_keys,
    run,
    take_snapshot,
)


def test_decode_keys() -> None:
    assert decode_keys("\x1b[Dq") == ["left", "q"]
    assert decode_keys("\x1b") == ["esc"]
    assert decode_keys("\x1b[99zq") == ["q"]
    assert decode_keys("\x1b[5~\x1bOP") == ["pgup", "f1"]


def test_controller_maps_every_key() -> None:
    view = View()
    control = Controller(view)
    assert control.handle("q", []) == "quit"
    assert control.handle("r", []) == "rescan"
    control.handle("w", [])
    assert view.period is Period.WEEK
    control.handle("left", [])
    control.handle("[", [])
    assert view.cursor == 2
    control.handle("right", [])
    assert view.cursor == 1
    control.handle("2", [])
    assert view.cursor == 1
    control.handle("m", [])
    assert (view.period, view.cursor) == (Period.MONTH, 0)
    control.handle("pgup", [], page=5)
    assert view.cursor == 5
    control.handle("pgdn", [], page=10)
    assert view.cursor == 0
    control.handle("home", [])
    assert view.cursor == 10**6
    control.handle("end", [])
    assert view.cursor == 0
    control.handle("g", [])
    control.handle("b", [])
    control.handle("v", [])
    assert (view.group, view.detail, view.metric) == (GroupBy.TOOL, GroupBy.PROJECT, Metric.FRESH)
    control.handle("a", ["x", "y"])
    assert view.account == "x"
    control.handle("a", ["x", "y"])
    control.handle("a", ["x", "y"])
    assert view.account is None
    for key in "htxp":
        control.handle(key, [])
    assert (view.heatmap, view.theme, view.redact, view.paused) == (True, "midnight", True, True)
    control.handle("+", [])
    assert view.interval == 5.0
    for _ in range(4):
        control.handle("-", [])
    assert view.interval == 0.5
    for _ in range(9):
        control.handle("+", [])
    assert view.interval == 30.0
    control.handle("?", [])
    assert view.help
    control.handle("s", [])
    assert view.sources
    assert not view.help
    control.handle("esc", [])
    assert not view.sources
    assert control.handle("unknown", []) is None


class FakeScreen:
    def __init__(self, batches: Sequence[object]) -> None:
        self.batches = list(batches)
        self.frames: list[list[str]] = []
        self.current = (140, 42)

    def size(self) -> tuple[int, int]:
        return self.current

    def draw(self, lines: Sequence[str]) -> None:
        self.frames.append(list(lines))

    def read_keys(self, timeout: float) -> list[str]:
        if not self.batches:
            return ["q"]
        batch = self.batches.pop(0)
        if batch == "resize":
            self.current = (100, 30)
            return []
        return list(batch)  # type: ignore[call-overload]


def test_run_loop_draws_reacts_and_quits() -> None:
    ticks = itertools.count()

    def clock() -> float:
        return NOW + next(ticks) * 0.7

    source = DemoSource(BERLIN, clock=clock, days=20)
    view = View(theme="plain")
    screen = FakeScreen([["w"], ["left"], [], "resize", ["?"], ["esc"], ["s"], ["r"], ["p"], []])
    assert run(source, view, BERLIN, screen=screen, clock=clock) == 0
    texts = ["\n".join(lines) for lines in screen.frames]
    assert any("discovering agent homes" in text for text in texts)
    assert any("indexing 1 / 1 files" in text for text in texts)
    assert any("Tokens per week" in text for text in texts)
    assert any("rescan now" in text for text in texts)
    assert any("demo mode" in text for text in texts)
    assert any("PAUSED" in text for text in texts)
    assert {len(line) for line in screen.frames[-1]} == {100}
    assert view.cursor == 1


def test_take_snapshot_clamps_the_cursor_to_the_data() -> None:
    source = DemoSource(BERLIN, clock=lambda: NOW, days=20)
    view = View(cursor=10**6)
    take_snapshot(source, view, now=NOW, tz=BERLIN, count=10)
    assert 15 <= view.cursor <= 20


def test_bucket_count_follows_width_and_history() -> None:
    view = View()
    assert bucket_count(view, 160, 48, 4) == 75
    assert bucket_count(view, 160, 48, 4, span=3) == 14
    assert bucket_count(view, 160, 48, 4, span=30) == 30
    assert bucket_count(View(period=Period.MONTH), 160, 48, 4, span=200) == 36


def test_terminal_session_restores_the_tty() -> None:
    master, slave = os.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    before = termios.tcgetattr(slave)
    with open(slave, closefd=False) as stdin, open(slave, "w", closefd=False) as stdout:
        with Terminal(stdin, stdout) as terminal:
            assert terminal.size() == (80, 24)
            terminal.draw(["ab", "cd"])
            os.write(master, b"\x1b[Dq")
            assert terminal.read_keys(1.0) == ["left", "q"]
            assert terminal.read_keys(0.0) == []
        assert termios.tcgetattr(slave) == before
    # A pty hands output over in chunks: read until the teardown arrives.
    output, deadline = b"", time.monotonic() + 2.0
    while b"\x1b[?1049l" not in output and time.monotonic() < deadline:
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            output += os.read(master, 65536)
    assert b"\x1b[?1049h" in output
    assert b"\x1b[?1049l" in output
    os.close(master)
    os.close(slave)


def test_sigterm_handler_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as stop:
        _terminate(15, None)
    assert stop.value.code == 143
