#!/usr/bin/env python3
"""Render Token Use's overview JSON as a dependency-free HTML chart."""

import html
import json
import sys
from pathlib import Path


source = Path(sys.argv[1])
destination = Path(sys.argv[2])
data = json.loads(source.read_text(encoding="utf-8"))

token_fields = [
    ("input_tokens", "Input", "#60a5fa"),
    ("output_tokens", "Output", "#f59e0b"),
    ("cache_read_tokens", "Cache read", "#34d399"),
    ("cache_write_tokens", "Cache write", "#a78bfa"),
]


def token_total(row):
    return sum(int(row.get(field, 0)) for field, _, _ in token_fields)


def compact(number):
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return str(number)


tools = data["by_tool"]
maximum = max(token_total(row) for row in tools)
chart_width = 760
bar_height = 54
gap = 52
svg_height = 55 + len(tools) * (bar_height + gap)
svg_rows = []

for index, row in enumerate(tools):
    y = 42 + index * (bar_height + gap)
    x = 155
    segments = []
    for field, label, color in token_fields:
        value = int(row.get(field, 0))
        width = chart_width * value / maximum
        if width:
            segments.append(
                f'<rect x="{x:.2f}" y="{y}" width="{width:.2f}" height="{bar_height}" '
                f'fill="{color}"><title>{html.escape(label)}: {value:,}</title></rect>'
            )
        x += width
    svg_rows.append(
        f'<text x="140" y="{y + 24}" text-anchor="end" class="tool">{html.escape(row["tool"])}</text>'
        f'<text x="140" y="{y + 45}" text-anchor="end" class="sub">{row["sessions"]:,} sessions</text>'
        + "".join(segments)
        + f'<text x="{155 + chart_width + 14}" y="{y + 33}" class="total">{compact(token_total(row))}</text>'
    )

legend = "".join(
    f'<span><i style="background:{color}"></i>{html.escape(label)}</span>'
    for _, label, color in token_fields
)
cards = "".join(
    f'<article><h2>{html.escape(row["tool"])}</h2>'
    f'<strong>{token_total(row):,}</strong><small>raw tokens</small>'
    f'<p>{row["calls"]:,} calls · {row["sessions"]:,} sessions · {html.escape(row["cost"])} API-equivalent estimate</p></article>'
    for row in tools
)

document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Code and Codex token usage</title>
<style>
:root{{--bg:#08111f;--panel:#111c2e;--text:#e5edf8;--muted:#91a3bb;--line:#24334b}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:16px system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;padding:48px 28px}} h1{{font-size:34px;margin:0 0 8px}} .lede,.note{{color:var(--muted)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin:30px 0}}
article,.chart{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:24px}}
article h2{{margin:0 0 14px;font-size:18px}} article strong{{display:block;font-size:32px}} article small{{color:var(--muted)}} article p{{margin:14px 0 0;color:var(--muted)}}
.chart{{overflow-x:auto}} svg{{min-width:1000px;width:100%;height:auto}} .tool{{fill:var(--text);font-weight:700;font-size:16px}} .sub{{fill:var(--muted);font-size:12px}} .total{{fill:var(--text);font-weight:700;font-size:16px}}
.legend{{display:flex;gap:22px;flex-wrap:wrap;margin:0 0 15px}} .legend span{{color:var(--muted)}} .legend i{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:7px}}
.note{{font-size:13px;line-height:1.55;margin-top:20px}}
</style></head><body><main>
<h1>Claude Code vs Codex</h1><p class="lede">{html.escape(data["period"])} · generated from local session logs by Token Use</p>
<section class="cards">{cards}</section>
<section class="chart"><div class="legend">{legend}</div>
<svg viewBox="0 0 1100 {svg_height}" role="img" aria-label="Stacked raw-token totals by tool">{''.join(svg_rows)}</svg></section>
<p class="note">Raw totals include cache reads and cache writes, so they are much larger than fresh input/output alone. Cost is an API-equivalent estimate from Token Use's bundled prices—not an invoice or subscription charge—and locally routed models may use fallback pricing.</p>
</main></body></html>"""

destination.write_text(document, encoding="utf-8")
print(f"Rendered {destination}")
