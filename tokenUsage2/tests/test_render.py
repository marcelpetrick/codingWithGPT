# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

import re
from pathlib import Path

import pytest

from conftest import BERLIN, NOW
from tokenusage2.aggregate import GroupBy, Metric, Period, QuotaView, build_snapshot
from tokenusage2.demo import DemoSource
from tokenusage2.model import Account, Tool
from tokenusage2.render import (
    THEME_NAMES,
    Column,
    View,
    clean,
    clip,
    compact,
    duration,
    fit_columns,
    layout,
    mask,
    quota_cell,
    render,
    render_message,
    sparkline,
    stack_cells,
)
from tokenusage2.tui import bucket_count, take_snapshot

ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(scope="module")
def demo() -> DemoSource:
    return DemoSource(BERLIN, clock=lambda: NOW, days=40)


def frame(demo: DemoSource, view: View, width: int = 160, height: int = 48, **options) -> list[str]:
    count = bucket_count(view, width, height, len(demo.accounts()))
    snapshot = take_snapshot(demo, view, now=NOW, tz=BERLIN, count=count)
    return render(snapshot, view, width, height, tz=BERLIN, **options)


def visible(lines: list[str]) -> list[str]:
    return [ANSI.sub("", line) for line in lines]


@pytest.mark.parametrize("theme", THEME_NAMES)
@pytest.mark.parametrize(
    ("width", "height"), [(70, 16), (100, 30), (119, 40), (160, 48), (240, 70)]
)
def test_every_line_is_exactly_the_terminal_width(
    demo: DemoSource, theme: str, width: int, height: int
) -> None:
    lines = visible(frame(demo, View(theme=theme), width, height))
    assert len(lines) == height
    assert {len(line) for line in lines} == {width}


def test_plain_frame_shows_every_panel(demo: DemoSource) -> None:
    text = "\n".join(frame(demo, View(theme="plain"), mode="DEMO", status="status!"))
    assert "\x1b" not in text
    for needle in (
        "tokenUsage2",
        "DEMO",
        "Accounts",
        "Tokens per day",
        "Live feed",
        "you@example.com",
        "codex-work",
        "5h quota",
        "claude-opus-5",
        "status!",
        "cache hit",
    ):
        assert needle in text


def test_retained_history_is_drawn_hatched() -> None:
    source = DemoSource(BERLIN, clock=lambda: NOW, days=90)
    text = "\n".join(frame(source, View(theme="plain", period=Period.MONTH)))
    assert "▒ retained daily total (split unknown)" in text
    assert "▒" in text.split("Tokens per month")[1]


def test_colour_themes_emit_styles(demo: DemoSource) -> None:
    assert "\x1b[0;" in frame(demo, View(theme="default"))[0]
    assert "48;5;234" in "".join(frame(demo, View(theme="midnight")))


def test_redaction_masks_identities(demo: DemoSource) -> None:
    text = "\n".join(frame(demo, View(theme="plain", redact=True)))
    assert "you@example.com" not in text
    assert "y…@e….com" in text


def test_tiny_terminals_get_a_message(demo: DemoSource) -> None:
    lines = frame(demo, View(theme="plain"), 50, 10)
    assert len(lines) == 10
    assert {len(line) for line in lines} == {50}
    assert any("terminal too small" in line for line in lines)


def test_overlays(demo: DemoSource) -> None:
    help_text = "\n".join(frame(demo, View(theme="plain", help=True)))
    assert "rescan now" in help_text
    sources = "\n".join(frame(demo, View(theme="plain", sources=True), sources=["hello sources"]))
    assert "hello sources" in sources


def test_heatmap_replaces_the_feed(demo: DemoSource) -> None:
    text = "\n".join(frame(demo, View(theme="plain", heatmap=True)))
    assert "Activity" in text
    assert "Thu" in text
    assert "Live feed" not in text


def test_every_combination_renders(demo: DemoSource) -> None:
    for period in Period:
        for group in GroupBy:
            for metric in Metric:
                view = View(theme="plain", period=period, group=group, metric=metric, detail=group)
                lines = frame(demo, view, 130, 40)
                assert {len(line) for line in lines} == {130}
    week = "\n".join(frame(demo, View(theme="plain", period=Period.WEEK)))
    assert "Tokens per week" in week


def test_empty_data_renders_placeholders() -> None:
    snapshot = build_snapshot([], [], [], now=NOW, tz=BERLIN)
    text = "\n".join(render(snapshot, View(theme="plain"), 130, 40, tz=BERLIN))
    for needle in (
        "no accounts found",
        "no usage in this range",
        "no usage in this bucket",
        "waiting for the first request",
    ):
        assert needle in text


def test_many_accounts_are_summarised() -> None:
    accounts = [Account(f"x{i}", Tool.CLAUDE, Path("/x"), f"acct{i}") for i in range(20)]
    snapshot = build_snapshot([], accounts, [], now=NOW, tz=BERLIN)
    text = "\n".join(render(snapshot, View(theme="plain"), 130, 30, tz=BERLIN))
    assert "more — press a to filter" in text


def test_layout() -> None:
    assert layout(160, 48, 3).right is not None
    narrow = layout(100, 40, 3)
    assert narrow.right is None
    assert narrow.left is not None
    short = layout(100, 20, 3)
    assert short.timeline is not None
    assert short.left is None
    assert layout(100, 12, 3).timeline is None
    assert layout(100, 12, 3).capacity == 1


def test_text_helpers() -> None:
    assert [compact(v) for v in (0, 999, 999.6, 12_345, 99_950, 1_234_567, 2.5e9, 3e13)] == [
        "0",
        "999",
        "1.0k",
        "12.3k",
        "100k",
        "1.2M",
        "2.5B",
        "30.0T",
    ]
    assert [duration(s) for s in (-5, 5, 125, 3900, 90000, 115 * 86400)] == [
        "0s",
        "5s",
        "2m",
        "1h05m",
        "1d01h",
        "115d",
    ]
    assert mask("you@example.com") == "y…@e….com"
    assert mask("x@localhost") == "x…@localhost"
    assert mask("API key") == "API key"
    assert mask(None) == ""
    assert clean("a\tb") == "a b"
    assert clean("漢字") == "??"
    assert clean("é") == "e"
    assert clip("hello", 3) == "he…"
    assert clip("x", 0) == ""
    assert sparkline([0, 1, 8], 3) == " ▁█"
    assert sparkline([0, 0], 2) == "  "
    assert sparkline([1, 2], 0) == ""


def test_stack_cells() -> None:
    assert stack_cells([], 1.0, 4) == []
    assert stack_cells([(8, "s0", False)], 1.0, 4) == [("█", "s0")]
    assert stack_cells([(4, "s0", False)], 1.0, 4) == [("▄", "s0")]
    assert stack_cells([(0.1, "s0", False)], 1.0, 4) == [("▁", "s0")]
    assert stack_cells([(8, "s0", False), (8, "s1", True)], 1.0, 4) == [("█", "s0"), ("▒", "s1")]
    assert stack_cells([(4, "s1", True)], 1.0, 4) == [("░", "s1")]


def test_fit_columns_keeps_priorities_and_flexes() -> None:
    columns = [
        Column("a", 5, priority=0, flex=True),
        Column("b", 5, priority=2),
        Column("c", 5, priority=1),
    ]
    assert fit_columns(columns, 11) == [(0, 5), (2, 5)]
    assert fit_columns(columns, 20) == [(0, 8), (1, 5), (2, 5)]


def test_quota_cell_states() -> None:
    assert quota_cell(None, NOW) == [("—", "dim")]
    rolled = quota_cell(QuotaView("5h", 0.0, None, NOW, "x", True), NOW)
    assert "reset" in "".join(text for text, _ in rolled)
    high = quota_cell(QuotaView("5h", 92.0, NOW + 3900, NOW - 7200, "x", False), NOW)
    assert high[0][1] == "bad"
    assert high[2][1] == "dim"
    assert high[3][0].strip() == "1h05m"
    unknown_reset = quota_cell(QuotaView("5h", 50.0, None, NOW, "x", False), NOW)
    assert unknown_reset[0][1] == "ok"


def test_series_colours_are_stable() -> None:
    view = View()
    first = view.series("x")
    view.series("y")
    assert view.series("x") == first == "s0"


def test_render_message() -> None:
    lines = render_message(40, 5, ["title", "sub"], "plain")
    assert len(lines) == 5
    assert "title" in lines[1]
    assert "sub" in lines[2]
