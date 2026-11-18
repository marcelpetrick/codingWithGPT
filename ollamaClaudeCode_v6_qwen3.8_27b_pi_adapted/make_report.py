#!/usr/bin/env python3
"""make_report.py -- generate report.html for round v6 from the result files. Never edit the HTML.

It reuses refresh-compare.py (round 11-02) for validity and scoring, so the report and the rule
cannot disagree. Arms: pi1118 (pi, base, KAT = champion, occamy = runner-up) and pi1118q8 (pi Q8_0).

Usage: python3 make_report.py            -> report.html
"""
import csv
import html
import importlib.util
import json
import statistics
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
V4 = HERE.parent / "ollamaClaudeCode_v4_tielCoder"
spec = importlib.util.spec_from_file_location("rc", V4 / "refresh-compare.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)

PI = "qwen3.8-pi:27b-q4km-ctx200k-nothink"
BASE = "qwen3.8-base:27b-q4km-ctx200k-nothink"
KAT = "kat-coder-v2.5:q5km-ctx256k-agentic"
OCC = "occamy-1.0:q5km-ctx256k-agentic"
PIQ8 = "qwen3.8-pi:27b-q8-ctx64k-nothink"
TASKS = [("hard", "Python"), ("qtcpp", "Qt/C++"), ("gitlab", "GitLab"), ("summary", "Summary")]

MODELS = [  # tag, arm, short name, role, (i) text (max five sentences)
    (PI, "pi1118", "Qwen3.8-27B pi", "subject",
     "Qwen3.8-27B with the harness-hub pi LoRA, merged into the Q8_0 base and requantized to Q4_K_M. "
     "The adapter was trained with RL for the pi coding agent, with thinking off. "
     "Thinking is forced off here too. It is a dense 27B model, so every token uses all weights. "
     "It runs at num_ctx 200000, 31.2 GB, 100% GPU."),
    (BASE, "pi1118", "Qwen3.8-27B base", "control",
     "The same Q8_0 base and the same Q4_K_M requantization, without the adapter. "
     "Any difference to the pi row comes from the adapter (or from rounding noise). "
     "Same window, sampler and thinking-off setting as pi."),
    (KAT, "pi1118", "KAT-Coder-V2.5", "champion",
     "Kwaipilot KAT-Coder-V2.5-Dev, a Qwen3.6-35B-A3B fine-tune, Q5_K_M. "
     "The default alias claude-ol-kat since 2026-10-19. "
     "A mixture-of-experts model with about 3B active weights, so it is fast. "
     "Re-measured in this arm, under the same server state."),
    (OCC, "pi1118", "occamy-1.0", "runner-up",
     "occamy-1.0, Q5_K_M, a 35B-A3B mixture-of-experts model. "
     "Second in the 10-19 pick and first in the unfinished 11-02 interim (98.3, n=2). "
     "Re-measured in this arm, under the same server state."),
    (PIQ8, "pi1118q8", "Qwen3.8-27B pi Q8_0", "drift check",
     "The merged pi model at Q8_0, the precision the card recommends. "
     "It fits only a 65536 window on the box, so it has no summary score. "
     "It shows whether Q4_K_M rounding hides the adapter."),
]
COLORS = {PI: "--s1", BASE: "--s2", KAT: "--s3", OCC: "--s4", PIQ8: "--s5"}
COL_INFO = {
    "correct": "The rule of round 11-02: the mean, over four tasks, of the median share of checks passed. "
               "A model needs n>=2 per task and T5>=7/8 to be ranked. Within 3 points, the shorter session wins.",
    "Python": "Fix a three-module ledger bug with Claude Code. 18 hidden tests score the result.",
    "Qt/C++": "A Qt 6 list model with signals, object lifetime, CMake and ctest. 14 hidden tests.",
    "GitLab": "Apply meeting notes with glab, including reversed decisions and tickets that must stay untouched. 15 checks of the final state.",
    "Summary": "Summarize a log of about 150k tokens. 12 facts and 4 corrections are checked; above 600 words scores 0.",
    "T5": "Nested-schema tool calls, 8 trials. Below 7/8 the model is not ranked.",
    "n": "The smallest number of valid runs over the tasks. 3 is final, 2 is preliminary.",
    "session": "The sum of the median wall times of the three session tasks. A session stops at 600 s and keeps its score.",
    "calls": "Median number of tool calls over all valid sessions. The card claims the adapter cuts tool calls by 55-64%.",
    "gen": "Generation speed at about 150k tokens of context (summary probe, median).",
    "prefill": "Cold prefill speed of the 150k-token prompt.",
}


def tsv_rows(arm):
    f = V4 / "results" / f"cc-session-{arm}.tsv"
    if not f.exists():
        return []
    with f.open() as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def collect():
    out = []
    cache = {}
    for tag, arm, name, role, info in MODELS:
        if arm not in cache:
            cache[arm] = rc.summarize(arm)
        e = cache[arm].get(tag)
        if not e:
            continue
        rows = [r for r in tsv_rows(arm) if r["model"] == tag and r["thinking"] == "on"
                and rc.void_reason(r, tag, r["fixture"], int(r["run"]), arm) is None]
        last = {}
        for r in rows:
            last[(r["fixture"], int(r["run"]))] = r
        calls = [int(r["calls"]) for r in last.values() if r["calls"].isdigit()]
        runs = {fx: [] for fx, _ in TASKS}
        for (fx, run), r in sorted(last.items(), key=lambda kv: kv[0][1]):
            runs[fx].append({"run": run, "score": r["hidden"], "wall": rc.num(r["wall_s"]),
                             "calls": r["calls"], "timeout": "timeout" in r.get("note", "")})
        for (t, run), r in sorted(rc.summary_rows(arm).items()):
            if t == tag and not r["void"]:
                runs["summary"].append({"run": run, "score": r["score"], "wall": rc.num(r["wall_s"]),
                                        "words": r["words"]})
        med = {fx: (100 * statistics.median(v) if v else None) for fx, v in e["tasks"].items()}
        wall = {fx: (statistics.median(v) if v else None) for fx, v in e["walls"].items()}
        three = [med[k] for k in ("hard", "qtcpp", "gitlab")]
        sp = e["speed"]
        gen = [rc.num(r["gen_tps"]) for r in sp.values() if rc.num(r["gen_tps"])]
        out.append({
            "tag": tag, "name": name, "role": role, "info": info, "color": COLORS[tag], "arm": arm,
            "correct": e["correct"], "three": sum(three) / 3 if None not in three else None,
            "med": med, "wall": wall, "session": e["session_s"], "t5": e["t5"], "n": e["n"],
            "ranked": e["ranked"], "calls": statistics.median(calls) if calls else None,
            "gen": statistics.median(gen) if gen else None,
            "prefill": rc.num(sp.get("cold", {}).get("prefill_tps")), "runs": runs, "void": e["void"],
        })
    return out


def verdict(ms):
    by = {m["tag"]: m for m in ms}
    pi, base, kat, occ = by.get(PI), by.get(BASE), by.get(KAT), by.get(OCC)
    lines = []
    if not (pi and kat and pi["correct"] is not None and kat["correct"] is not None):
        return "Not enough data for a verdict yet.", []
    final = all(m and m["n"] >= 3 for m in (pi, base, kat))
    t5ok = pi["t5"].split("/")[0].isdigit() and int(pi["t5"].split("/")[0]) >= rc.T5_MIN
    d = pi["correct"] - kat["correct"]
    if t5ok and d > rc.TIE_POINTS:
        v = "Use Qwen3.8-27B pi as the default: it is more than 3 points more correct than KAT."
    elif t5ok and d >= -rc.TIE_POINTS:
        v = ("Keep Qwen3.8-27B pi as an extra alias, not as the default: its correctness ties KAT "
             "(%+.1f points), and KAT is faster." % d)
    else:
        v = "Do not use Qwen3.8-27B pi here: it is %.1f points less correct than KAT." % -d
    if not final:
        v = "Preliminary (n<3). " + v
    lines.append("pi %.1f vs KAT %.1f correctness; sessions %s s vs %s s." % (
        pi["correct"], kat["correct"], fmt(pi["session"]), fmt(kat["session"])))
    if base and base["correct"] is not None:
        a = pi["correct"] - base["correct"]
        lines.append("Adapter vs its own base: %+.1f points (%s)." % (
            a, "the adapter helps" if a > rc.TIE_POINTS else "a tie under the rule"))
    if occ and occ["correct"] is not None:
        lines.append("Runner-up occamy: %.1f correctness, sessions %s s." % (occ["correct"], fmt(occ["session"])))
    return v, lines


def fmt(x, d=0):
    return "-" if x is None else ("%.*f" % (d, x))


def main():
    ms = collect()
    v, lines = verdict(ms)
    data = json.dumps({"models": ms, "tasks": TASKS, "colInfo": COL_INFO})
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = TEMPLATE.replace("__DATA__", data).replace("__VERDICT__", html.escape(v)) \
        .replace("__LINES__", "".join("<li>%s</li>" % html.escape(x) for x in lines)) \
        .replace("__STAMP__", stamp)
    (HERE / "report.html").write_text(page)
    print("report.html:", v)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Qwen3.8 pi round</title>
<style>
:root{color-scheme:light;--bg:#eefaf4;--surface:#f4fbf7;--card:#ffffff;--ink:#12322a;--ink2:#4a6b61;--muted:#7d968e;
--line:#d3ece2;--grid:#e3f3ec;--accent:#3cc99a;--accent-soft:#c9f2e2;
--s1:#1baf7a;--s2:#2a78d6;--s3:#eb6834;--s4:#6250d6;--s5:#e87ba4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0f1a16;--surface:#14201b;--card:#18261f;
--ink:#e4f5ee;--ink2:#a9c7bc;--muted:#7f9d92;--line:#28423a;--grid:#1f332c;--accent:#48d6a6;--accent-soft:#1f3d33;
--s1:#199e70;--s2:#3987e5;--s3:#d95926;--s4:#9085e9;--s5:#d55181}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0f1a16;--surface:#14201b;--card:#18261f;--ink:#e4f5ee;--ink2:#a9c7bc;--muted:#7f9d92;
--line:#28423a;--grid:#1f332c;--accent:#48d6a6;--accent-soft:#1f3d33;--s1:#199e70;--s2:#3987e5;--s3:#d95926;--s4:#9085e9;--s5:#d55181}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1080px;margin:0 auto;padding:28px 16px 60px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}h2{font-size:17px;margin:0 0 4px}
.sub{color:var(--ink2);margin:0 0 20px}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin:16px 0;box-shadow:0 1px 0 var(--grid)}
.verdict{background:linear-gradient(135deg,var(--accent-soft),var(--card));border-color:var(--accent)}
.verdict p{font-size:18px;font-weight:600;margin:0 0 6px}.verdict ul{margin:6px 0 0;padding-left:20px;color:var(--ink2)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;border-top:4px solid var(--c)}
.tile .n{font-size:28px;font-weight:700}.tile .l{color:var(--ink2);font-size:13px}.tile .r{color:var(--muted);font-size:12px}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:8px 0 4px;font-size:13px;color:var(--ink2)}
.legend>span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:3px;background:var(--c);margin-right:6px;vertical-align:-1px}
.hint{color:var(--muted);font-size:13px;margin:0}
svg{display:block;width:100%;height:auto;overflow:visible}svg text{fill:var(--ink2);font-size:12px}
.tip{position:fixed;pointer-events:none;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:8px 10px;
font-size:13px;box-shadow:0 6px 20px rgba(0,40,30,.15);display:none;max-width:280px;z-index:9}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:600;cursor:pointer;user-select:none}th[aria-sort]::after{content:" ↕";color:var(--muted)}
.i{display:inline-grid;place-items:center;width:16px;height:16px;border-radius:50%;background:var(--accent-soft);color:var(--ink);
font-size:11px;font-weight:700;margin-left:4px;cursor:help;font-style:normal}
.dot{display:inline-block;width:10px;height:10px;border-radius:3px;background:var(--c);margin-right:6px}
.role{font-size:11px;color:var(--muted);margin-left:4px}footer{color:var(--muted);font-size:12px;margin-top:24px}
</style></head><body><main>
<h1>Qwen3.8-27B "pi" on the Ollama box</h1>
<p class="sub">Round v6 · arm pi1118 · Ollama 0.40.11 · generated __STAMP__ from the result files by <code>make_report.py</code></p>
<section class="card verdict"><p>__VERDICT__</p><ul>__LINES__</ul></section>
<section class="tiles" id="tiles"></section>
<section class="card"><h2>Correctness per task</h2><p class="hint">Median share of checks passed. Hover a bar for every run.</p>
<div class="legend" id="lg1"></div><div id="c1"></div></section>
<section class="card"><h2>Median session time per task</h2><p class="hint">Seconds of wall time with Claude Code; a session stops at 600 s. Shorter is better.</p>
<div class="legend" id="lg2"></div><div id="c2"></div></section>
<section class="card"><h2>Tool calls per session</h2><p class="hint">Median over all valid sessions. The card claims the adapter cuts tool calls by 55–64%.</p><div id="c3"></div></section>
<section class="card"><h2>All numbers</h2><p class="hint">Click a column to sort. Hover (i) for what a column or a model means.</p>
<div class="scroll"><table id="tbl"></table></div></section>
<footer>Rule fixed before the data: ROUND_2026-11-02.md and README.md of this folder. Void runs (spill, reload, foreign model, crash) are not counted.</footer>
</main><div class="tip" id="tip"></div>
<script>
const D=__DATA__;const M=D.models;const T=D.tasks;const tip=document.getElementById("tip");
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const f=(x,d=0)=>x==null?"–":x.toFixed(d);
function showTip(e,h){tip.innerHTML=h;tip.style.display="block";const x=Math.min(e.clientX+14,innerWidth-300);tip.style.left=x+"px";tip.style.top=(e.clientY+14)+"px"}
function hideTip(){tip.style.display="none"}
function legend(id,ms){document.getElementById(id).innerHTML=ms.map(m=>`<span style="--c:var(${m.color})">${m.name} <span class="role">${m.role}</span></span>`).join("")}
// tiles
document.getElementById("tiles").innerHTML=M.filter(m=>m.arm==="pi1118").map(m=>`<div class="tile" style="--c:var(${m.color})">
<div class="l">${m.name} · ${m.role}</div><div class="n">${f(m.correct,1)}</div><div class="r">correctness · ${f(m.session)} s sessions · T5 ${m.t5} · n=${m.n}</div></div>`).join("");
function bars(id,ms,tasks,val,max,unit,tipf){
 const W=1000,H=300,L=44,R=10,TOP=14,B=34,g=tasks.length,gw=(W-L-R)/g,bw=Math.min(26,(gw-24)/ms.length-2);
 let s=`<svg viewBox="0 0 ${W} ${H}" role="img">`;
 for(let k=0;k<=4;k++){const v=max*k/4,y=TOP+(H-TOP-B)*(1-k/4);s+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="${css('--grid')}"/><text x="${L-6}" y="${y+4}" text-anchor="end">${Math.round(v)}${unit}</text>`}
 tasks.forEach((t,ti)=>{const x0=L+ti*gw+(gw-ms.length*(bw+2))/2;s+=`<text x="${L+ti*gw+gw/2}" y="${H-10}" text-anchor="middle">${t[1]}</text>`;
  ms.forEach((m,mi)=>{const v=val(m,t[0]);if(v==null)return;const h=Math.max(2,(H-TOP-B)*Math.min(v,max)/max),x=x0+mi*(bw+2),y=H-B-h;
   s+=`<path d="M${x},${H-B} V${y+4} q0,-4 4,-4 h${bw-8} q4,0 4,4 V${H-B} Z" fill="var(${m.color})" data-m="${mi}" data-t="${ti}" class="bar"/>`;
   if(bw>=14)s+=`<text x="${x+bw/2}" y="${y-4}" text-anchor="middle" style="font-size:11px;fill:var(--ink)">${Math.round(v)}</text>`;
   s+=`<rect x="${x-1}" y="${TOP}" width="${bw+2}" height="${H-TOP-B}" fill="transparent" data-m="${mi}" data-t="${ti}" class="hit"/>`})});
 s+=`<line x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}" stroke="${css('--line')}"/></svg>`;
 const el=document.getElementById(id);el.innerHTML=s;
 el.querySelectorAll(".hit").forEach(r=>{r.addEventListener("mousemove",e=>showTip(e,tipf(ms[+r.dataset.m],tasks[+r.dataset.t])));r.addEventListener("mouseleave",hideTip)})}
const runTxt=(m,t)=>(m.runs[t[0]]||[]).map(r=>`r${r.run}: ${r.score}${r.wall!=null?" · "+Math.round(r.wall)+" s":""}${r.calls?" · "+r.calls+" calls":""}${r.timeout?" · timeout":""}`).join("<br>")||"no valid run";
legend("lg1",M);bars("c1",M,T,(m,t)=>m.med[t],100,"%",(m,t)=>`<b>${m.name}</b> · ${t[1]}<br>median ${f(m.med[t[0]])}%<br>${runTxt(m,t)}`);
const S=T.filter(t=>t[0]!=="summary");legend("lg2",M);
bars("c2",M,S,(m,t)=>m.wall[t],600," s",(m,t)=>`<b>${m.name}</b> · ${t[1]}<br>median ${f(m.wall[t[0]])} s<br>${runTxt(m,t)}`);
bars("c3",M,[["calls","all sessions"]],(m)=>m.calls,Math.max(10,...M.map(m=>m.calls||0))*1.15,"",(m)=>`<b>${m.name}</b><br>median ${f(m.calls)} tool calls per session`);
// table
const cols=[["model",m=>m.name],["correct",m=>m.correct,1],["Python",m=>m.med.hard],["Qt/C++",m=>m.med.qtcpp],["GitLab",m=>m.med.gitlab],
["Summary",m=>m.med.summary],["T5",m=>parseInt(m.t5)||null,null,m=>m.t5],["n",m=>m.n],["session",m=>m.session],["calls",m=>m.calls],["gen",m=>m.gen],["prefill",m=>m.prefill]];
let sortK=1,dir=-1;
function table(){const rows=[...M].sort((a,b)=>{const x=cols[sortK][1](a),y=cols[sortK][1](b);if(x==null)return 1;if(y==null)return -1;return (x>y?1:x<y?-1:0)*dir});
 const esc=s=>s.replace(/"/g,"&quot;");
 let h="<thead><tr>"+cols.map((c,i)=>`<th data-i="${i}" aria-sort="none">${c[0]}${D.colInfo[c[0]]?`<i class="i" title="${esc(D.colInfo[c[0]])}">i</i>`:""}</th>`).join("")+"</tr></thead><tbody>";
 rows.forEach(m=>{h+="<tr>"+cols.map((c,i)=>{if(i===0)return `<td><span class="dot" style="--c:var(${m.color})"></span>${m.name}<span class="role">${m.role}</span><i class="i" title="${esc(m.info)}">i</i></td>`;
  const v=c[3]?c[3](m):c[1](m);return `<td>${typeof v==="string"?v:f(v,c[2]||0)}</td>`}).join("")+"</tr>"});
 document.getElementById("tbl").innerHTML=h+"</tbody>";
 document.querySelectorAll("#tbl th").forEach(th=>th.onclick=()=>{const i=+th.dataset.i;dir=(i===sortK)?-dir:-1;sortK=i;table()})}
table();
</script></body></html>
"""

if __name__ == "__main__":
    main()
