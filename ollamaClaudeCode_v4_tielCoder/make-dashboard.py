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
    ("tiel-coder:35b-q5-ctx256k-agentic", "Tiel-Coder 35B-A3B", "context overflow is a visible error"),
    ("qwen3.6:35b-a3b-q4_K_M-agentic", "Qwen3.6 35B-A3B", "the incumbent; ran greedy (temp 0)"),
    ("gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic", "Gemma4 26B-A4B", "vision; smallest footprint"),
    ("north-mini-code-1.0:q4_K_M-ctx256k-agentic", "North-Mini-Code 1.0", "fastest generation"),
]


def main():
    tb, led, tps = terminal_bench(), ledger(), tokrate()
    cands = [r for r in rows("candidates-2026-09-21.tsv")]
    field = [(t, n, note) for t, n, note in FIELD]
    for c in cands:  # a screened-in candidate joins the field table
        if c.get("verdict") == "SCREENED-IN":
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
        trs.append(
            f"<tr><td><b>{E(r['name'])}</b><div class='muted small'>{E(r['note'])}</div></td>"
            f"<td class='num'>{num(r['tps'], '{:.0f}')}</td>"
            f"<td class='num'>{num(r['wall'], '{:.0f} s')}</td>"
            f"<td class='num'>{num(r['rate'], '{:.0f}%')}<div class='muted small'>{r['k']}/{r['n']}"
            f"{'' if r['rate'] is None else f' &middot; [{r['lo']:.0f}, {r['hi']:.0f}]'}</div></td>"
            f"<td class='cicell'>{ci_bar(r)}</td>"
            f"<td>{hidden_chips(r['hidden'])}</td></tr>")

    crs = []
    for c in cands:
        v = c.get("verdict", "")
        tone = "good" if v == "SCREENED-IN" else "crit"
        crs.append(
            f"<tr><td><b>{E(c['name'])}</b><div class='muted small'>{E(c['source'])}</div></td>"
            f"<td><span class='chip {tone}'>{E(v)}</span></td>"
            f"<td class='num'>{E(c.get('got_gib') or '-')}</td><td class='num'>{E(c.get('vram_gb') or '-')}</td>"
            f"<td>{E(c.get('gates') or '-')}</td><td class='num'>{E(c.get('gen_toks') or '-')}</td>"
            f"<td class='num'>{E(c.get('ledger_median_s') or '-')}</td><td>{E(c.get('ledger_hidden') or '-')}</td>"
            f"<td class='small'>{E(c.get('note') or '')}</td></tr>")
    queue = ["occamy", "kat-coder", "byteshape", "laguna-xs21"]
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
</style></head><body><main>
<h1>Which model for agentic coding</h1>
<div class="muted small">Ollama 0.33.3 on .67 &middot; Claude Code &middot; generated {datetime.now():%Y-%m-%d %H:%M} from results/ &middot; round document: ROUND_2026-09-24.md</div>

<div class="verdict"><b>{E(vline) or "verdict pending"}</b><div class="muted small">{E(vwhen)}</div></div>

<h2>The field on three axes</h2>
<div class="panel"><table>
<tr><th>model</th><th>speed<br>tok/s</th><th>speed<br>session</th><th>correctness<br>Terminal-Bench</th>
<th>95% interval (0&ndash;100%)</th><th>quality<br>held-out tests per run</th></tr>
{''.join(trs)}
</table></div>
<ul class="small muted">
<li><b>speed</b>: generation tok/s (think off, temp 0), and median wall time of the ledger coding session (thinking on). Lower session time is better.</li>
<li><b>correctness</b>: Terminal-Bench, 9 scored tasks (<i>nginx-request-logging</i> is defective and excluded), thinking on for every model, complete passes only. <b>Overlapping intervals are not a ranking.</b></li>
<li><b>quality</b>: 18 held-out tests the model never sees. 18/18 means it implemented the spec, not just the visible tests.</li>
</ul>

<h2>Candidates: screened one at a time, best first</h2>
<div class="panel"><table>
<tr><th>candidate</th><th>verdict</th><th>GiB</th><th>VRAM GB</th><th>gates</th><th>tok/s</th><th>ledger s</th><th>hidden</th><th>note</th></tr>
{''.join(crs) or '<tr><td colspan="9" class="muted">none finished yet</td></tr>'}
</table></div>
<p class="small muted">Still queued: {E(', '.join(pending)) or 'none'}. Ruled out on web evidence and never pulled: Ornith-27B-Coder, Qwen3.6-27B-A3B-Coder, KAT-Ornith, SignOfFour, both OmniMerges, glm-4.7-flash, qwen3-coder:30b (reasons in the round document).</p>
</main></body></html>
"""
    out = HERE / "dashboard.html"
    out.write_text(page)
    print(f"wrote {out} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
