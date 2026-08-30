#!/usr/bin/env python3
"""Create a social-ready usage report from retained Claude and Codex totals."""

import html
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


claude_stats = Path(sys.argv[1])
codex_state = Path(sys.argv[2])
year = int(sys.argv[3])
destination = Path(sys.argv[4])

stats = json.loads(claude_stats.read_text(encoding="utf-8"))
claude_total = sum(
    model.get("inputTokens", 0)
    + model.get("outputTokens", 0)
    + model.get("cacheReadInputTokens", 0)
    + model.get("cacheCreationInputTokens", 0)
    for model in stats.get("modelUsage", {}).values()
)
claude_daily = {month: 0 for month in range(1, 13)}
daily_dates = []
for day in stats.get("dailyModelTokens", []):
    parsed = datetime.fromisoformat(day["date"])
    if parsed.year != year:
        continue
    daily_dates.append(parsed)
    claude_daily[parsed.month] += sum(day.get("tokensByModel", {}).values())

with sqlite3.connect(codex_state) as connection:
    codex_total = connection.execute(
        "SELECT COALESCE(SUM(tokens_used), 0) FROM threads "
        "WHERE created_at >= ? AND created_at < ?",
        (
            int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()),
            int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp()),
        ),
    ).fetchone()[0]
    codex_monthly = dict(
        connection.execute(
            "SELECT CAST(strftime('%m', created_at, 'unixepoch') AS INTEGER), "
            "COALESCE(SUM(tokens_used), 0) FROM threads "
            "WHERE created_at >= ? AND created_at < ? GROUP BY 1",
            (
                int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()),
                int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp()),
            ),
        )
    )
codex_monthly = {month: codex_monthly.get(month, 0) for month in range(1, 13)}

combined = claude_total + codex_total
claude_share = claude_total / combined if combined else 0
attributed_claude = sum(claude_daily.values())
unallocated_claude = max(0, claude_total - attributed_claude)
first_daily = min(daily_dates).strftime("%b %-d") if daily_dates else "n/a"
last_daily = max(daily_dates).strftime("%b %-d") if daily_dates else "n/a"


def compact(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.0f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return str(value)


def month_chart(values, color, gradient_id, maximum, unavailable=()):
    width, height = 1010, 220
    left, right, top, bottom = 45, 12, 28, 36
    plot_w, plot_h = width - left - right, height - top - bottom
    group_w, bar_w = plot_w / 12, 42
    parts = [
        f'<defs><linearGradient id="{gradient_id}" x1="0" y1="1" x2="0" y2="0">'
        f'<stop offset="0" stop-color="{color}" stop-opacity=".52"/>'
        f'<stop offset="1" stop-color="{color}"/></linearGradient>'
        '<pattern id="missing" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#34445d" stroke-width="3"/></pattern></defs>'
    ]
    for tick in range(4):
        value = maximum * tick / 3
        y = top + plot_h - plot_h * tick / 3
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" class="axis">{compact(value)}</text>')
    for month in range(1, 13):
        center = left + (month - 0.5) * group_w
        x = center - bar_w / 2
        value = values[month]
        if month in unavailable:
            parts.append(f'<rect x="{x:.1f}" y="{top}" width="{bar_w}" height="{plot_h}" rx="7" fill="url(#missing)" opacity=".5"/>')
        if value:
            bar_h = max(3, plot_h * value / maximum)
            y = top + plot_h - bar_h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="8" fill="url(#{gradient_id})"><title>{value:,} tokens</title></rect>')
            parts.append(f'<text x="{center:.1f}" y="{max(20, y-8):.1f}" text-anchor="middle" class="value">{compact(value)}</text>')
        parts.append(f'<text x="{center:.1f}" y="{height-15}" text-anchor="middle" class="month">{datetime(year, month, 1).strftime("%b")}</text>')
    return f'<svg viewBox="0 0 {width} {height}" aria-hidden="true">{"".join(parts)}</svg>'


claude_chart = month_chart(
    claude_daily,
    "#ff8066",
    "claudeGradient",
    max(max(claude_daily.values()), 1),
    unavailable=(5, 6),
)
codex_chart = month_chart(
    codex_monthly,
    "#52c7ff",
    "codexGradient",
    max(max(codex_monthly.values()), 1),
)

annual_bar_width = 690
claude_width = annual_bar_width * claude_total / max(claude_total, codex_total, 1)
codex_width = annual_bar_width * codex_total / max(claude_total, codex_total, 1)
snapshot = datetime.now().strftime("%d %b %Y")

document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{year} AI coding token usage</title>
<style>
:root{{--ink:#07101f;--panel:#101d31;--panel2:#13243d;--text:#f7f9ff;--muted:#9dafca;--line:#263a57;--claude:#ff8066;--codex:#52c7ff;--lime:#bcf34a}}
*{{box-sizing:border-box}}html,body{{margin:0;background:#030812;color:var(--text);font-family:Inter,"Segoe UI",system-ui,sans-serif}}
body{{display:flex;justify-content:center}}.poster{{width:1200px;min-height:1500px;padding:66px 72px 48px;position:relative;overflow:hidden;background:radial-gradient(circle at 93% 4%,#193c63 0,transparent 28%),radial-gradient(circle at 0 52%,#321d31 0,transparent 31%),var(--ink)}}
.poster:before{{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);background-size:34px 34px;pointer-events:none}}
header,.content,footer{{position:relative}}.eyebrow{{color:var(--lime);font-weight:800;letter-spacing:.18em;text-transform:uppercase;font-size:14px}}h1{{font-size:58px;line-height:1.02;letter-spacing:-.045em;margin:17px 0 13px;max-width:900px}}.subtitle{{color:var(--muted);font-size:20px;margin:0}}.hero{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin:38px 0 26px}}.metric{{background:linear-gradient(145deg,rgba(24,41,67,.94),rgba(13,25,44,.94));border:1px solid var(--line);border-radius:22px;padding:23px 24px;box-shadow:0 18px 60px rgba(0,0,0,.19)}}.metric span{{display:block;color:var(--muted);font-weight:650;font-size:15px}}.metric strong{{display:block;font-size:37px;letter-spacing:-.04em;margin:7px 0 3px}}.metric small{{color:var(--muted)}}.metric.claude{{border-top:3px solid var(--claude)}}.metric.codex{{border-top:3px solid var(--codex)}}.metric.total{{border-top:3px solid var(--lime)}}
.panel{{background:linear-gradient(150deg,rgba(17,31,52,.96),rgba(10,21,38,.96));border:1px solid var(--line);border-radius:25px;padding:24px 24px 17px;margin-top:17px;box-shadow:0 24px 70px rgba(0,0,0,.18)}}.panel-head{{display:flex;justify-content:space-between;align-items:flex-start;margin:0 5px 3px}}.panel h2{{font-size:22px;margin:0;letter-spacing:-.02em}}.panel p{{color:var(--muted);font-size:14px;margin:6px 0 0}}.badge{{border-radius:999px;padding:7px 12px;font-size:12px;font-weight:800;letter-spacing:.05em}}.badge.claude{{background:rgba(255,128,102,.13);color:#ffab98}}.badge.codex{{background:rgba(82,199,255,.13);color:#8cdbff}}svg{{display:block;width:100%;height:auto}}.grid{{stroke:var(--line);stroke-width:1}}.axis,.month{{fill:#8297b6;font-size:11px}}.value{{fill:#e8effc;font-size:11px;font-weight:750}}
.year{{display:grid;grid-template-columns:225px 1fr 92px;gap:13px;align-items:center;margin:17px 5px}}.year-label{{font-weight:750}}.year-label i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:9px}}.track{{height:17px;background:#091426;border-radius:999px;overflow:hidden;border:1px solid #20334e}}.fill{{height:100%;border-radius:999px}}.fill.claude{{background:linear-gradient(90deg,#e55848,var(--claude))}}.fill.codex{{background:linear-gradient(90deg,#2388d5,var(--codex))}}.year-value{{text-align:right;font-weight:850;font-size:18px}}.callout{{display:flex;gap:13px;align-items:flex-start;background:rgba(188,243,74,.075);border:1px solid rgba(188,243,74,.25);border-radius:18px;padding:15px 18px;margin-top:18px;color:#dcebad;font-size:14px;line-height:1.45}}.callout b{{font-size:18px;color:var(--lime)}}
footer{{display:flex;justify-content:space-between;align-items:flex-end;color:#7589a6;font-size:12px;margin-top:25px;line-height:1.45}}footer strong{{display:block;color:#aebdd2;font-size:13px}}@media(max-width:800px){{.poster{{width:100%;min-height:100vh;padding:36px 22px}}h1{{font-size:40px}}.hero{{grid-template-columns:1fr}}.panel{{overflow-x:auto}}.panel>svg{{min-width:820px}}}}
</style></head><body><main class="poster"><header><div class="eyebrow">My AI coding year · {year}</div><h1>{combined / 1_000_000_000:.1f} billion tokens.<br>One developer workstation.</h1><p class="subtitle">Claude Code and Codex usage retained locally — visualized without uploading a single prompt.</p></header><div class="content"><section class="hero"><article class="metric claude"><span>Claude Code</span><strong>{compact(claude_total)}</strong><small>{claude_share:.0%} of retained total</small></article><article class="metric codex"><span>Codex</span><strong>{compact(codex_total)}</strong><small>{1-claude_share:.0%} of retained total</small></article><article class="metric total"><span>Combined</span><strong>{compact(combined)}</strong><small>{year} retained usage</small></article></section>
<section class="panel"><div class="panel-head"><div><h2>Claude Code · attributable monthly usage</h2><p>Daily aggregates retained from {first_daily} through {last_daily}</p></div><span class="badge claude">CLAUDE</span></div>{claude_chart}</section>
<section class="panel"><div class="panel-head"><div><h2>Codex · tokens by thread creation month</h2><p>Internal thread totals, grouped by the month each thread began</p></div><span class="badge codex">CODEX</span></div>{codex_chart}</section>
<section class="panel"><div class="panel-head"><div><h2>{year} retained total</h2><p>Provider comparison on a shared linear scale</p></div></div><div class="year"><div class="year-label"><i style="background:var(--claude)"></i>Claude Code</div><div class="track"><div class="fill claude" style="width:{claude_width:.1f}px"></div></div><div class="year-value">{compact(claude_total)}</div></div><div class="year"><div class="year-label"><i style="background:var(--codex)"></i>Codex</div><div class="track"><div class="fill codex" style="width:{codex_width:.1f}px"></div></div><div class="year-value">{compact(codex_total)}</div></div></section>
<div class="callout"><b>↗</b><div><strong>{compact(unallocated_claude)} Claude tokens are retained in the annual total but cannot be assigned precisely by month.</strong><br>The striped May–June region marks missing historical transcript detail; July and August are partial reporting periods.</div></div></div>
<footer><div><strong>Local data · no prompts uploaded</strong>Claude stats cache + Codex thread database</div><div style="text-align:right">Snapshot {snapshot}<br>Raw tokens include cached context</div></footer></main></body></html>"""

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(document, encoding="utf-8")
print(f"Rendered {destination}")
