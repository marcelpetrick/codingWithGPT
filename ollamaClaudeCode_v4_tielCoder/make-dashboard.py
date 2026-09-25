#!/usr/bin/env python3
"""make-dashboard.py -- dashboard.html: which model for agentic coding, on the
three axes the owner asked for (2026-09-24): speed, correctness, quality.

Regenerated after every candidate; everything it shows is read from results/
and from the verdict line of ROUND_2026-09-24.md, so the page cannot drift
from the data or from the written verdict.

  speed        tokrate.tsv   generation tok/s (think off, temp 0)
               cc-session    ledger fixture, median session wall
  correctness  terminal-bench-official.tsv, thinking-parity arm only,
               complete passes only, defective tasks and infra failures out
  quality      cc-session    ledger fixture, held-out tests per run (x/18)
  candidates   candidates-2026-09-21.tsv (the screen)
"""
import csv
import html
import math
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
sys.path.insert(0, str(HERE / "terminalbench" / "official"))
from summarise import DEFECTIVE, INFRA, split_arm, wilson  # noqa: E402

ARM = "thinkon"
N_TASKS = 10


def slug(tag):
    return tag.replace(":", "_").replace("/", "_").lower()


def rows(name):
    p = RES / name
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


# ---------------------------------------------------------------- correctness
def terminal_bench():
    by_run = defaultdict(list)
    for r in rows("terminal-bench-official.tsv"):
        by_run[r["run_id"]].append(r)
    out = defaultdict(lambda: {"k": 0, "n": 0, "secs": []})
    for run_id, rs in by_run.items():
        model, arm = split_arm(run_id)
        if arm != ARM:
            continue
        m = re.search(r"-n(\d+)-", run_id)
        if not m or len(rs) < N_TASKS * int(m.group(1)):
            continue  # a partial pass is not a rate
        for r in rs:
            if r["task"] in DEFECTIVE or r["failure_mode"] in INFRA:
                continue
            o = out[model]
            o["n"] += 1
            o["k"] += r["resolved"] == "True"
            try:
                o["secs"].append(float(r["agent_sec"]))
            except ValueError:
                pass
    return out


# ------------------------------------------------------------ speed + quality
def ledger():
    out = defaultdict(lambda: {"walls": [], "hidden": []})
    for r in rows("cc-session.tsv"):
        if r["fixture"] != "hard" or r["thinking"] != "on":
            continue
        o = out[slug(r["model"])]
        try:
            o["walls"].append(float(r["wall_s"]))
        except ValueError:
            pass
        h = re.match(r"(\d+)/18", r.get("hidden", ""))
        if h:
            o["hidden"].append(int(h.group(1)))
    return out


def tokrate():
    out = defaultdict(list)
    for r in rows("tokrate.tsv"):
        try:
            out[slug(r["model"])].append(float(r["gen_tps"]))
        except ValueError:
            pass
    return {k: statistics.median(v) for k, v in out.items()}


def verdict_line():
    p = HERE / "ROUND_2026-09-24.md"
    if not p.exists():
        return "", ""
    s = p.read_text()
    m = re.search(r"## Verdict so far\s+\*\*(.+?)\*\*\s*\n\*\((.+?)\)\*", s, re.S)
    return (m.group(1), m.group(2)) if m else ("", "")


# ---------------------------------------------------------------- the field
FIELD = [  # tag, display name, note
    ("kat-coder-v2.5:q5km-ctx256k-agentic", "KAT-Coder-V2.5-Dev (the pick)", "18/18 at the fastest session; the default since 2026-09-25"),
    ("tiel-coder:35b-q5-ctx256k-agentic", "Tiel-Coder 35B-A3B", "the pick when overflow safety matters: it refuses, not truncates"),
    ("qwen3.6:35b-a3b-q4_K_M-agentic", "Qwen3.6 35B-A3B", "the incumbent; ran greedy (temp 0)"),
    ("qwen3.6:35b-a3b-q4_K_M-agentic-t06", "Qwen3.6 35B-A3B at vendor sampling", "t 0.6 / top_p 0.95 / top_k 20: the greedy-vs-spec control"),
    ("gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic", "Gemma4 26B-A4B", "vision; smallest footprint"),
    ("north-mini-code-1.0:q4_K_M-ctx256k-agentic", "North-Mini-Code 1.0", "fastest generation"),
]


# Column explanations for the (i) tooltips -- up to five sentences each, written
# for a reader who has not seen the round document.
TIPS = {
    "model": "The model and its Ollama tag, as run on the .67 server (Ollama 0.33.3, one model resident at a time). "
             "The grey line says what the model is kept for. Screened-in candidates from this round appear as '(candidate)'.",
    "tps": "Generation speed in tokens per second, at a 2,000-word prompt, thinking off, temperature 0, median of three runs, "
           "with the server idle. Higher is better. It measures raw decoding only: a model can generate fast and still finish "
           "a coding session slowly, if it needs many turns.",
    "session": "Median wall-clock time of the 'ledger' coding session, three runs, thinking on, driven through the real Claude Code CLI. "
               "The model has to read the repository, fix three bugs across three modules, implement one missing function and get the "
               "tests green. Lower is better. This is the number you actually wait for, since it includes every turn and tool call.",
    "tb": "Terminal-Bench (upstream harness, dataset terminal-bench-core 0.1.1): real terminal tasks in Docker containers, graded by "
          "the tasks' own tests. A frozen subset of 10 tasks, run 3 times each; 9 are scored because nginx-request-logging cannot "
          "be passed as written. Thinking is on for every model, only complete passes count, and infrastructure failures are void, "
          "not zero. The small line shows solved/trials and the 95% interval.",
    "ci": "The 95% Wilson confidence interval of the Terminal-Bench rate, drawn on a 0-100% axis: the band is the interval, the dot "
          "the measured rate. With only 27 trials per model the band is about 35 points wide. Two models whose bands overlap are "
          "NOT ranked by this benchmark -- that rule was fixed before any results. Today every band overlaps.",
    "hidden": "Held-out tests, one chip per run: after the ledger session ends, 18 extra tests the model never saw are run "
              "against its code. They check what the docstrings specify, not what the visible tests happen to assert. 18/18 "
              "means the model implemented the specification; fewer means it made the visible tests green and left parts of "
              "the spec undone. Green is 18/18, amber anything less.",
    "cand": "A candidate model found this round and pre-evaluated on the web before it was pulled; the grey line is the exact "
            "GGUF source. Models ruled out on the evidence never appear here -- they are listed with reasons in CANDIDATE_REGISTER.md.",
    "verdict": "The screen's result. SCREENED-IN: passed all three gates and went on to Terminal-Bench. CUT-G1: did not fit "
               "fully in GPU memory; CUT-G2 failed the tool-call gates; CUT-G3 had a coding session too slow or too many "
               "held-out failures. VOID means our harness failed, not the model.",
    "gib": "Size of the downloaded model in GiB, including the vision projector where the repository ships one. It is checked "
           "to within 3% of the expected file, because a Hugging Face quant label can resolve to a different file (a wrong, "
           "smaller quant would silently lower quality).",
    "vram": "GPU memory the model occupies once loaded with its full 262,144-token context window. It must be 100% on the "
            "GPU: a spill into system RAM cost 5x the speed in earlier rounds. The box keeps about 35.56 GB resident.",
    "gates": "Ten tool-call gates, passed out of ten; 9 are required. They test: one correct tool call, choosing the right tool, "
             "using a tool's result, two parallel calls, a nested schema (an 'edits' array -- what Claude Code's edit tools "
             "send), finding a hidden fact at 4k/16k/60k/120k tokens of context, and calling tools correctly at ~53k tokens.",
    "gtps": "Generation tokens per second recorded during the screen. Reported, never a gate.",
    "ledger": "Median wall-clock of the three ledger coding sessions (see the field table). Gate G3 requires 150 s or less, "
              "because a model that needs many slow turns is the wrong shape even if it is capable.",
    "chidden": "Median held-out tests passed out of 18 across the three ledger sessions (see the field table). Gate G3 requires "
               "at least 16.",
    "note": "The model's reported capabilities (tools, thinking, vision), or the reason it was cut.",
}


def th(label, key):
    """A sortable header with an (i) tooltip."""
    return (f'<th>{label}<span class="info" tabindex="0" role="button" '
            f'aria-label="About this column" data-tip="{html.escape(TIPS[key], quote=True)}">i</span></th>')


def main():
    tb, led, tps = terminal_bench(), ledger(), tokrate()
    cands = [r for r in rows("candidates-2026-09-21.tsv")]
    field = [(t, n, note) for t, n, note in FIELD]
    for c in cands:  # a screened-in candidate joins the field table
        if c.get("verdict") == "SCREENED-IN" and c["baked_tag"] not in {t for t, _, _ in FIELD}:
            field.append((c["baked_tag"], c["name"] + " (candidate)", "screened in " + c["date"]))

    table = []
    for tag, name, note in field:
        s = slug(tag)
        t = tb.get(s, {"k": 0, "n": 0, "secs": []})
        lo, hi = wilson(t["k"], t["n"]) if t["n"] else (0, 0)
        L = led.get(s, {"walls": [], "hidden": []})
        table.append({
            "name": name, "note": note,
            "rate": 100 * t["k"] / t["n"] if t["n"] else None, "k": t["k"], "n": t["n"],
            "lo": lo, "hi": hi,
            "tb_med": statistics.median(t["secs"]) if t["secs"] else None,
            "wall": statistics.median(L["walls"]) if L["walls"] else None,
            "hidden": L["hidden"],
            "tps": tps.get(s),
        })

    vline, vwhen = verdict_line()
    E = html.escape

    def num(v, fmt):
        return fmt.format(v) if v is not None else "&mdash;"

    # correctness chart: rate with its 95% interval on a 0-100 axis
    def ci_bar(r):
        if r["rate"] is None:
            return '<span class="muted">not run</span>'
        return (f'<div class="ci"><div class="ci-range" style="left:{r["lo"]:.1f}%;width:{r["hi"]-r["lo"]:.1f}%"></div>'
                f'<div class="ci-dot" style="left:{r["rate"]:.1f}%"></div></div>')

    def hidden_chips(h):
        if not h:
            return '<span class="muted">&mdash;</span>'
        return " ".join(f'<span class="chip {"good" if x == 18 else "warn"}">{x}/18</span>' for x in h)

    trs = []
    for r in table:
        def dv(v):  # sort key for a cell; missing values sort last either way
            return "" if v is None else f"{v:.3f}"
        hid = statistics.mean(r["hidden"]) if r["hidden"] else None
        trs.append(
            f"<tr><td data-v='{E(r['name'])}'><b>{E(r['name'])}</b><div class='muted small'>{E(r['note'])}</div></td>"
            f"<td class='num' data-v='{dv(r['tps'])}'>{num(r['tps'], '{:.0f}')}</td>"
            f"<td class='num' data-v='{dv(r['wall'])}'>{num(r['wall'], '{:.0f} s')}</td>"
            f"<td class='num' data-v='{dv(r['rate'])}'>{num(r['rate'], '{:.0f}%')}<div class='muted small'>{r['k']}/{r['n']}"
            f"{'' if r['rate'] is None else f' &middot; [{r['lo']:.0f}, {r['hi']:.0f}]'}</div></td>"
            f"<td class='cicell' data-v='{dv(r['lo'] if r['rate'] is not None else None)}'>{ci_bar(r)}</td>"
            f"<td data-v='{dv(hid)}'>{hidden_chips(r['hidden'])}</td></tr>")

    crs = []
    for c in cands:
        v = c.get("verdict", "")
        tone = "good" if v == "SCREENED-IN" else "crit"
        def cv(k):
            x = (c.get(k) or "").split("/")[0]
            try:
                return f"{float(x):.3f}"
            except ValueError:
                return ""
        crs.append(
            f"<tr><td data-v='{E(c['name'])}'><b>{E(c['name'])}</b><div class='muted small'>{E(c['source'])}</div></td>"
            f"<td data-v='{E(v)}'><span class='chip {tone}'>{E(v)}</span></td>"
            f"<td class='num' data-v='{cv('got_gib')}'>{E(c.get('got_gib') or '-')}</td>"
            f"<td class='num' data-v='{cv('vram_gb')}'>{E(c.get('vram_gb') or '-')}</td>"
            f"<td data-v='{cv('gates')}'>{E(c.get('gates') or '-')}</td>"
            f"<td class='num' data-v='{cv('gen_toks')}'>{E(c.get('gen_toks') or '-')}</td>"
            f"<td class='num' data-v='{cv('ledger_median_s')}'>{E(c.get('ledger_median_s') or '-')}</td>"
            f"<td data-v='{cv('ledger_hidden')}'>{E(c.get('ledger_hidden') or '-')}</td>"
            f"<td class='small' data-v='{E(c.get('note') or '')}'>{E(c.get('note') or '')}</td></tr>")
    queue = ["occamy", "kat-coder", "ornith15-35b", "byteshape"]
    done = {c["name"] for c in cands}
    pending = [q for q in queue if q not in done]

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agentic Model Dashboard</title>
<style>
:root{{--paper:#F6F7F9;--panel:#FFF;--ink:#131822;--muted:#5C6675;--rule:#DCE1E8;
--good:#0F8A6B;--good-soft:#E2F1EC;--warn:#A57C0C;--warn-soft:#F5EEDC;--crit:#C6304F;--crit-soft:#FAE4E9;
--ref:#3D5FC4;--ref-soft:#E5EAFA}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--paper:#0E1218;--panel:#161B24;--ink:#E9EDF3;
--muted:#8F99A8;--rule:#28303C;--good:#3FC79F;--good-soft:#123229;--warn:#E0B544;--warn-soft:#2E2812;
--crit:#F06A86;--crit-soft:#361820;--ref:#7F9BF0;--ref-soft:#1B2340}}}}
:root[data-theme="dark"]{{--paper:#0E1218;--panel:#161B24;--ink:#E9EDF3;--muted:#8F99A8;--rule:#28303C;
--good:#3FC79F;--good-soft:#123229;--warn:#E0B544;--warn-soft:#2E2812;--crit:#F06A86;--crit-soft:#361820;
--ref:#7F9BF0;--ref-soft:#1B2340}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:16px;margin:28px 0 8px}}
.muted{{color:var(--muted)}} .small{{font-size:12px}}
.verdict{{background:var(--good-soft);border-left:4px solid var(--good);padding:14px 16px;border-radius:8px;margin:16px 0}}
.verdict b{{font-size:17px}}
.panel{{background:var(--panel);border:1px solid var(--rule);border-radius:10px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:720px}}
th,td{{padding:9px 12px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top}}
th{{font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.03em}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.chip{{display:inline-block;padding:1px 7px;border-radius:99px;font-size:12px;font-weight:600;margin:1px 0}}
.chip.good{{background:var(--good-soft);color:var(--good)}} .chip.warn{{background:var(--warn-soft);color:var(--warn)}}
.chip.crit{{background:var(--crit-soft);color:var(--crit)}}
.cicell{{min-width:160px}}
.ci{{position:relative;height:14px;margin-top:5px;border-radius:7px;background:var(--rule)}}
.ci-range{{position:absolute;top:0;bottom:0;background:var(--ref-soft);border:1px solid var(--ref);border-radius:7px}}
.ci-dot{{position:absolute;top:1px;width:10px;height:10px;margin-left:-5px;border-radius:50%;background:var(--ref)}}
ul{{margin:6px 0;padding-left:20px}}
.info{{display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;margin-left:5px;border-radius:50%;
border:1px solid var(--muted);font:600 10px/1 Georgia,serif;font-style:italic;text-transform:none;letter-spacing:0;
color:var(--muted);cursor:help;vertical-align:1px}}
.info:hover,.info:focus{{color:var(--ref);border-color:var(--ref);outline:none}}
#tip{{position:fixed;z-index:10;max-width:340px;padding:10px 12px;border-radius:8px;background:var(--ink);color:var(--paper);
font-size:13px;line-height:1.45;font-weight:400;text-transform:none;letter-spacing:0;box-shadow:0 6px 20px rgba(0,0,0,.25);
pointer-events:none;display:none}}
th.sortable{{cursor:pointer;user-select:none}} th.sortable:hover{{color:var(--ink)}}
th.sortable::after{{content:" \\2195";opacity:.35}} th[aria-sort=ascending]::after{{content:" \\2191";opacity:1}}
th[aria-sort=descending]::after{{content:" \\2193";opacity:1}}
</style></head><body><main>
<h1>Which model for agentic coding</h1>
<div class="muted small">Ollama 0.33.3 on .67 &middot; Claude Code &middot; generated {datetime.now():%Y-%m-%d %H:%M} from results/ &middot; round document: ROUND_2026-09-24.md</div>

<div class="verdict"><b>{E(vline) or "verdict pending"}</b><div class="muted small">{E(vwhen)}</div></div>

<h2>The field on three axes</h2>
<div class="panel"><table>
<tr>{th("model","model")}{th("speed<br>tok/s","tps")}{th("speed<br>session","session")}{th("correctness<br>Terminal-Bench","tb")}
{th("95% interval (0&ndash;100%)","ci")}{th("quality<br>held-out tests per run","hidden")}</tr>
{''.join(trs)}
</table></div>
<ul class="small muted">
<li><b>speed</b>: generation tok/s (think off, temp 0), and median wall time of the ledger coding session (thinking on). Lower session time is better.</li>
<li><b>correctness</b>: Terminal-Bench, 9 scored tasks (<i>nginx-request-logging</i> is defective and excluded), thinking on for every model, complete passes only. <b>Overlapping intervals are not a ranking.</b></li>
<li><b>quality</b>: 18 held-out tests the model never sees. 18/18 means it implemented the spec, not just the visible tests.</li>
</ul>

<h2>Candidates: screened one at a time, best first</h2>
<div class="panel"><table>
<tr>{th("candidate","cand")}{th("verdict","verdict")}{th("GiB","gib")}{th("VRAM GB","vram")}{th("gates","gates")}{th("tok/s","gtps")}{th("ledger s","ledger")}{th("hidden","chidden")}{th("note","note")}</tr>
{''.join(crs) or '<tr><td colspan="9" class="muted">none finished yet</td></tr>'}
</table></div>
<p class="small muted">Still queued: {E(', '.join(pending)) or 'none'}. Ruled out on web evidence and never pulled: Ornith-27B-Coder, Qwen3.6-27B-A3B-Coder, KAT-Ornith, SignOfFour, both OmniMerges, glm-4.7-flash, qwen3-coder:30b, Laguna XS 2.1 (reasons in CANDIDATE_REGISTER.md).</p>
<p class="small muted">Click a column header to sort; click again to reverse. Empty cells always sort last.</p>
</main>
<div id="tip" role="tooltip"></div>
<script>
(function () {{
  var tip = document.getElementById("tip"), open = null;
  function show(el) {{
    tip.textContent = el.getAttribute("data-tip"); tip.style.display = "block"; open = el;
    var r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    var y = r.bottom + 8; if (y + h > window.innerHeight - 8) y = r.top - h - 8;
    tip.style.left = x + "px"; tip.style.top = Math.max(8, y) + "px";
  }}
  function hide() {{ tip.style.display = "none"; open = null; }}
  document.querySelectorAll(".info").forEach(function (el) {{
    el.addEventListener("mouseenter", function () {{ show(el); }});
    el.addEventListener("mouseleave", hide);
    el.addEventListener("focus", function () {{ show(el); }});
    el.addEventListener("blur", hide);
    el.addEventListener("click", function (e) {{ e.stopPropagation(); open === el ? hide() : show(el); }});
    el.addEventListener("keydown", function (e) {{ if (e.key === "Escape") {{ hide(); el.blur(); }} }});
  }});
  window.addEventListener("scroll", hide, true);
}})();
document.querySelectorAll("table").forEach(function (tbl) {{
  var head = tbl.rows[0];
  Array.prototype.forEach.call(head.cells, function (th, col) {{
    th.classList.add("sortable");
    th.addEventListener("click", function () {{
      var asc = th.getAttribute("aria-sort") !== "ascending";
      Array.prototype.forEach.call(head.cells, function (h) {{ h.removeAttribute("aria-sort"); }});
      th.setAttribute("aria-sort", asc ? "ascending" : "descending");
      var rows = Array.prototype.slice.call(tbl.rows, 1).filter(function (r) {{ return r.cells.length > 1; }});
      rows.sort(function (a, b) {{
        var x = a.cells[col] ? a.cells[col].getAttribute("data-v") || "" : "";
        var y = b.cells[col] ? b.cells[col].getAttribute("data-v") || "" : "";
        if (x === "" && y === "") return 0;
        if (x === "") return 1;
        if (y === "") return -1;
        var nx = parseFloat(x), ny = parseFloat(y);
        var d = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
        return asc ? d : -d;
      }});
      var parent = tbl.rows[1] ? tbl.rows[1].parentNode : tbl;
      rows.forEach(function (r) {{ parent.appendChild(r); }});
    }});
  }});
}});
</script>
</body></html>
"""
    out = HERE / "dashboard.html"
    out.write_text(page)
    print(f"wrote {out} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
