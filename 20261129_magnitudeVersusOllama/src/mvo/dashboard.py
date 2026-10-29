# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""dashboard.html: verdict tiles, bar charts per model and the sortable tables.

Colors follow the arm type, never the rank (validated with the dataviz palette checker):
Magnitude with drafter = blue, Ollama without drafter = orange, Ollama with MTP = aqua,
Magnitude without drafter = yellow. Every bar has a direct value label and a hover tooltip.
"""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any

ROLES: dict[str, tuple[str, str]] = {  # role -> (css slot, legend text)
    "magnitude-draft": ("s1", "Magnitude, with drafter"),
    "ollama-plain": ("s2", "Ollama, no drafter"),
    "ollama-draft": ("s3", "Ollama, with MTP drafter"),
    "magnitude-plain": ("s4", "Magnitude, no drafter"),
}
WORKLOAD_NAMES = {"A": "A · repeat a passage", "B": "B · write new code", "C": "C · quality"}
VERDICT_STYLE = {
    "a faster": ("good", "Magnitude clearly faster"),
    "b faster": ("critical", "Ollama clearly faster"),
    "tie": ("neutral", "Tie under the rule"),
    "too few runs": ("warning", "Too few runs (n < 5)"),
}

CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;
--good:#0ca30c;--warning:#fab219;--serious:#ec835a;--critical:#d03b3b;--neutral:#898781}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;--page:#0d0d0d;
--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;
--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 10px}h3{font-size:15px;margin:0 0 8px}
.sub{color:var(--ink2);margin:0 0 18px}
.banner{background:var(--surface);border:1px solid var(--ring);border-left:5px solid var(--s1);border-radius:10px;
padding:14px 18px;font-size:17px;font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:8px 18px;margin:10px 0 4px;color:var(--ink2);font-size:13px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
.tile{background:var(--surface);border:1px solid var(--ring);border-left:5px solid var(--dot);border-radius:10px;
padding:14px 16px}
.tile.good{--dot:var(--good)}.tile.warning{--dot:var(--warning)}
.tile.critical{--dot:var(--critical)}.tile.neutral{--dot:var(--neutral)}
.tile .k{color:var(--ink2);font-size:13px}.tile .v{font-size:32px;font-weight:700;letter-spacing:-.02em}
.tile .d{color:var(--ink2);font-size:13px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:2px 9px;border-radius:99px;
border:1px solid var(--ring);background:var(--surface);color:var(--ink)}
.chip::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--dot)}
.chip.good{--dot:var(--good)}.chip.warning{--dot:var(--warning)}.chip.critical{--dot:var(--critical)}
.chip.neutral{--dot:var(--neutral)}.chip.serious{--dot:var(--serious)}
.model{background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:16px 18px;margin:14px 0}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px}
.chart svg{width:100%;height:auto;overflow:visible}
.chart text{fill:var(--ink2);font:12px system-ui,sans-serif}.chart .val{fill:var(--ink);font-weight:600}
.chart .grp{fill:var(--ink);font-weight:600}
.chart .grid{stroke:var(--grid)}.chart .base{stroke:var(--axis)}.chart .wh{stroke:var(--ink2);stroke-width:1.5}
.chart rect.bar{rx:4}.chart g.m:hover rect.bar{opacity:.8}
.s1{fill:var(--s1);background:var(--s1)}.s2{fill:var(--s2);background:var(--s2)}
.s3{fill:var(--s3);background:var(--s3)}.s4{fill:var(--s4);background:var(--s4)}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--ring);
border-radius:8px;padding:6px 10px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.15);display:none;max-width:320px}
.tablewrap{overflow-x:auto;background:var(--surface);border:1px solid var(--ring);border-radius:10px}
table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid var(--grid);padding:6px 10px;text-align:left;white-space:nowrap;font-size:13px}
th{color:var(--ink2);cursor:pointer;user-select:none;font-weight:600}tr:last-child td{border-bottom:0}
.info{color:var(--muted);cursor:help}
details{margin-top:28px;color:var(--ink2)}
@media (max-width:560px){.charts{grid-template-columns:1fr}}
"""

JS = """
const tip=document.getElementById('tip');
document.querySelectorAll('g.m').forEach(g=>{g.addEventListener('mousemove',e=>{tip.innerHTML=g.dataset.tip;
tip.style.display='block';tip.style.left=Math.min(e.clientX+14,innerWidth-330)+'px';tip.style.top=(e.clientY+14)+'px'});
g.addEventListener('mouseleave',()=>{tip.style.display='none'})});
function sortTable(id,col){const t=document.getElementById(id),b=t.tBodies[0],rows=[...b.rows];
const dir=t.dataset.col==col&&t.dataset.dir=="asc"?"desc":"asc";t.dataset.col=col;t.dataset.dir=dir;
const key=r=>{const s=r.cells[col]?r.cells[col].innerText:"";const n=parseFloat(s);return isNaN(n)?s:n};
rows.sort((x,y)=>{const a=key(x),c=key(y);const r=a<c?-1:a>c?1:0;return dir=="asc"?r:-r});
rows.forEach(r=>b.appendChild(r))}
"""


def role(spec: dict[str, Any]) -> str:
    """Return the arm type: engine plus 'draft' or 'plain'."""
    engine = "magnitude" if spec.get("engine") == "magnitude" else "ollama"
    drafter = str(spec.get("drafter", "none")).lower()
    return f"{engine}-{'plain' if drafter.startswith('none') else 'draft'}"


def bar_chart(title: str, unit: str, groups: list[tuple[str, list[dict[str, Any]]]]) -> str:
    """Horizontal grouped bars: one group per cell, one bar per arm, median with a min-max whisker."""
    bars = [b for _, items in groups for b in items]
    if not bars:
        return ""
    top = max(b["high"] for b in bars) or 1.0
    label_w, plot_w, bar_h, gap, group_gap = 170, 380, 16, 3, 18
    y = 8
    parts: list[str] = []
    for name, items in groups:
        parts.append(f'<text class="grp" x="0" y="{y + 12}">{html.escape(name)}</text>')
        y += 20
        for b in items:
            w = max(2.0, plot_w * b["median"] / top)
            lo, hi = label_w + plot_w * b["low"] / top, label_w + plot_w * b["high"] / top
            tip = (
                f"<b>{html.escape(b['arm'])}</b><br>{html.escape(name)}<br>median {b['median']:.1f} {unit}"
                f"<br>range {b['low']:.1f}–{b['high']:.1f} · n = {b['n']}"
            )
            parts.append(
                f'<g class="m" data-tip="{html.escape(tip)}">'
                f'<rect x="0" y="{y - 2}" width="{label_w + plot_w + 70}" height="{bar_h + 4}" fill="transparent"/>'
                f'<text x="{label_w - 8}" y="{y + 12}" text-anchor="end">{html.escape(b["arm"])}</text>'
                f'<rect class="bar {b["slot"]}" x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h}"/>'
                f'<line class="wh" x1="{lo:.1f}" x2="{hi:.1f}" y1="{y + bar_h / 2}" y2="{y + bar_h / 2}"/>'
                f'<text class="val" x="{label_w + max(w, hi - label_w) + 6:.1f}" y="{y + 12}">{b["median"]:.0f}</text>'
                "</g>"
            )
            y += bar_h + gap
        y += group_gap
    bottom = y - group_gap
    grid = "".join(
        f'<line class="grid" x1="{label_w + plot_w * f:.1f}" x2="{label_w + plot_w * f:.1f}" y1="0" y2="{bottom}"/>'
        f'<text x="{label_w + plot_w * f:.1f}" y="{bottom + 14}" text-anchor="middle">{top * f:.0f}</text>'
        for f in (0.25, 0.5, 0.75, 1.0)
    )
    base = f'<line class="base" x1="{label_w}" x2="{label_w}" y1="0" y2="{y - group_gap}"/>'
    height = y - group_gap + 20
    return (
        f'<div class="chart"><h3>{html.escape(title)}</h3>'
        f'<svg viewBox="0 0 {label_w + plot_w + 70} {height}" role="img" aria-label="{html.escape(title)}">'
        f"{grid}{base}{''.join(parts)}</svg></div>"
    )


def chip(kind: str, text: str) -> str:
    """A status chip: colored dot plus a text label (never color alone)."""
    return f'<span class="chip {kind}">{html.escape(text)}</span>'


def gate_kind(status: str) -> str:
    """Map a gate status to a status color."""
    s = status.lower()
    if s.startswith("loaded") or s.startswith("runs"):
        return "good"
    if s.startswith("refused") or s.startswith("failed"):
        return "critical"
    return "warning"


def table(table_id: str, lines: list[dict[str, str]], cols: list[str], columns_help: dict[str, str]) -> str:
    """A sortable table. Verdict and status cells become chips."""
    head = "".join(
        f"<th onclick=\"sortTable('{table_id}',{i})\">{html.escape(c)}"
        f' <span class="info" title="{html.escape(columns_help.get(c, ""))}">ⓘ</span></th>'
        for i, c in enumerate(cols)
    )
    body = []
    for line in lines:
        cells = []
        for c in cols:
            value = line.get(c, "")
            if c in ("decode_verdict", "prefill_verdict") and value in VERDICT_STYLE:
                cells.append(f"<td>{chip(VERDICT_STYLE[value][0], value)}</td>")
            elif c == "status":
                cells.append(f"<td>{chip(gate_kind(value), value)}</td>")
            else:
                cells.append(f"<td>{html.escape(value)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    if not body:
        body.append(f'<tr><td colspan="{len(cols)}">No rows yet.</td></tr>')
    return (
        f'<div class="tablewrap"><table id="{table_id}"><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def render(
    verdict: str,
    specs: dict[str, dict[str, Any]],
    cell_stats: list[dict[str, Any]],
    comps: list[dict[str, str]],
    tables: list[tuple[str, str, list[dict[str, str]], list[str]]],
    columns_help: dict[str, str],
) -> str:
    """Return the page. cell_stats rows: site, workload, ctx, arm, decode/prefill Summary fields."""
    families: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in cell_stats:
        spec = specs.get(item["arm"], {})
        families[(item["site"], str(spec.get("family", item.get("model", "?"))))].append(item)

    used_roles = sorted({role(specs.get(i["arm"], {})) for i in cell_stats}, key=list(ROLES).index)
    legend = "".join(f'<span><i class="sw {ROLES[r][0]}"></i>{html.escape(ROLES[r][1])}</span>' for r in used_roles)

    tiles = []
    for c in comps:
        if c["workload"] == "C" or c["decode_ratio"] == "–":
            continue
        kind, text = VERDICT_STYLE.get(c["decode_verdict"], ("neutral", c["decode_verdict"]))
        tiles.append(
            f'<div class="tile {kind}"><div class="k">{html.escape(c["site"])} · '
            f"{html.escape(WORKLOAD_NAMES.get(c['workload'], c['workload']))} · {html.escape(c['ctx'])} ctx</div>"
            f'<div class="v">{html.escape(c["decode_ratio"])}</div>'
            f'<div class="d">decode, {html.escape(c["pair"])}</div>{chip(kind, text)}</div>'
        )

    sections = []
    for (site, family), items in sorted(families.items()):
        charts = []
        for metric, label, unit in (
            ("decode", "Decode speed (tok/s, higher is better)", "tok/s"),
            ("prefill", "Prefill speed (tok/s, higher is better)", "tok/s"),
        ):
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for i in sorted(
                items, key=lambda x: (x["workload"], int(x["ctx"]), list(ROLES).index(role(specs.get(x["arm"], {}))))
            ):
                if i["workload"] == "C" or not i[f"{metric}_n"]:
                    continue
                groups[f"{WORKLOAD_NAMES.get(i['workload'], i['workload'])} · {i['ctx']} ctx"].append(
                    {
                        "arm": i["arm"],
                        "slot": ROLES[role(specs.get(i["arm"], {}))][0],
                        "median": i[f"{metric}_median"],
                        "low": i[f"{metric}_low"],
                        "high": i[f"{metric}_high"],
                        "n": i[f"{metric}_n"],
                    }
                )
            charts.append(bar_chart(label, unit, list(groups.items())))
        sections.append(
            f'<section class="model"><h3>{html.escape(family)} · {html.escape(site)}</h3>'
            f'<div class="charts">{"".join(charts)}</div></section>'
        )

    table_html = "".join(
        f"<h2>{html.escape(title)}</h2>{table(tid, lines, cols, columns_help)}" for title, tid, lines, cols in tables
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Magnitude vs Ollama</title><style>{CSS}</style></head><body><main>
<h1>Magnitude vs Ollama</h1>
<p class="sub">Generated by <code>mvo report</code> from <code>results/*.jsonl</code>. Do not edit.
Hover a bar for details. Click a table header to sort.</p>
<div class="banner">{html.escape(verdict)}</div>
<h2>Speed ratios (Magnitude ÷ Ollama, decode)</h2><div class="tiles">{"".join(tiles) or "<p>No pairs yet.</p>"}</div>
<h2>Charts per model</h2><div class="legend">{legend}</div>{"".join(sections) or "<p>No rows yet.</p>"}
{table_html}
<details><summary>Arm notes</summary><ul>{
        "".join(
            f"<li><code>{html.escape(k)}</code>: {html.escape(str(v.get('note', '')))}</li>" for k, v in specs.items()
        )
    }</ul></details>
<div id="tip"></div><script>{JS}</script></main></body></html>
"""
