#!/usr/bin/env python3
"""Build the one-page evaluation PDF from the measured TSVs.

Reads:  eval/rows.tsv          (speed, footprint, context ceiling)
        agentic/*.tsv          (the seven agentic gates, per model)
Writes: evaluation.html  ->  evaluation.pdf   (via headless chromium)

Chart choices, per the dataviz method:
  - throughput is a magnitude comparison across a handful of named items, so a
    horizontal bar chart, sorted, with direct value labels
  - one series means one hue and no legend; the title names the measure
  - colors are the reference palette's light-mode slot 1 and text tokens
  - print target, so the page deliberately commits to the light surface
"""
import csv, glob, html, os, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SURFACE, INK, INK2, INK3 = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8880"
SERIES = "#2a78d6"
GOOD, WARN, BAD = "#008300", "#eda100", "#e34948"

def read_tsv(p):
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return list(csv.DictReader(f, delimiter="\t"))

rows = read_tsv(os.path.join(HERE, "eval", "rows.tsv"))

agentic = {}
for p in sorted(glob.glob(os.path.join(HERE, "agentic", "*.tsv"))):
    if p.endswith(".raw.jsonl"):
        continue
    model = os.path.basename(p)[:-4].replace("__", ":", 1).replace("_", ".")
    agentic[model] = {r["test"]: (r["result"], r["detail"]) for r in read_tsv(p)}

def norm(name):
    """agentic filenames lose punctuation; match them back to eval model names."""
    return "".join(ch for ch in name.lower() if ch.isalnum())

ag_by_norm = {norm(k): v for k, v in agentic.items()}

def f(x, default="—"):
    return x if x not in (None, "", "?") else default

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

# ---------- throughput chart (single series, sorted, direct labels) ----------
bars = [(r["model"], num(r.get("tok_s_L"))) for r in rows if num(r.get("tok_s_L"))]
bars.sort(key=lambda t: t[1], reverse=True)
vmax = max([v for _, v in bars], default=1)

bar_rows = []
for name, v in bars:
    pct = v / vmax * 100
    bar_rows.append(f"""
    <div class="brow">
      <div class="blabel">{html.escape(name)}</div>
      <div class="btrack"><div class="bfill" style="width:{pct:.1f}%"></div></div>
      <div class="bval">{v:.1f}</div>
    </div>""")

# ---------- capability matrix ----------
GATES = [
    ("T1_single_tool", "single tool"),
    ("T2_tool_selection", "pick right tool"),
    ("T3_multiturn", "multi-turn"),
    ("T4_parallel_calls", "parallel calls"),
    ("T5_complex_schema", "nested schema"),
    ("T7_tool_at_long_ctx", "tools @ long ctx"),
]

# The needle gates are named for the *word count* of the filler document, not a
# token count, and the server's reported prompt size does not match either (see
# review2.md). So the recall column reports the deepest level that passed and
# the prompt size the server actually reported for it -- never a nominal figure.
NEEDLES = ["T6_needle_4k", "T6_needle_16k", "T6_needle_60k", "T6_needle_120k"]

def recall_cell(a):
    deepest = None
    for g in NEEDLES:
        got = a.get(g)
        if got and got[0] == "PASS":
            deepest = (g, got[1])
    if deepest is None:
        return '<td class="mut">—</td>' if not any(a.get(g) for g in NEEDLES) \
               else '<td class="ba">fail</td>'
    g, detail = deepest
    words = g.rsplit("_", 1)[1]
    tok = detail.replace("found_at_", "").replace("_prompt_tokens", "")
    label = f"{words}w" + (f" / {int(tok)/1000:.0f}k rep." if tok.isdigit() else "")
    return f'<td class="ok" title="{html.escape(detail)}">{label}</td>'

def cell(res):
    if res is None:
        return '<td class="mut">—</td>'
    r, d = res
    if r == "PASS":
        return f'<td class="ok" title="{html.escape(d)}">pass</td>'
    if r in ("PARTIAL", "FLAKY"):
        short = "flaky" if r == "FLAKY" else "partial"
        return f'<td class="wa" title="{html.escape(d)}">{short}</td>'
    return f'<td class="ba" title="{html.escape(d)}">{ "err" if r=="ERROR" else "fail"}</td>'

gate_head = "".join(f"<th>{n}</th>" for _, n in GATES) + "<th>deepest recall</th>"

matrix = []
for r in rows:
    a = ag_by_norm.get(norm(r["model"]), {})
    tds = "".join(cell(a.get(g)) for g, _ in GATES) + recall_cell(a)
    matrix.append(f'<tr><td class="mono">{html.escape(r["model"])}</td>{tds}</tr>')

# ---------- footprint table ----------
foot = []
for r in rows:
    split = r.get("split", "")
    sp = f'<span class="ba">split</span>' if split == "YES" else '<span class="ok">full</span>'
    foot.append(
        f'<tr><td class="mono">{html.escape(r["model"])}</td>'
        f'<td>{f(r.get("size_gb"))}</td><td>{f(r.get("vram_gb"))}</td><td>{sp}</td>'
        f'<td>{f(r.get("tok_s_S"))}</td><td>{f(r.get("tok_s_L"))}</td>'
        f'<td>{f(r.get("max_ctx_in_vram"))}</td>'
        f'<td>{f(r.get("think_default"))}</td></tr>'
    )

findings = os.environ.get("ONEPAGER_FINDINGS", "").strip()
verdict = os.environ.get("ONEPAGER_VERDICT", "").strip()

doc = f"""<!doctype html>
<meta charset="utf-8">
<title>Local model evaluation — agentic coding on 192.168.100.67</title>
<style>
  @page {{ size: A4; margin: 11mm 11mm 9mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:{SURFACE}; color:{INK};
         font:9.2px/1.42 "Helvetica Neue",Helvetica,Arial,sans-serif; }}
  h1 {{ font-size:16px; margin:0 0 1px; letter-spacing:-.2px; }}
  .sub {{ color:{INK2}; font-size:8.6px; margin-bottom:7px; }}
  h2 {{ font-size:9.6px; text-transform:uppercase; letter-spacing:.09em;
        color:{INK2}; margin:11px 0 4px; font-weight:600; }}
  table {{ border-collapse:collapse; width:100%; }}
  th,td {{ text-align:right; padding:2.6px 4px; border-bottom:.5px solid #e6e5e1; }}
  th:first-child,td:first-child {{ text-align:left; }}
  th {{ color:{INK3}; font-weight:600; font-size:8px; text-transform:uppercase;
        letter-spacing:.05em; border-bottom:.8px solid #d8d7d2; }}
  .mono {{ font-family:"SF Mono",Menlo,Consolas,monospace; font-size:8.4px; }}
  .ok {{ color:{GOOD}; font-weight:600; }}
  .wa {{ color:#8a6100; font-weight:600; }}
  .ba {{ color:{BAD}; font-weight:600; }}
  .mut {{ color:{INK3}; }}
  .verdict {{ border:.8px solid #d8d7d2; border-left:2.5px solid {SERIES};
              background:#f6f8fb; padding:6px 9px; margin:0 0 3px; }}
  .verdict b {{ font-size:10px; }}
  .cols {{ display:flex; gap:13px; }}
  .cols > div {{ flex:1; }}
  ul {{ margin:2px 0 0; padding-left:12px; }}
  li {{ margin-bottom:2.6px; }}
  .brow {{ display:flex; align-items:center; gap:6px; margin-bottom:2.6px; }}
  .blabel {{ width:36%; font-family:"SF Mono",Menlo,monospace; font-size:8.2px;
             color:{INK}; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .btrack {{ flex:1; height:9px; background:#eceae5; }}
  .bfill {{ height:9px; background:{SERIES};
            border-top-right-radius:3px; border-bottom-right-radius:3px; }}
  .bval {{ width:34px; text-align:right; font-weight:600; font-size:8.6px; }}
  .foot {{ margin-top:9px; color:{INK3}; font-size:7.5px; border-top:.5px solid #e6e5e1;
           padding-top:4px; }}
</style>

<h1>Local models for agentic coding — server 192.168.100.67</h1>
<div class="sub">36.1 GB usable VRAM (measured, two GPUs) · Ollama 0.32.5 ·
generated {datetime.date.today().isoformat()} · all figures measured on this host</div>

{f'<div class="verdict">{verdict}</div>' if verdict else ''}

<h2>Generation throughput — profile L, thinking disabled (tok/s)</h2>
{''.join(bar_rows) if bar_rows else '<div class="mut">no throughput data</div>'}

<h2>Footprint, speed and context ceiling</h2>
<table>
<tr><th>model</th><th>size GB</th><th>VRAM GB</th><th>placement</th>
    <th>tok/s S</th><th>tok/s L</th><th>max ctx in VRAM</th><th>thinks by default</th></tr>
{''.join(foot) if foot else '<tr><td colspan="8" class="mut">no data</td></tr>'}
</table>

<h2>Agentic capability gates</h2>
<table>
<tr><th>model</th>{gate_head}</tr>
{''.join(matrix) if matrix else '<tr><td colspan="8" class="mut">no data</td></tr>'}
</table>

<div class="cols">
<div>
<h2>What the gates mean</h2>
<ul>
<li><b>pick right tool</b> — four tools offered; must choose <span class="mono">search_code</span>, not the first one.</li>
<li><b>multi-turn</b> — must consume a <span class="mono">tool_result</span> it was handed and act on it rather than re-calling.</li>
<li><b>nested schema</b> — enums plus an array of objects, like a real patch tool.</li>
<li><b>tools @ long ctx</b> — tool call with ~53k tokens already in the window. Run 3×: this is where models silently stop emitting tool calls.</li>
<li><b>deepest recall</b> — a fact buried mid-document, retrieved. Shown as filler <i>words</i> and the prompt size the server reported. Proves the context is usable, not merely allocatable.</li>
</ul>
</div>
<div>
<h2>Findings</h2>
{findings if findings else '<ul><li>pending</li></ul>'}
</div>
</div>

<div class="foot">
Profile S = Sieve-of-Eratosthenes prompt capped at 300 tokens (comparable to the v0 history).
Profile L = "Write exactly 1000 tokens about GPUs", uncapped (comparable to the figures quoted by Alex).
The two are never averaged: longer generations amortise warm-up and report higher tok/s on identical hardware.
Context ceiling = largest num_ctx whose weights+KV still sit entirely in VRAM. Recall depth is stated in filler
words plus the server-reported prompt size; those two disagree with each other and with a chars/4 estimate, so
neither is presented as a verified token count. GPU temperature and utilisation are not shown because the Ollama
HTTP API does not expose them and SSH to the host is refused.
</div>
"""

out_html = os.path.join(HERE, "evaluation.html")
with open(out_html, "w") as fh:
    fh.write(doc)

out_pdf = os.path.join(HERE, "evaluation.pdf")
cmd = ["chromium", "--headless", "--disable-gpu", "--no-sandbox",
       "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}", f"file://{out_html}"]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
if not os.path.exists(out_pdf):
    print("chromium failed:", r.stderr[-800:], file=sys.stderr)
    sys.exit(1)
print(f"wrote {out_html}")
print(f"wrote {out_pdf} ({os.path.getsize(out_pdf)/1024:.0f} KB)")
