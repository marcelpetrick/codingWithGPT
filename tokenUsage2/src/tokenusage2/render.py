# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Frame rendering: panels drawn onto a cell canvas, emitted as ANSI or plain text.

Only single-width glyphs are drawn and user-controlled strings are cleaned to
single-width characters, so every emitted line is exactly ``width`` cells and
a frame can be asserted on as plain strings in tests.
"""

import math
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, tzinfo

from tokenusage2.aggregate import (
    METRIC_HELP,
    AccountRow,
    GroupBy,
    Metric,
    Period,
    QuotaView,
    Snapshot,
)
from tokenusage2.model import Tool

MIN_WIDTH, MIN_HEIGHT = 70, 16
AXIS = 8
BLOCKS = "▁▂▃▄▅▆▇█"
SPARK = " ▁▂▃▄▅▆▇█"
HEAT = " ░▒▓█"
SERIES = 8
TOOL_STYLE = {Tool.CLAUDE: "claude", Tool.CODEX: "codex", Tool.OPENCODE: "opencode"}

_DEFAULT = {
    "base": "",
    "text": "38;5;252",
    "dim": "38;5;244",
    "border": "38;5;61",
    "title": "1;38;5;117",
    "accent": "1;38;5;214",
    "hi": "1;38;5;16;48;5;117",
    "ok": "38;5;114",
    "warn": "38;5;221",
    "bad": "1;38;5;203",
    "header": "1;38;5;16;48;5;117",
    "claude": "38;5;209",
    "codex": "38;5;75",
    "opencode": "38;5;114",
    "s0": "38;5;209",
    "s1": "38;5;75",
    "s2": "38;5;114",
    "s3": "38;5;177",
    "s4": "38;5;221",
    "s5": "38;5;45",
    "s6": "38;5;204",
    "s7": "38;5;145",
}
_AMBER = {
    "base": "",
    "text": "38;5;223",
    "dim": "38;5;137",
    "border": "38;5;130",
    "title": "1;38;5;214",
    "accent": "1;38;5;228",
    "hi": "1;38;5;52;48;5;214",
    "ok": "38;5;220",
    "warn": "38;5;208",
    "bad": "1;38;5;196",
    "header": "1;38;5;52;48;5;214",
    "claude": "38;5;215",
    "codex": "38;5;221",
    "opencode": "38;5;180",
    "s0": "38;5;214",
    "s1": "38;5;223",
    "s2": "38;5;172",
    "s3": "38;5;229",
    "s4": "38;5;208",
    "s5": "38;5;180",
    "s6": "38;5;130",
    "s7": "38;5;187",
}


def _painted(theme: Mapping[str, str], background: str) -> dict[str, str]:
    return {
        name: code if "48;5" in code else ";".join(filter(None, (code, background)))
        for name, code in theme.items()
    }


THEMES: dict[str, dict[str, str]] = {
    "default": _DEFAULT,
    "midnight": _painted(_DEFAULT, "48;5;234"),
    "amber": _AMBER,
    "plain": {},
}
THEME_NAMES = tuple(THEMES)

HELP_LINES = (
    "q          quit",
    "d w m      daily, weekly or monthly buckets (also 1 2 3)",
    "← → [ ]    move the bucket cursor (scrolls back through history)",
    "PgUp PgDn  page back / forward     Home  oldest data     End  current bucket",
    "g          colour the timeline by account, tool, backend or model",
    "b          break the selected bucket down by model, project, backend or account",
    "v          metric: all tokens incl. cache, fresh input+output, output only",
    "a          filter to one account (cycles, then back to all)",
    "h          swap the live feed for the hour × weekday heatmap",
    "s          sources: discovered homes, files, quota snapshots, reconciliation",
    "t          theme (default, midnight, amber, plain)",
    "x          redact e-mail addresses",
    "r          rescan now (also re-runs discovery)",
    "p          pause live refresh        + / -   refresh interval",
    "? or F1    this help",
)
HINTS = (
    ("q", "quit"),
    ("d/w/m", "period"),
    ("←→", "select"),
    ("g", "group"),
    ("b", "breakdown"),
    ("v", "metric"),
    ("a", "account"),
    ("h", "heatmap"),
    ("s", "sources"),
    ("t", "theme"),
    ("x", "redact"),
    ("?", "help"),
)


# --- text helpers ------------------------------------------------------------


def clean(text: str) -> str:
    """Make a user-controlled string safe and single-width."""
    if text.isascii() and text.isprintable():
        return text
    out = []
    for char in text:
        if char < " " or char == "\x7f":
            out.append(" ")
        elif unicodedata.category(char) in {"Mn", "Me", "Cf", "Cc"}:
            continue
        elif unicodedata.east_asian_width(char) in {"W", "F"}:
            out.append("?")
        else:
            out.append(char)
    return "".join(out)


def clip(text: str, width: int) -> str:
    if width <= 0:
        return ""
    return text if len(text) <= width else text[: width - 1] + "…"


def compact(value: float) -> str:
    number = float(value)
    if abs(number) < 999.5:
        return f"{number:.0f}"
    for suffix, scale in (("k", 1e3), ("M", 1e6), ("B", 1e9), ("T", 1e12)):
        scaled = number / scale
        if abs(scaled) < 999.5 or suffix == "T":
            return f"{scaled:.1f}{suffix}" if abs(scaled) < 99.95 else f"{scaled:.0f}{suffix}"
    raise AssertionError("unreachable")  # pragma: no cover


def duration(seconds: float) -> str:
    value = max(0, int(seconds))
    if value < 60:
        return f"{value}s"
    if value < 3600:
        return f"{value // 60}m"
    if value < 86400:
        return f"{value // 3600}h{value % 3600 // 60:02d}m"
    if value < 10 * 86400:
        return f"{value // 86400}d{value % 86400 // 3600:02d}h"
    return f"{value // 86400}d"


def mask(identity: str | None) -> str:
    if not identity or "@" not in identity:
        return identity or ""
    local, _, domain = identity.partition("@")
    head, dot, tld = domain.rpartition(".")
    return f"{local[:1]}…@{head[:1] + '…' if head else ''}{dot}{tld}"


def sparkline(values: Sequence[int], width: int) -> str:
    values = list(values)[-width:] if width > 0 else []
    peak = max(values, default=0)
    if not peak:
        return " " * len(values)
    return "".join(SPARK[0 if v <= 0 else max(1, round(v / peak * 8))] for v in values)


# --- canvas ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


class Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.chars = [[" "] * width for _ in range(height)]
        self.styles = [["base"] * width for _ in range(height)]

    def put(self, x: int, y: int, text: str, style: str = "text", limit: int | None = None) -> int:
        if not 0 <= y < self.height:
            return x + len(text)
        end = self.width if limit is None else min(self.width, x + limit)
        for char in text:
            if x >= end:
                break
            if x >= 0:
                self.chars[y][x] = char
                self.styles[y][x] = style
            x += 1
        return x

    def fill(self, rect: Rect, style: str = "base", char: str = " ") -> None:
        for row in range(rect.y, rect.y + rect.h):
            self.put(rect.x, row, char * rect.w, style)

    def box(self, rect: Rect, title: str = "", right: str = "", style: str = "border") -> None:
        x, y, w, h = rect.x, rect.y, rect.w, rect.h
        if w < 2 or h < 2:
            return
        self.put(x, y, "╭" + "─" * (w - 2) + "╮", style)
        for row in range(y + 1, y + h - 1):
            self.put(x, row, "│", style)
            self.put(x + w - 1, row, "│", style)
        self.put(x, y + h - 1, "╰" + "─" * (w - 2) + "╯", style)
        shown = clip(f" {clean(title)} ", w - 4) if title else ""
        self.put(x + 2, y, shown, "title")
        note = f" {right} "
        if right and len(shown) + len(note) + 6 <= w:
            self.put(x + w - 2 - len(note), y, note, "dim")

    def lines(self, theme: Mapping[str, str]) -> list[str]:
        if not theme:
            return ["".join(row) for row in self.chars]
        out = []
        for chars, styles in zip(self.chars, self.styles, strict=True):
            parts, current = [], None
            for char, style in zip(chars, styles, strict=True):
                if style != current:
                    code = theme.get(style, theme.get("text", ""))
                    parts.append(f"\x1b[0;{code}m" if code else "\x1b[0m")
                    current = style
                parts.append(char)
            parts.append("\x1b[0m")
            out.append("".join(parts))
        return out


# --- view state and layout ---------------------------------------------------


@dataclass(slots=True)
class View:
    """Presentation state; the TUI mutates it from key presses."""

    period: Period = Period.DAY
    group: GroupBy = GroupBy.ACCOUNT
    metric: Metric = Metric.TOTAL
    detail: GroupBy = GroupBy.MODEL
    cursor: int = 0
    theme: str = "default"
    redact: bool = False
    help: bool = False
    sources: bool = False
    heatmap: bool = False
    paused: bool = False
    interval: float = 2.0
    account: str | None = None
    colors: dict[str, int] = field(default_factory=dict)

    def series(self, name: str) -> str:
        index = self.colors.get(name)
        if index is None:
            index = self.colors[name] = len(self.colors)
        return f"s{index % SERIES}"


@dataclass(frozen=True, slots=True)
class Layout:
    header: Rect
    accounts: Rect
    timeline: Rect | None
    left: Rect | None
    right: Rect | None
    footer: Rect
    account_rows: int

    @property
    def capacity(self) -> int:
        """How many timeline buckets fit, at two cells per bar minimum."""
        if self.timeline is None:
            return 1
        return max(1, (self.timeline.w - 2 - AXIS) // 2)


def layout(width: int, height: int, accounts: int) -> Layout:
    account_rows = max(1, min(accounts, max(1, (height - 2) // 4)))
    accounts_rect = Rect(0, 1, width, account_rows + 3)
    rest_y = accounts_rect.y + accounts_rect.h
    rest_h = height - 1 - rest_y
    timeline = left = right = None
    if rest_h >= 18:
        timeline_h = max(9, rest_h * 11 // 20)
        timeline = Rect(0, rest_y, width, timeline_h)
        bottom = Rect(0, rest_y + timeline_h, width, rest_h - timeline_h)
        if width >= 120:
            left_w = width * 11 // 20
            left = Rect(0, bottom.y, left_w, bottom.h)
            right = Rect(left_w, bottom.y, width - left_w, bottom.h)
        else:
            left = bottom
    elif rest_h >= 6:
        timeline = Rect(0, rest_y, width, rest_h)
    return Layout(
        Rect(0, 0, width, 1),
        accounts_rect,
        timeline,
        left,
        right,
        Rect(0, height - 1, width, 1),
        account_rows,
    )


# --- tables ------------------------------------------------------------------

type Fragment = tuple[str, str]
type Cell = Fragment | list[Fragment]


@dataclass(frozen=True, slots=True)
class Column:
    header: str
    width: int
    align: str = ">"
    priority: int = 0
    flex: bool = False


def fit_columns(columns: Sequence[Column], available: int) -> list[tuple[int, int]]:
    """Pick the most important columns that fit; the flex column takes the rest."""
    chosen: list[int] = []
    used = 0
    for index in sorted(range(len(columns)), key=lambda i: columns[i].priority):
        need = columns[index].width + (1 if chosen else 0)
        if used + need <= available:
            chosen.append(index)
            used += need
    chosen.sort()
    widths = {index: columns[index].width for index in chosen}
    flexible = [index for index in chosen if columns[index].flex]
    if flexible:
        widths[flexible[0]] += available - used
    return [(index, widths[index]) for index in chosen]


def draw_cells(
    canvas: Canvas,
    x: int,
    y: int,
    fitted: Sequence[tuple[int, int]],
    columns: Sequence[Column],
    cells: Sequence[Cell],
) -> None:
    for index, width in fitted:
        cell = cells[index]
        fragments = [cell] if isinstance(cell, tuple) else list(cell)
        if len(fragments) == 1:
            text, style = fragments[0]
            fragments = [(clip(text, width), style)]
        length = min(width, sum(len(text) for text, _ in fragments))
        cursor = x + (width - length if columns[index].align == ">" else 0)
        remaining = width
        for text, style in fragments:
            piece = text[: max(0, remaining)]
            canvas.put(cursor, y, piece, style)
            cursor += len(piece)
            remaining -= len(piece)
        x += width + 1


def draw_header_row(
    canvas: Canvas, x: int, y: int, fitted: Sequence[tuple[int, int]], columns: Sequence[Column]
) -> None:
    draw_cells(canvas, x, y, fitted, columns, [(column.header, "dim") for column in columns])


# --- panels ------------------------------------------------------------------

ACCOUNT_COLUMNS = (
    Column("", 1, "<", 0),
    Column("account", 12, "<", 0, flex=True),
    Column("identity", 26, "<", 7),
    Column("plan", 8, "<", 8),
    Column("today", 7, ">", 1),
    Column("week", 7, ">", 2),
    Column("month", 7, ">", 3),
    Column("all", 7, ">", 9),
    Column("last 24h", 24, "<", 5),
    Column("5h quota", 19, "<", 4),
    Column("weekly quota", 19, "<", 4),
    Column("idle", 6, ">", 6),
    Column("rate", 7, ">", 6),
)


def quota_cell(view: QuotaView | None, now: float) -> list[Fragment]:
    if view is None:
        return [("—", "dim")]
    used = max(0.0, min(100.0, view.used))
    filled = round(used / 100 * 8)
    level = "ok" if used < 60 else "warn" if used < 85 else "bad"
    stale = now - view.observed_at > 3600
    if view.rolled:
        countdown = "reset"
    elif view.resets_at is not None:
        countdown = duration(view.resets_at - now)
    else:
        countdown = ""
    return [
        ("█" * filled, level),
        ("░" * (8 - filled), "dim"),
        (f" {used:3.0f}%", "dim" if stale else "text"),
        (f" {countdown:>5}", "dim"),
    ]


def account_cells(row: AccountRow, snapshot: Snapshot, view: View) -> list[Cell]:
    style = TOOL_STYLE[row.tool]
    metric = snapshot.metric
    quotas = {quota.window: quota for quota in row.quotas}
    identity = mask(row.identity) if view.redact else row.identity or "—"
    idle = duration(snapshot.now - row.last_ts) if row.last_ts else "—"
    return [
        ("●", style) if row.running else ("·", "dim"),
        (clean(row.label), "dim" if row.archived else style),
        (clean(identity), "text"),
        (clean(row.plan or "—"), "dim"),
        (compact(row.today.value(metric)), "text"),
        (compact(row.week.value(metric)), "text"),
        (compact(row.month.value(metric)), "text"),
        (compact(row.all.value(metric)), "dim"),
        (sparkline(row.hourly, 24), style),
        quota_cell(quotas.get("5h"), snapshot.now),
        quota_cell(quotas.get("week"), snapshot.now),
        (idle, "dim"),
        (f"{compact(row.rate)}/m" if row.rate else "—", "accent" if row.rate else "dim"),
    ]


def draw_accounts(canvas: Canvas, rect: Rect, snapshot: Snapshot, view: View, rows: int) -> None:
    running = sum(1 for row in snapshot.accounts if row.running)
    canvas.box(rect, "Accounts", f"{len(snapshot.accounts)} found · {running} running")
    fitted = fit_columns(ACCOUNT_COLUMNS, rect.w - 4)
    draw_header_row(canvas, rect.x + 2, rect.y + 1, fitted, ACCOUNT_COLUMNS)
    accounts = snapshot.accounts
    if not accounts:
        canvas.put(rect.x + 2, rect.y + 2, "no accounts found — run `tokenusage2 --doctor`", "warn")
        return
    shown = accounts if len(accounts) <= rows else accounts[: rows - 1]
    for offset, row in enumerate(shown):
        draw_cells(
            canvas,
            rect.x + 2,
            rect.y + 2 + offset,
            fitted,
            ACCOUNT_COLUMNS,
            account_cells(row, snapshot, view),
        )
    if len(shown) < len(accounts):
        canvas.put(
            rect.x + 2,
            rect.y + 2 + len(shown),
            f"+{len(accounts) - len(shown)} more — press a to filter",
            "dim",
        )


def stack_cells(
    segments: Sequence[tuple[float, str, bool]], scale: float, rows: int
) -> list[tuple[str, str]]:
    """Glyph and style per row (bottom first) of one stacked bar."""
    bounds, top = [], 0.0
    for value, style, hatched in segments:
        bounds.append((top, top + value * scale, style, hatched))
        top += value * scale
    if top <= 0:
        return []
    top = max(top, 1.0)
    cells = []
    for row in range(rows):
        low, high = row * 8, row * 8 + 8
        if top <= low:
            break
        _, _, style, hatched = max(
            bounds, key=lambda b: max(0.0, min(b[1], high) - max(b[0], low)) + (b[1] > low) * 1e-9
        )
        if top >= high:
            glyph = "▒" if hatched else "█"
        else:
            eighths = min(8, max(1, round(top - low)))
            glyph = "░" if hatched else BLOCKS[eighths - 1]
        cells.append((glyph, style))
    return cells


def draw_timeline(canvas: Canvas, rect: Rect, snapshot: Snapshot, view: View) -> None:
    metric = snapshot.metric
    title = f"Tokens per {snapshot.period} · by {snapshot.group} · {METRIC_HELP[metric]}"
    canvas.box(rect, title, "←→ select · d/w/m · g · v")
    inner_x, inner_y = rect.x + 1, rect.y + 1
    inner_w, inner_h = rect.w - 2, rect.h - 2
    chart_h = inner_h - 2
    buckets = snapshot.buckets
    if chart_h < 2 or not buckets:
        return
    plot_x, plot_w = inner_x + AXIS, inner_w - AXIS
    slot = max(1, plot_w // len(buckets))
    bar_w = max(1, min(slot - 1, 7)) if slot > 1 else 1
    totals = [bucket.total.value(metric) for bucket in buckets]
    peak = max(totals, default=0)
    label_y = inner_y + chart_h
    for row in range(chart_h):
        canvas.put(inner_x + AXIS - 1, inner_y + row, "│", "border")
    for row in (0, chart_h // 2):
        value = peak * (chart_h - row) / chart_h
        canvas.put(inner_x, inner_y + row, compact(value).rjust(AXIS - 2), "dim")
        canvas.put(inner_x + AXIS - 1, inner_y + row, "┤", "border")
    canvas.put(inner_x, label_y, "0".rjust(AXIS - 2), "dim")
    canvas.put(inner_x + AXIS - 1, label_y, "└", "border")
    scale = chart_h * 8 / peak if peak else 0.0
    heights = []
    for index, bucket in enumerate(buckets):
        segments = []
        for name in snapshot.groups:
            tally = bucket.groups.get(name)
            if tally is None:
                continue
            hatched = tally.hatched(metric)
            solid = tally.value(metric) - hatched
            if solid > 0:
                segments.append((solid, view.series(name), False))
            if hatched > 0:
                segments.append((hatched, view.series(name), True))
        cells = stack_cells(segments, scale, chart_h)
        heights.append(len(cells))
        x = plot_x + index * slot
        for row, (glyph, style) in enumerate(cells):
            canvas.put(x, inner_y + chart_h - 1 - row, glyph * bar_w, style)
    widest = max(len(bucket.short) for bucket in buckets) + 1
    every = max(1, math.ceil(widest / slot))
    for index, bucket in enumerate(buckets):
        if index != snapshot.selected and (len(buckets) - 1 - index) % every == 0:
            canvas.put(
                plot_x + index * slot,
                label_y,
                bucket.short,
                "dim",
                limit=inner_x + inner_w - (plot_x + index * slot),
            )
    selected = buckets[snapshot.selected]
    select_x = plot_x + snapshot.selected * slot
    canvas.put(select_x, label_y, selected.short, "hi", limit=inner_x + inner_w - select_x)
    value_text = compact(totals[snapshot.selected])
    value_y = inner_y + chart_h - 1 - heights[snapshot.selected]
    if totals[snapshot.selected] and value_y >= inner_y:
        value_x = min(select_x, inner_x + inner_w - len(value_text))
        canvas.put(value_x, value_y, value_text, "accent")
    legend_y = label_y + 1
    x = inner_x + 1
    entries = [("■", view.series(name), clean(name)) for name in snapshot.groups]
    if snapshot.has_hatched:
        entries.append(("▒", "dim", "retained daily total (split unknown)"))
    if not snapshot.groups:
        canvas.put(inner_x + 1, legend_y, "no usage in this range", "dim")
    for glyph, style, name in entries:
        if x + len(name) + 4 > inner_x + inner_w:
            canvas.put(x, legend_y, "…", "dim")
            break
        x = canvas.put(x, legend_y, glyph, style)
        x = canvas.put(x + 1, legend_y, name, "text") + 2


BREAKDOWN_EXTRA = {GroupBy.MODEL: "backend", GroupBy.ACCOUNT: "tool"}


def draw_breakdown(canvas: Canvas, rect: Rect, snapshot: Snapshot, view: View) -> None:
    bucket = snapshot.selected_bucket
    title = f"{bucket.long if bucket else ''} · by {snapshot.detail}"
    if bucket is not None and bucket.total.calls:
        title += f" · cache hit {bucket.total.cache_share:.0%}"
    canvas.box(rect, title, "b: switch")
    extra = BREAKDOWN_EXTRA.get(snapshot.detail)
    columns = [Column(str(snapshot.detail), 10, "<", 0, flex=True)]
    if extra:
        columns.append(Column(extra, 18, "<", 6))
    columns += [
        Column("calls", 6, ">", 3),
        Column("input", 7, ">", 4),
        Column("cache r", 7, ">", 2),
        Column("cache w", 7, ">", 5),
        Column("output", 7, ">", 1),
        Column("total", 7, ">", 0),
        Column("share", 13, "<", 2),
    ]
    fitted = fit_columns(columns, rect.w - 4)
    x, y = rect.x + 2, rect.y + 1
    draw_header_row(canvas, x, y, fitted, columns)
    if bucket is None:
        return
    whole = bucket.total.value(snapshot.metric) or 1
    rows = snapshot.breakdown[: max(0, rect.h - 4)]
    colored = snapshot.detail is snapshot.group
    for offset, row in enumerate(rows, 1):
        tally = row.tally
        share = tally.value(snapshot.metric) / whole
        filled = round(share * 8)
        cells: list[Cell] = [(clean(row.name), view.series(row.name) if colored else "text")]
        if extra:
            cells.append((clean(row.extra), "dim"))
        cells += [
            (compact(tally.calls), "dim"),
            (compact(tally.input), "text"),
            (compact(tally.cache_read), "text"),
            (compact(tally.cache_write), "text"),
            (compact(tally.output), "text"),
            (compact(tally.total), "accent"),
            [("█" * filled, "s1"), ("░" * (8 - filled), "dim"), (f" {share:4.0%}", "text")],
        ]
        draw_cells(canvas, x, y + offset, fitted, columns, cells)
    if not rows:
        canvas.put(x, y + 1, "no usage in this bucket", "dim")
        return
    total = bucket.total
    cells = [(f"Σ {len(snapshot.breakdown)} rows", "title")]
    if extra:
        cells.append(("", "dim"))
    cells += [
        (compact(total.calls), "dim"),
        (compact(total.input), "title"),
        (compact(total.cache_read), "title"),
        (compact(total.cache_write), "title"),
        (compact(total.output), "title"),
        (compact(total.total), "accent"),
        ("", "dim"),
    ]
    draw_cells(canvas, x, rect.y + rect.h - 2, fitted, columns, cells)


FEED_COLUMNS = (
    Column("time", 8, "<", 0),
    Column("account", 11, "<", 1),
    Column("model", 14, "<", 2, flex=True),
    Column("project", 14, "<", 4),
    Column("in", 6, ">", 5),
    Column("cache", 6, ">", 3),
    Column("out", 6, ">", 3),
    Column("total", 7, ">", 0),
)


def draw_feed(
    canvas: Canvas,
    rect: Rect,
    snapshot: Snapshot,
    tz: tzinfo,
    names: Mapping[str, tuple[str, Tool]],
) -> None:
    canvas.box(rect, "Live feed · newest first", "h: heatmap")
    fitted = fit_columns(FEED_COLUMNS, rect.w - 4)
    x, y = rect.x + 2, rect.y + 1
    draw_header_row(canvas, x, y, fitted, FEED_COLUMNS)
    if not snapshot.recent:
        canvas.put(x, y + 1, "waiting for the first request…", "dim")
    for offset, event in enumerate(snapshot.recent[: max(0, rect.h - 3)], 1):
        age = snapshot.now - event.ts
        moment = datetime.fromtimestamp(event.ts, tz)
        stamp = moment.strftime("%H:%M:%S") if age < 86400 else moment.strftime("%d %b")
        label, tool = names.get(event.account, (event.account, event.tool))
        usage = event.usage
        draw_cells(
            canvas,
            x,
            y + offset,
            fitted,
            FEED_COLUMNS,
            [
                (stamp, "hi" if age < 20 else "dim"),
                (clean(label), TOOL_STYLE[tool]),
                (clean(event.model), "text"),
                (clean(project_label(event.project)), "dim"),
                (compact(usage.input), "text"),
                (compact(usage.cache_read + usage.cache_write), "dim"),
                (compact(usage.output), "text"),
                (compact(usage.total), "accent"),
            ],
        )


def project_label(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1] if path else "—"


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def draw_heatmap(canvas: Canvas, rect: Rect, snapshot: Snapshot) -> None:
    canvas.box(rect, "Activity · hour × weekday · last 4 weeks", "h: feed")
    inner_x, inner_y, inner_w = rect.x + 2, rect.y + 1, rect.w - 4
    cell = max(1, min(3, (inner_w - 4) // 24))
    peak = max((max(row) for row in snapshot.heatmap), default=0)
    for hour in range(0, 24, 3 if cell >= 2 else 6):
        canvas.put(inner_x + 4 + hour * cell, inner_y, f"{hour:02d}", "dim")
    for day, values in enumerate(snapshot.heatmap):
        y = inner_y + 1 + day
        if y >= rect.y + rect.h - 1:
            break
        canvas.put(inner_x, y, WEEKDAYS[day], "dim")
        for hour, value in enumerate(values):
            level = 0 if not peak or value <= 0 else max(1, round(value / peak * (len(HEAT) - 1)))
            canvas.put(inner_x + 4 + hour * cell, y, HEAT[level] * cell, "accent")
    if not peak and rect.h > 10:
        canvas.put(inner_x, inner_y + 9, "no activity in the last four weeks", "dim")


def draw_header(
    canvas: Canvas,
    width: int,
    snapshot: Snapshot,
    view: View,
    mode: str,
    tz: tzinfo,
    filter_label: str | None,
) -> None:
    canvas.fill(Rect(0, 0, width, 1), "header")
    left = f" ◆ tokenUsage2  {mode} "
    canvas.put(0, 0, left, "header")
    clock = datetime.fromtimestamp(snapshot.now, tz).strftime("%a %d %b  %H:%M:%S")
    right = f" ⚡ {compact(snapshot.rate)} tok/min   {clock} "
    metric = snapshot.metric
    middle = (
        f"today {compact(snapshot.today.value(metric))}  ·  "
        f"week {compact(snapshot.week.value(metric))}  ·  "
        f"month {compact(snapshot.month.value(metric))}  ·  "
        f"all {compact(snapshot.all.value(metric))}"
    )
    if filter_label:
        middle += f"  ·  [{clean(filter_label)}]"
    if len(left) + len(right) <= width:
        canvas.put(width - len(right), 0, right, "header")
        room = width - len(left) - len(right)
        if len(middle) + 2 <= room:
            canvas.put(len(left) + (room - len(middle)) // 2, 0, middle, "header")


def draw_footer(canvas: Canvas, rect: Rect, status: str) -> None:
    status = clip(status, max(0, rect.w // 2))
    limit = rect.w - len(status) - 2
    x = 1
    for key, description in HINTS:
        if x + len(key) + len(description) + 3 > limit:
            break
        x = canvas.put(x, rect.y, key, "accent")
        x = canvas.put(x + 1, rect.y, description, "dim") + 2
    canvas.put(rect.w - len(status) - 1, rect.y, status, "dim")


def draw_overlay(canvas: Canvas, title: str, lines: Sequence[str]) -> None:
    lines = [clean(line) for line in lines] or [""]
    width = min(canvas.width - 4, max(len(title) + 8, max(len(line) for line in lines) + 4))
    height = min(canvas.height - 2, len(lines) + 2)
    rect = Rect((canvas.width - width) // 2, (canvas.height - height) // 2, width, height)
    canvas.fill(rect, "text")
    canvas.box(rect, title, "esc: close", style="title")
    for offset, line in enumerate(lines[: height - 2]):
        canvas.put(rect.x + 2, rect.y + 1 + offset, clip(line, width - 4), "text")


def render(
    snapshot: Snapshot,
    view: View,
    width: int,
    height: int,
    *,
    tz: tzinfo,
    status: str = "",
    sources: Sequence[str] = (),
    mode: str = "LIVE",
) -> list[str]:
    """One full frame as ``height`` lines of exactly ``width`` cells."""
    canvas = Canvas(width, height)
    theme = THEMES.get(view.theme, _DEFAULT)
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        message = clip(
            f"terminal too small ({width}×{height}); need {MIN_WIDTH}×{MIN_HEIGHT}", width
        )
        canvas.put(max(0, (width - len(message)) // 2), height // 2, message, "warn")
        return canvas.lines(theme)
    frame = layout(width, height, len(snapshot.accounts))
    names = {row.id: (row.label, row.tool) for row in snapshot.accounts}
    filter_label = (
        names[snapshot.account_filter][0]
        if snapshot.account_filter in names
        else (snapshot.account_filter)
    )
    draw_header(canvas, width, snapshot, view, mode, tz, filter_label)
    draw_accounts(canvas, frame.accounts, snapshot, view, frame.account_rows)
    if frame.timeline is not None:
        draw_timeline(canvas, frame.timeline, snapshot, view)
    if frame.left is not None:
        draw_breakdown(canvas, frame.left, snapshot, view)
    if frame.right is not None:
        if view.heatmap:
            draw_heatmap(canvas, frame.right, snapshot)
        else:
            draw_feed(canvas, frame.right, snapshot, tz, names)
    draw_footer(canvas, frame.footer, status)
    if view.help:
        draw_overlay(canvas, "Keys", HELP_LINES)
    elif view.sources:
        draw_overlay(canvas, "Sources", sources)
    return canvas.lines(theme)


def render_message(width: int, height: int, lines: Sequence[str], theme: str) -> list[str]:
    """A centred message, used while the first scan runs."""
    canvas = Canvas(width, height)
    top = max(0, (height - len(lines)) // 2)
    for offset, line in enumerate(lines):
        text = clip(clean(line), width)
        canvas.put(
            max(0, (width - len(text)) // 2), top + offset, text, "title" if offset == 0 else "dim"
        )
    return canvas.lines(THEMES.get(theme, _DEFAULT))
