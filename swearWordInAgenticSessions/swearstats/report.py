"""Render a portable, dependency-free HTML dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_report(data: dict[str, Any], output: Path) -> None:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_document(payload), encoding="utf-8")


def _document(payload: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Agentic Swear Jar</title>
<style>
:root{{--ink:#f5f1e8;--muted:#9d9a91;--night:#0c0c0c;--panel:#151515;--line:#2a2927;--acid:#d7ff44;--pink:#ff5c8a;--blue:#62d6ff;--orange:#ff9b42;--radius:22px}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:var(--night);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.45}}
body:before{{content:"";position:fixed;inset:0;pointer-events:none;opacity:.18;background-image:radial-gradient(#fff 0.5px,transparent .5px);background-size:7px 7px;mask-image:linear-gradient(to bottom,#000,transparent 65%)}}
.wrap{{width:min(1180px,calc(100% - 32px));margin:auto}} header{{padding:72px 0 36px;position:relative}}
.eyebrow{{font:700 12px/1 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.18em;text-transform:uppercase;color:var(--acid)}}
h1{{font-size:clamp(54px,10vw,126px);letter-spacing:-.075em;line-height:.78;margin:24px 0 32px;max-width:980px}} h1 em{{font-style:normal;color:var(--acid)}}
.lede{{font-size:clamp(18px,2.1vw,26px);max-width:720px;color:#c8c5bd;margin:0}} .lede strong{{color:var(--ink)}}
.stamp{{position:absolute;right:0;top:80px;width:130px;height:130px;border:1px solid var(--line);border-radius:50%;display:grid;place-items:center;text-align:center;font:700 11px/1.35 ui-monospace,monospace;color:var(--muted);transform:rotate(8deg)}}
.tabs{{display:flex;gap:8px;position:sticky;top:12px;z-index:5;margin:28px 0;padding:7px;width:max-content;max-width:100%;background:#181818e8;border:1px solid var(--line);border-radius:999px;backdrop-filter:blur(16px)}}
.tab{{border:0;border-radius:999px;padding:10px 18px;background:transparent;color:var(--muted);font:700 13px/1 inherit;cursor:pointer;white-space:nowrap}} .tab.active{{background:var(--ink);color:var(--night)}}
.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}} .panel{{grid-column:span 12;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:24px;overflow:hidden;position:relative}}
.metric{{grid-column:span 3;min-height:180px;display:flex;flex-direction:column;justify-content:space-between}} .metric .value{{font-size:clamp(38px,5vw,67px);font-weight:800;line-height:.9;letter-spacing:-.06em}} .metric .label{{font:700 11px/1.2 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}} .metric small{{color:var(--muted)}}
.metric.hot{{background:var(--acid);color:#111;border-color:var(--acid)}} .metric.hot .label,.metric.hot small{{color:#3d451d}}
.half{{grid-column:span 6}} .third{{grid-column:span 4}} h2{{font-size:26px;letter-spacing:-.035em;margin:0 0 4px}} .sub{{color:var(--muted);margin:0 0 26px;font-size:14px}}
.bar-row{{display:grid;grid-template-columns:minmax(78px,1.2fr) 4fr 48px;align-items:center;gap:12px;margin:13px 0;font-size:13px}} .bar{{height:9px;border-radius:99px;background:#292927;overflow:hidden}} .bar i{{display:block;height:100%;border-radius:inherit;background:var(--acid)}} .bar-row b{{text-align:right;font-variant-numeric:tabular-nums}}
.chart{{height:250px;width:100%;display:block}} .chart text{{fill:var(--muted);font:11px ui-monospace,monospace}} .axis{{stroke:#343331;stroke-width:1}} .line{{fill:none;stroke:var(--acid);stroke-width:3;stroke-linecap:round;stroke-linejoin:round}} .area{{fill:url(#fade)}}
.heat{{display:grid;grid-template-columns:repeat(24,minmax(7px,1fr));gap:4px;align-items:end;height:150px}} .heat-col{{display:flex;flex-direction:column;gap:4px;height:100%;justify-content:flex-end}} .heat-cell{{min-height:6px;border-radius:3px;background:var(--acid)}} .hour-labels{{display:grid;grid-template-columns:repeat(6,1fr);font:10px ui-monospace,monospace;color:var(--muted);margin-top:8px}}
.comparison{{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:center}} .versus{{font:800 11px ui-monospace,monospace;color:var(--muted)}} .side{{padding:22px;border:1px solid var(--line);border-radius:17px}} .side strong{{display:block;font-size:38px;letter-spacing:-.05em}} .side.codex{{border-color:#275062}} .side.claude{{border-color:#5a442d}}
.daily-grid{{display:grid;grid-template-columns:repeat(53,1fr);grid-template-rows:repeat(7,10px);grid-auto-flow:column;gap:3px;overflow:hidden}} .day{{width:100%;height:10px;border-radius:2px;background:#222}} .day[data-level="1"]{{background:#39451b}}.day[data-level="2"]{{background:#647b23}}.day[data-level="3"]{{background:#99bd32}}.day[data-level="4"]{{background:var(--acid)}}
table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{padding:12px 8px;border-bottom:1px solid var(--line);text-align:left}} th{{font:700 10px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}} td:last-child,th:last-child{{text-align:right}} .rank{{color:var(--muted);width:30px}} code{{font-family:ui-monospace,monospace;color:var(--acid)}}
.legend{{display:flex;gap:16px;align-items:center;font:11px ui-monospace,monospace;color:var(--muted);margin-top:16px}} .dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}} .empty{{color:var(--muted);padding:60px 0;text-align:center}}
.privacy{{margin:32px 0;padding:22px;border:1px dashed #46443f;border-radius:16px;color:var(--muted);font-size:13px;display:flex;gap:12px}} footer{{padding:30px 0 70px;color:var(--muted);font:11px ui-monospace,monospace;display:flex;justify-content:space-between;gap:20px}}
@media(max-width:800px){{.metric{{grid-column:span 6}}.half,.third{{grid-column:span 12}}.stamp{{display:none}}.comparison{{grid-template-columns:1fr}}.versus{{text-align:center}}}}
@media(max-width:480px){{header{{padding-top:48px}}.metric{{grid-column:span 12;min-height:140px}}.tabs{{width:100%;overflow:auto}}.tab{{padding:10px 14px}}.panel{{padding:19px}}}}
@media(prefers-reduced-motion:no-preference){{.panel{{animation:rise .5s both}}.panel:nth-child(2){{animation-delay:.04s}}.panel:nth-child(3){{animation-delay:.08s}}@keyframes rise{{from{{opacity:0;transform:translateY(10px)}}}}}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">Local telemetry / zero judgment</div>
  <h1>Agentic<br><em>Swear Jar.</em></h1>
  <p class="lede">A field report from the moments when code fought back. <strong>The harness is a machine. No feelings were hurt.</strong></p>
  <div class="stamp">PROMPTS IN<br>NUMBERS<br>✦<br>100% LOCAL</div>
</header>
<nav class="tabs" id="tabs" aria-label="Data source"></nav>
<main class="grid" id="dashboard"></main>
<div class="privacy"><span>◉</span><span><strong>Private by construction.</strong> This file contains aggregate counts only. No prompt text, session IDs, or project paths are embedded.</span></div>
<footer><span id="period"></span><span id="generated"></span></footer>
</div>
<script id="report-data" type="application/json">{payload}</script>
<script>
const DATA=JSON.parse(document.getElementById('report-data').textContent);let active='all';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const fmt=n=>new Intl.NumberFormat().format(n||0);const pct=n=>`${{Number(n||0).toFixed(1)}}%`;
const metric=(value,label,note,hot='')=>`<article class="panel metric ${{hot}}"><div class="label">${{label}}</div><div class="value">${{value}}</div><small>${{note}}</small></article>`;
function bars(items,color='var(--acid)'){{const max=Math.max(1,...items.map(x=>x[1]));return items.map(([name,value])=>`<div class="bar-row"><span>${{esc(name)}}</span><div class="bar"><i style="width:${{value/max*100}}%;background:${{color}}"></i></div><b>${{fmt(value)}}</b></div>`).join('')||'<div class="empty">No hits in this slice. Impressive restraint.</div>'}}
function lineChart(rows){{if(!rows.length)return '<div class="empty">Not enough dated prompts yet.</div>';const w=620,h=220,p=28,max=Math.max(1,...rows.map(x=>x.prompt_rate));const pts=rows.map((x,i)=>`${{p+(w-2*p)*(rows.length===1?.5:i/(rows.length-1))}},${{h-p-(h-2*p)*x.prompt_rate/max}}`).join(' ');const labels=rows.filter((_,i)=>i===0||i===rows.length-1||i%Math.ceil(rows.length/5)===0).map((x,i,a)=>`<text x="${{p+(w-2*p)*(rows.indexOf(x)/(Math.max(1,rows.length-1)))}}" y="214" text-anchor="${{i===0?'start':i===a.length-1?'end':'middle'}}">${{esc(x.month)}}</text>`).join('');return `<svg class="chart" viewBox="0 0 ${{w}} ${{h}}" preserveAspectRatio="none"><defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#d7ff44" stop-opacity=".25"/><stop offset="1" stop-color="#d7ff44" stop-opacity="0"/></linearGradient></defs><line class="axis" x1="${{p}}" y1="${{h-p}}" x2="${{w-p}}" y2="${{h-p}}"/><polygon class="area" points="${{p}},${{h-p}} ${{pts}} ${{w-p}},${{h-p}}"/><polyline class="line" points="${{pts}}"/>${{labels}}</svg>`}}
function heatmap(hours){{const max=Math.max(1,...hours.map(x=>x.hits));return `<div class="heat">${{hours.map((x,i)=>`<div class="heat-col" title="${{i}}:00 — ${{x.hits}} hits in ${{x.prompts}} prompts"><div class="heat-cell" style="height:${{Math.max(5,x.hits/max*100)}}%;opacity:${{x.hits?.25+x.hits/max*.75:.08}}"></div></div>`).join('')}}</div><div class="hour-labels"><span>00</span><span>04</span><span>08</span><span>12</span><span>16</span><span>20</span></div>`}}
function calendar(rows){{const recent=rows.slice(-371);const max=Math.max(1,...recent.map(x=>x.hits));return `<div class="daily-grid">${{recent.map(x=>{{const level=x.hits?Math.max(1,Math.ceil(x.hits/max*4)):0;return `<span class="day" data-level="${{level}}" title="${{x.date}} — ${{x.hits}} hits / ${{x.prompts}} prompts"></span>`}}).join('')}}</div><div class="legend"><span>Last ${{recent.length}} days</span><span><i class="dot" style="background:#222"></i>quiet</span><span><i class="dot" style="background:var(--acid)"></i>spicy</span></div>`}}
function sourceComparison(){{const c=DATA.sources.claude?.totals,x=DATA.sources.codex?.totals;if(!c||!x)return '';return `<article class="panel"><h2>Harness face-off</h2><p class="sub">Normalized by prompt count, because volume alone is a lousy referee.</p><div class="comparison"><div class="side claude"><span>Claude Code</span><strong>${{c.hits_per_100_prompts}}</strong><small>hits / 100 prompts · ${{fmt(c.prompts)}} prompts total</small></div><div class="versus">VERSUS</div><div class="side codex"><span>Codex CLI</span><strong>${{x.hits_per_100_prompts}}</strong><small>hits / 100 prompts · ${{fmt(x.prompts)}} prompts total</small></div></div></article>`}}
function render(key){{active=key;document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.key===key));const s=DATA.sources[key],t=s.totals;const top=s.terms.slice(0,10);const sev=[['mild',s.severity['1']],['moderate',s.severity['2']],['strong',s.severity['3']]];document.getElementById('dashboard').innerHTML=
metric(fmt(t.prompts),'Prompts scanned',`${{fmt(t.words)}} words, streamed locally`)+
metric(fmt(t.hits),'Total swear hits',`${{t.hits_per_1000_words}} per 1,000 words`,'hot')+
metric(pct(t.prompt_rate),'Spicy prompts',`${{fmt(t.profane_prompts)}} prompts contained ≥1 hit`)+
metric(fmt(s.streaks.longest_clean),'Longest clean run','consecutive prompts')+
(key==='all'?sourceComparison():'')+
`<article class="panel half"><h2>Pressure over time</h2><p class="sub">Monthly share of prompts containing at least one match.</p>${{lineChart(s.monthly)}}</article>`+
`<article class="panel half"><h2>When the code bites</h2><p class="sub">Raw matches by local hour of day.</p>${{heatmap(s.hourly)}}</article>`+
`<article class="panel half"><h2>The vocabulary</h2><p class="sub">Inflections collapse into their canonical form.</p>${{bars(top.map(x=>[x.term,x.count]))}}</article>`+
`<article class="panel half"><h2>Intensity mix</h2><p class="sub">A deliberately simple three-level lexicon rating.</p>${{bars(sev,'var(--pink)')}}</article>`+
`<article class="panel"><h2>Activity field</h2><p class="sub">Daily match intensity. Hover a square for exact counts.</p>${{calendar(DATA.daily[key]||[])}}</article>`+
`<article class="panel half"><h2>Prompt length</h2><p class="sub">Which prompt sizes are most likely to turn spicy?</p>${{bars(s.lengths.map(x=>[x.label+' words',x.prompt_rate]),'var(--blue)')}}</article>`+
`<article class="panel half"><h2>Top terms, audited</h2><p class="sub">Exact whole-word matches; no fuzzy AI classification.</p><table><thead><tr><th>#</th><th>Canonical term</th><th>Hits</th></tr></thead><tbody>${{top.map((x,i)=>`<tr><td class="rank">${{i+1}}</td><td><code>${{esc(x.term)}}</code></td><td>${{fmt(x.count)}}</td></tr>`).join('')||'<tr><td colspan="3">Nothing found.</td></tr>'}}</tbody></table></article>`;
}}
const tabs=document.getElementById('tabs');Object.entries(DATA.sources).forEach(([key,s])=>{{const b=document.createElement('button');b.className='tab';b.dataset.key=key;b.textContent=s.label;b.onclick=()=>render(key);tabs.appendChild(b)}});
document.getElementById('period').textContent=DATA.period.first?`Observed ${{new Date(DATA.period.first).toLocaleDateString()}} — ${{new Date(DATA.period.last).toLocaleDateString()}}`:'No dated prompts';
document.getElementById('generated').textContent=`Generated ${{new Date(DATA.generated_at).toLocaleString()}} · ${{DATA.lexicon_size}} variants`;
render('all');
</script>
</body>
</html>"""
