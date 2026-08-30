#!/usr/bin/env python3
"""Render a calendar year from Token Use's normalized archive."""

import csv
import html
import json
import sqlite3
import sys
from pathlib import Path


archive = Path(sys.argv[1])
year = int(sys.argv[2])
output_dir = Path(sys.argv[3])
if not archive.is_file():
    raise SystemExit(f"Token Use archive not found: {archive}")

tool_labels = {"claude-code": "Claude", "codex": "Codex"}
colors = {
    "claude_input": "#fb923c",
    "claude_output": "#fbbf24",
    "claude_cache": "#7c2d12",
    "codex_input": "#60a5fa",
    "codex_output": "#22d3ee",
    "codex_cache": "#1e3a8a",
}
rows = {
    (month, tool): {
        "month": f"{year}-{month:02d}", "tool": label, "calls": 0,
        "sessions": 0, "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_write_tokens": 0, "cost_usd": 0.0,
    }
    for month in range(1, 13)
    for tool, label in tool_labels.items()
}

query = """
SELECT CAST(substr(timestamp, 6, 2) AS INTEGER) AS month, tool,
       COUNT(*) AS calls, COUNT(DISTINCT session_id) AS sessions,
       SUM(input_tokens), SUM(output_tokens),
       SUM(MAX(cache_read_input_tokens, cached_input_tokens)),
       SUM(cache_creation_input_tokens), SUM(cost_usd)
FROM calls
WHERE timestamp >= ? AND timestamp < ? AND tool IN ('claude-code', 'codex')
GROUP BY month, tool ORDER BY month, tool
"""
with sqlite3.connect(archive) as connection:
    for record in connection.execute(query, (f"{year}-01-01", f"{year + 1}-01-01")):
        month, tool, calls, sessions, input_t, output_t, cache_read, cache_write, cost = record
        row = rows[(month, tool)]
        row.update({
            "calls": calls, "sessions": sessions, "input_tokens": input_t or 0,
            "output_tokens": output_t or 0, "cache_read_tokens": cache_read or 0,
            "cache_write_tokens": cache_write or 0, "cost_usd": cost or 0.0,
        })

records = list(rows.values())
for row in records:
    row["fresh_tokens"] = row["input_tokens"] + row["output_tokens"]
    row["cache_tokens"] = row["cache_read_tokens"] + row["cache_write_tokens"]
    row["total_tokens"] = row["fresh_tokens"] + row["cache_tokens"]


def compact(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def provider_aware_chart(parts, title):
    """Generate charts with separate palettes for the paired providers."""
    width, height, left, right, top, bottom = 1180, 360, 72, 22, 28, 55
    plot_w, plot_h = width-left-right, height-top-bottom
    maximum = max(sum(row[key] for key, _, _ in parts) for row in records) or 1
    group_w, bar_w = plot_w / 12, 27
    out = [f'<text x="{left}" y="18" class="chart-title">{html.escape(title)}</text>']
    for tick in range(5):
        value, y = maximum*tick/4, top+plot_h-plot_h*tick/4
        out += [f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>',
                f'<text x="{left-9}" y="{y+4:.1f}" text-anchor="end" class="axis">{compact(value)}</text>']
    for month in range(1, 13):
        center = left+(month-.5)*group_w
        out.append(f'<text x="{center:.1f}" y="{height-20}" text-anchor="middle" class="axis">{month:02d}</text>')
        for index, (tool, label) in enumerate(tool_labels.items()):
            row, x, y_bottom = rows[(month, tool)], center+(-bar_w-3 if index == 0 else 3), top+plot_h
            for key, claude_color, codex_color in parts:
                value = row[key]
                segment_h = plot_h*value/maximum
                y_bottom -= segment_h
                if segment_h:
                    color = colors[claude_color if tool == "claude-code" else codex_color]
                    out.append(f'<rect x="{x:.1f}" y="{y_bottom:.1f}" width="{bar_w}" height="{segment_h:.1f}" fill="{color}"><title>{label} · {row["month"]} · {key.replace("_", " ")}: {value:,}</title></rect>')
    return f'<svg viewBox="0 0 {width} {height}">{"".join(out)}</svg>'


total_chart = provider_aware_chart(
    [("fresh_tokens", "claude_input", "codex_input"), ("cache_tokens", "claude_cache", "codex_cache")],
    "Monthly total traffic — paired bars: Claude, then Codex",
)
fresh_chart = provider_aware_chart(
    [("input_tokens", "claude_input", "codex_input"), ("output_tokens", "claude_output", "codex_output")],
    "Fresh tokens only — input plus output",
)

totals = {label: sum(row["total_tokens"] for row in records if row["tool"] == label) for label in tool_labels.values()}
table_rows = []
for month in range(1, 13):
    claude, codex = rows[(month, "claude-code")], rows[(month, "codex")]
    table_rows.append(f'<tr><td>{year}-{month:02d}</td><td>{claude["total_tokens"]:,}</td><td>{codex["total_tokens"]:,}</td><td>{claude["sessions"]}</td><td>{codex["sessions"]}</td><td>${claude["cost_usd"]+codex["cost_usd"]:,.2f}</td></tr>')

output_dir.mkdir(parents=True, exist_ok=True)
json_path = output_dir / f"year-{year}.json"
csv_path = output_dir / f"year-{year}.csv"
html_path = output_dir / f"year-{year}.html"
json_path.write_text(json.dumps({"year": year, "records": records}, indent=2), encoding="utf-8")
with csv_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=records[0].keys(), lineterminator="\n")
    writer.writeheader(); writer.writerows(records)

legend = "".join(f'<span><i style="background:{color}"></i>{label}</span>' for label, color in [
    ("Claude fresh/input", colors["claude_input"]), ("Claude output", colors["claude_output"]),
    ("Claude cache", colors["claude_cache"]), ("Codex fresh/input", colors["codex_input"]),
    ("Codex output", colors["codex_output"]), ("Codex cache", colors["codex_cache"]),
])
document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{year} token usage</title>
<style>:root{{--bg:#08111f;--panel:#111c2e;--text:#e5edf8;--muted:#91a3bb;--line:#24334b}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px system-ui,sans-serif}}main{{max-width:1260px;margin:auto;padding:44px 28px}}h1{{font-size:34px;margin:0}}.lede,.note{{color:var(--muted)}}.cards{{display:flex;gap:18px;flex-wrap:wrap;margin:28px 0}}article,.chart,.table-wrap{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px}}article{{min-width:260px}}article strong{{display:block;font-size:30px;margin-top:8px}}.chart{{overflow-x:auto;margin:18px 0}}svg{{min-width:900px;width:100%;height:auto}}.grid{{stroke:var(--line);stroke-width:1}}.axis{{fill:var(--muted);font-size:12px}}.chart-title{{fill:var(--text);font-weight:700;font-size:16px}}.legend{{display:flex;gap:18px;flex-wrap:wrap}}.legend span{{color:var(--muted);font-size:13px}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:right}}th:first-child,td:first-child{{text-align:left}}.table-wrap{{overflow:auto}}.note{{font-size:13px;line-height:1.5}}</style></head><body><main>
<h1>{year} Claude Code vs Codex</h1><p class="lede">Monthly buckets from Token Use's normalized local archive.</p><section class="cards"><article>Claude Code<strong>{totals['Claude']:,}</strong><span class="lede">raw tokens</span></article><article>Codex<strong>{totals['Codex']:,}</strong><span class="lede">raw tokens</span></article><article>Combined<strong>{sum(totals.values()):,}</strong><span class="lede">raw tokens</span></article></section><div class="legend">{legend}</div><section class="chart">{total_chart}</section><section class="chart">{fresh_chart}</section><section class="table-wrap"><table><thead><tr><th>Month</th><th>Claude tokens</th><th>Codex tokens</th><th>Claude sessions</th><th>Codex sessions</th><th>API-equivalent cost</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></section><p class="note">Raw tokens include cache reads and writes. Cost uses Token Use's bundled API prices and may use fallback prices for locally routed models; it is not an invoice or subscription charge.</p>
</main></body></html>"""
html_path.write_text(document, encoding="utf-8")
print(f"Rendered {html_path}, {json_path}, and {csv_path}")
