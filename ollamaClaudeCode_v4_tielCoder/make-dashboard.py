#!/usr/bin/env python3
"""make-dashboard.py -- dashboard.html: the final results of the 09-24 round, one row
per model, and two picks computed from them by rules printed on the page.

Everything shown is read from results/ (and the verdict line of ROUND_2026-09-24.md),
so the page cannot drift from the data. Regenerate after every result.

  Terminal-Bench   terminalbench/official/results -> results/terminal-bench-official.tsv,
                   thinking-parity arm, complete passes, defective tasks and VOID trials out
  held-out, session cc-session-rb0925.tsv (same Claude Code version, x5) where a model has
                   it, else cc-session.tsv (its screen runs)
  T5 x8            gate-rerun.tsv          tok/s  tokrate.tsv (2k-word prompt)
  VRAM             candidates-2026-09-21.tsv, else vision-v2.tsv (resident GB at 262k)
  extended         the thinkon-ext arm, paired as ext-compare.py EXT_INFO=1 does
"""
import csv
import html
import re
import statistics
from math import comb
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
sys.path.insert(0, str(HERE / "terminalbench" / "official"))
from summarise import DEFECTIVE, INFRA, split_arm, wilson  # noqa: E402

ARM = "thinkon"
GATE_RERUN_HISTORY = 2   # gate-rerun.tsv's first lines are the 09-17 re-runs, not this round

# The rows of the page: tag -> display name. Screened-in candidates join from the screen TSV.
MODELS = [
    ("qwen3.6:35b-a3b-q4_K_M-agentic", "Qwen3.6 35B-A3B"),
    ("kat-coder-v2.5:q5km-ctx256k-agentic", "KAT-Coder-V2.5-Dev"),
    ("byteshape-qwen3.6-35b:q4ks-ctx256k-agentic", "ByteShape Qwen3.6 Q4_K_S"),
    ("gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic", "Gemma4 26B-A4B"),
    ("tiel-coder:35b-q5-ctx256k-agentic", "Tiel-Coder 35B-A3B"),
    ("laguna-xs-2.1:q4km-ctx256k-agentic", "Laguna XS 2.1"),
    ("occamy-1.0:q5km-ctx256k-agentic", "occamy-1.0"),
    ("ornith-1.5-35b:q5km-ctx256k-agentic", "Ornith-1.5-35B-A3B"),
    ("north-mini-code-1.0:q4_K_M-ctx256k-agentic", "North-Mini-Code 1.0"),
    ("qwen3.6:35b-a3b-q4_K_M-agentic-t06", "Qwen3.6 at vendor sampler (t 0.6)"),
]

# The picks' rules, fixed in the round (09-25) and printed on the page.
QUALITY = "held-out median 18/18 and no run below 16"
T5_MIN = 7


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
        # A partial pass is not a rate, but summarise.py already keeps only complete
        # passes in the TSV (counting VOID trials). Re-checking row counts here broke on
        # a repair (10-08): it removes the replaced VOID rows from the main pass.
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


def ledger_same_client():
    """The 09-25 same-version re-baseline (one Claude Code version, x5). Where a model
    has these runs, they replace its older runs, which were on mixed client versions."""
    out = defaultdict(lambda: {"walls": [], "hidden": []})
    for r in rows("cc-session-rb0925.tsv"):
        if r.get("fixture") != "hard" or r.get("thinking") != "on":
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
        if r.get("prompt_words") != "2000":   # one row per prompt size; the tooltip promises 2k
            continue
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
    # since 10-08 the section opens with "### Final pick (<when>): <bold verdict>";
    # before that, a bold verdict and its dated italic note
    m = re.search(r"## Verdict so far\s+### Final pick \(([^)]+)\): (.+)", s)
    if m:
        return m.group(2).replace("**", "").strip(), m.group(1)
    m = re.search(r"## Verdict so far\s+\*\*(.+?)\*\*\s*\*\((.+?)\)\*", s, re.S)
    return (m.group(1), m.group(2)) if m else ("", "")


TIPS = {
    "model": "The model, as run on .67 (Ollama 0.33.3 until 10-05, 0.35.1 since), one model resident at a time, 100% on the GPU. "
             "The (i) next to a name has its facts: maker, base, quant, size, sampler.",
    "tb": "Correctness. Terminal-Bench (terminal-bench-core 0.1.1): real terminal tasks in Docker, graded by the tasks' own tests. "
          "8 scored tasks x 3 attempts, thinking on for every model; VOID infrastructure failures are not counted. "
          "Bar = 95% interval on 0-100%. Overlapping bars are a tie, not a ranking.",
    "hidden": "Few mistakes. After a real Claude Code coding session (fix three bugs, implement one function), 18 tests the model never saw are run. "
              "Shown: median and worst run. The rule: median 18/18 and no run below 16.",
    "t5": "Tool-call reliability. Gate T5 run 8 times: fill a nested schema exactly, the shape Claude Code's edit tools send. "
          "At least 7/8 is required; less means broken edits in real sessions.",
    "session": "Speed you wait for. Median wall-clock of that coding session through the real Claude Code CLI, thinking on. "
               "Five runs on one Claude Code version where a model has them (09-25), else its three screen runs. Lower is better.",
    "tps": "Raw generation speed, tokens per second at a 2,000-word prompt, thinking off. Higher is better; a fast decoder can still need many turns.",
    "vram": "GPU memory with the full 262,144-token context loaded. The box has ~35.5 GB usable.",
}

# Model fact cards for the (i) next to each model name. Sources: the model cards and
# registry manifests checked in ROUND_2026-09-24.md / CANDIDATE_REGISTER.md, and this
# box's own measurements (resident GB at the baked 262,144 window, from /api/ps).
MODEL_FACTS = {
    "kat-coder-v2.5:q5km-ctx256k-agentic": (
        "KAT-Coder-V2.5-Dev -- Kwaipilot (Kuaishou). Fine-tune of Qwen3.6-35B-A3B: 127k SFT examples, then RL, "
        "trained with Claude Code as the harness. MoE: 35B total, ~3B active per token. Quant Q5_K_M (bartowski), "
        "23.3 GiB; 32.48 GB resident here at 262k, 100% GPU. Native context 262,144. Released July 2026, "
        "Apache-2.0, text only (vision tower removed). Vendor sampler t 1.0 / top_p 0.95."),
    "tiel-coder:35b-q5-ctx256k-agentic": (
        "Tiel-Coder-35B-A3B -- peculiar-ragdoll. Coder fine-tune on the Qwen3.6-35B-A3B architecture, 'Sharp' chat "
        "template (v22.5.0 since the 2026-09-10 re-upload). MoE: 35B total, ~3B active. Quant UD-Q5_K_XL, 24.77 GiB "
        "+ 0.84 GiB vision projector; 34.13 GB resident at 262k, the tightest fit on the box. Native context 262,144, "
        "recall verified to 254,181 tokens, and it refuses (HTTP 400) rather than truncating past its window. Vision: 42/42."),
    "qwen3.6:35b-a3b-q4_K_M-agentic": (
        "Qwen3.6-35B-A3B -- Alibaba Qwen, official. MoE: 35B total, ~3B active. Quant Q4_K_M (Ollama library), "
        "22.29 GiB; 32.68 GB resident at 262k. Native context 262,144 (extensible to ~1M per the card). Released "
        "April 2026, Apache-2.0, with vision. Run here GREEDY (temperature 0) as the long-running control; "
        "silently halves an over-long prompt."),
    "qwen3.6:35b-a3b-q4_K_M-agentic-t06": (
        "The same Qwen3.6-35B-A3B Q4_K_M weights as the control, baked at Qwen's own recommended sampler for "
        "thinking-mode coding: temperature 0.6, top_p 0.95, top_k 20, min_p 0. Exists only to separate the sampler "
        "effect from the model (09-21 defect 4: the control had run greedy for four rounds)."),
    "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic": (
        "Gemma4-26B-A4B-it -- Google, official. MoE: 26B total, ~4B active. Quant Q4_K_M; 22.34 GB resident at "
        "262k, the smallest footprint in the field, and the fastest prefill measured here. Has vision. Known Ollama "
        "handicaps: its renderer drops tool parameters named 'description' (PR #18503), and its tool calling "
        "degrades under a quantized KV cache."),
    "north-mini-code-1.0:q4_K_M-ctx256k-agentic": (
        "North-Mini-Code-1.0 -- Cohere. MoE: 30B total, ~3B active. Quant Q4_K_M; ~21.3 GB resident at 262k. "
        "Native context 256k. Released June 2026, Apache-2.0. The fastest generation on the box (136 tok/s) but "
        "slow sessions; no vision at all; silently halves an over-long prompt."),
    "occamy-1.0:q5km-ctx256k-agentic": (
        "occamy-1.0 -- Accio-Lab (reported as Alibaba-linked). Qwen3.6-35B-A3B further trained for long-horizon "
        "agentic work: SFT on ~15k trajectories, then RL, an expert merge and a final RL stage. MoE: 35B total, "
        "~3B active. Official GGUF Q5_K_M, 23.03 GiB + 0.84 GiB projector; 32.45 GB resident at 262k. Native "
        "context 262,144. Released mid-September 2026, Apache-2.0. Community reports: reasoning loops."),
    "ornith-1.5-35b:q5km-ctx256k-agentic": (
        "Ornith-1.5-35B-A3B -- ornith-ai. MoE: 35B total, ~3B active, on Qwen3.5/Gemma4 foundations with continued "
        "pretraining and RL. Official GGUF Q5_K_M, 23.61 GiB + 0.84 GiB projector; 32.45 GB resident at 262k. "
        "Native context 256k. Released 2026-08-18, MIT. 3.9M GGUF downloads; its repo tab reports broken tool "
        "calls and looping, and T5 failed here."),
    "byteshape-qwen3.6-35b:q4ks-ctx256k-agentic": (
        "ByteShape Qwen3.6-35B-A3B -- the SAME Qwen3.6 weights, re-quantized by ByteShape's ShapeLearn (a learned "
        "data type per tensor). Q4_K_S at 4.22 bits per weight: 17.02 GiB + 0.84 GiB projector; 28.53 GB resident "
        "at 262k, ~4 GB less than the Q4_K_M. Native context 262,144. Quant published May 2026, Apache-2.0. Run at "
        "Qwen's vendor sampler (t 0.6)."),
    "laguna-xs-2.1:q4km-ctx256k-agentic": (
        "Laguna XS 2.1 -- Poolside. MoE, 33.4B total. Ollama library Q4_K_M, 18.88 GiB; 25.14 GB resident at "
        "262k, 100% GPU, ~7 GB below qwen3.6/KAT. Run with Ollama's stock poolside-v1 renderer and the Modelfile "
        "sampler (t 1.0, top_p 1, top_k 20). Screened in 10-08 on Ollama 0.35.1; community reports say the stock "
        "template can skip thinking."),
}

def minfo(key):
    """(i) with the model's fact card."""
    f = MODEL_FACTS.get(key)
    if not f:
        return ""
    return (f'<span class="info" tabindex="0" role="button" aria-label="About this model" '
            f'data-tip="{html.escape(f, quote=True)}">i</span>')


def th(label, key):
    """A sortable header with an (i) tooltip."""
    return (f'<th>{label}<span class="info" tabindex="0" role="button" '
            f'aria-label="About this column" data-tip="{html.escape(TIPS[key], quote=True)}">i</span></th>')


def t5():
    out = {}
    f = RES / "gate-rerun.tsv"
    if f.exists():
        for line in f.read_text().splitlines()[GATE_RERUN_HISTORY:]:
            c = line.split("\t")
            if len(c) >= 4 and c[1] == "T5":
                out[c[0]] = c[2]
    return out


def vram():
    out = {}
    for r in rows("vision-v2.tsv"):
        if r.get("ctx") == "262144" and r.get("resident_gb"):
            out[r["model"]] = float(r["resident_gb"])
    for r in rows("candidates-2026-09-21.tsv"):
        if r.get("resident_gb"):
            out[r["baked_tag"]] = float(r["resident_gb"])
    return out


def extended():
    """The thinkon-ext pair, counted as ext-compare.py EXT_INFO=1 does: a task VOID for
    either model is dropped for both, and only tasks both ran are counted."""
    per = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    void = set()
    for r in rows("terminal-bench-official.tsv"):
        if r.get("arm") != "thinkon-ext" or r["task"] in DEFECTIVE:
            continue
        if r["failure_mode"] in INFRA:
            void.add(r["task"])
            continue
        per[r["model"]][r["task"]][1] += 1
        per[r["model"]][r["task"]][0] += r["resolved"] == "True"
    if len(per) != 2:
        return None
    common = set.intersection(*(set(t) for t in per.values())) - void
    a, b = per
    wa = sum(per[a][t][0] > per[b][t][0] for t in common)
    wb = sum(per[b][t][0] > per[a][t][0] for t in common)
    n = wa + wb   # two-sided exact sign test over the decided tasks
    p = min(1.0, 2 * sum(comb(n, i) for i in range(min(wa, wb) + 1)) / 2 ** n) if n else 1.0
    tot = {m: [sum(per[m][t][0] for t in common), sum(per[m][t][1] for t in common)] for m in per}
    # qwen3.6's pass ran wholly on 0.33.3 and KAT's (10-08) wholly on 0.35.1: two runtimes even
    # though neither run changed mid-pass, so the pair is information only (round, 10-07)
    return {"tasks": len(common), "tot": tot, "p": p, "mixed": True}


def main():
    E = html.escape
    tb, led, tps, gates, mem = terminal_bench(), ledger(), tokrate(), t5(), vram()
    led.update({k: v for k, v in ledger_same_client().items() if v["walls"]})

    table = []
    for tag, name in MODELS:
        s = slug(tag)
        t = tb.get(s)
        if not t or not t["n"]:
            continue   # only models with a complete final Terminal-Bench pass
        L = led.get(s, {"walls": [], "hidden": []})
        h = L["hidden"]
        lo, hi = wilson(t["k"], t["n"])
        g = gates.get(tag)
        g_ok = bool(g) and int(g.split("/")[0]) >= T5_MIN
        q_ok = bool(h) and statistics.median(h) == 18 and min(h) >= 16
        table.append({"tag": tag, "name": name, "k": t["k"], "n": t["n"], "rate": 100 * t["k"] / t["n"],
                      "lo": lo, "hi": hi, "h": h, "q_ok": q_ok, "t5": g, "t5_ok": g_ok,
                      "wall": statistics.median(L["walls"]) if L["walls"] else None,
                      "tps": tps.get(s), "vram": mem.get(tag)})

    # the two picks, from the rules printed with them
    ok = [r for r in table if r["q_ok"] and r["t5_ok"]]
    best = max(ok, key=lambda r: (r["rate"], -(r["wall"] or 1e9))) if ok else None
    tied = [r for r in ok if best and r["hi"] >= best["lo"] and r["lo"] <= best["hi"]]
    fast = min((r for r in tied if r["wall"]), key=lambda r: r["wall"], default=None)
    top_tb = max(table, key=lambda r: r["rate"]) if table else None

    def num(v, fmt):   # a sortable numeric cell; a missing value sorts last
        return f"<td class='num' data-v='{'' if v is None else v}'>{'&mdash;' if v is None else fmt.format(v)}</td>"

    def chip(good, text):
        return f"<span class='chip {'good' if good else 'crit'}'>{E(text)}</span>"

    trs = []
    for r in sorted(table, key=lambda r: (-(r["q_ok"] and r["t5_ok"]), -r["rate"])):
        mark = " <span class='chip good'>most correct</span>" if r is best else ""
        mark += " <span class='chip ref'>correct &amp; fastest</span>" if r is fast else ""
        h = r["h"]
        trs.append(
            f"<tr><td data-v='{E(r['name'])}'><b>{E(r['name'])}</b>{minfo(r['tag'])}{mark}"
            f"<div class='muted small'>{E(r['tag'])}</div></td>"
            f"<td class='cicell' data-v='{r['rate']:.3f}'><b>{r['rate']:.0f}%</b> "
            f"<span class='muted small'>{r['k']}/{r['n']} [{r['lo']:.0f}, {r['hi']:.0f}]</span>"
            f"<div class='ci'><div class='ci-range' style='left:{r['lo']:.1f}%;width:{r['hi'] - r['lo']:.1f}%'></div>"
            f"<div class='ci-dot' style='left:{r['rate']:.1f}%'></div></div></td>"
            f"<td data-v='{statistics.median(h) * 100 + min(h) if h else ''}'>"
            + (chip(r["q_ok"], f"{statistics.median(h):.0f}/18, worst {min(h)}") + f" <span class='muted small'>n={len(h)}</span>" if h else "<span class='muted'>&mdash;</span>")
            + f"</td><td data-v='{r['t5'].split('/')[0] if r['t5'] else ''}'>"
            + (chip(r["t5_ok"], r["t5"]) if r["t5"] else "<span class='muted small'>not run</span>")
            + "</td>" + num(r["wall"], "{:.0f} s") + num(r["tps"], "{:.0f}") + num(r["vram"], "{:.1f}") + "</tr>")

    picks = []
    if best:
        picks.append(f"<div class='pick'><div class='muted small'>MOST CORRECT</div><b>{E(best['name'])}</b>"
                     f"<div class='small'>Terminal-Bench {best['rate']:.0f}% [{best['lo']:.0f}, {best['hi']:.0f}], "
                     f"held-out {statistics.median(best['h']):.0f}/18, T5 {E(best['t5'])}</div>"
                     f"<div class='muted small'>Rule: highest Terminal-Bench among models with {QUALITY} and T5 &ge; {T5_MIN}/8.</div></div>")
    if fast:
        same = fast is best
        gap = (1 - fast["wall"] / best["wall"]) * 100 if best and best["wall"] else 0
        picks.append(f"<div class='pick'><div class='muted small'>CORRECT, FEW MISTAKES, FASTEST</div><b>{E(fast['name'])}</b>"
                     f"<div class='small'>{fast['wall']:.0f} s per session, Terminal-Bench {fast['rate']:.0f}%, held-out "
                     f"{statistics.median(fast['h']):.0f}/18, T5 {E(fast['t5'])}"
                     + ("" if same else f"; {gap:.0f}% faster than {E(best['name'])}"
                        + (" (not clearly: the rule needs &ge; 25%)" if gap < 25 else "")) + "</div>"
                     "<div class='muted small'>Rule: fastest session among the same eligible models whose Terminal-Bench "
                     "interval overlaps the most correct one's.</div></div>")

    notes = []
    if top_tb and best and top_tb is not best:
        why = "fails held-out quality" if not top_tb["q_ok"] else ("T5 below 7/8" if top_tb["t5"] else "T5 not run")
        notes.append(f"Highest Terminal-Bench score: {E(top_tb['name'])} {top_tb['rate']:.0f}%, not picked: {why}.")
    notes.append("All Terminal-Bench intervals overlap, so no model is significantly more correct than another.")
    x = extended()
    if x:
        (m1, (k1, n1)), (m2, (k2, n2)) = sorted(x["tot"].items(), key=lambda kv: -kv[1][0] / kv[1][1])
        notes.append(f"Extended Terminal-Bench, {x['tasks']} more tasks &times; 2: {E(m1.split('_')[0])} {k1}/{n1} = {100 * k1 / n1:.0f}% vs "
                     f"{E(m2.split('_')[0])} {k2}/{n2} = {100 * k2 / n2:.0f}%, sign test p = {x['p']:.2f}: a tie"
                     + (", and the two ran on different Ollama versions (information only)." if x["mixed"] else "."))

    vline, vwhen = verdict_line()
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agentic Model Results</title>
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
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:16px;margin:28px 0 8px}} h3{{font-size:14px;margin:18px 0 6px}}
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
#tip{{position:fixed;z-index:10;max-width:380px;padding:10px 12px;border-radius:8px;background:var(--ink);color:var(--paper);
font-size:13px;line-height:1.45;font-weight:400;text-transform:none;letter-spacing:0;box-shadow:0 6px 20px rgba(0,0,0,.25);
pointer-events:none;display:none}}
th.sortable{{cursor:pointer;user-select:none}} th.sortable:hover{{color:var(--ink)}}
th.sortable::after{{content:" \\2195";opacity:.35}} th[aria-sort=ascending]::after{{content:" \\2191";opacity:1}}
th[aria-sort=descending]::after{{content:" \\2193";opacity:1}}
.pick{{background:var(--panel);border:1px solid var(--rule);border-left:4px solid var(--good);border-radius:10px;padding:12px 14px;flex:1 1 280px}}\n.pick b{{font-size:18px}} .picks{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}\n.chip.ref{{background:var(--ref-soft);color:var(--ref)}}\n</style><body><main>
<h1>Local agentic coding on .67: final results</h1>
<div class="muted small">Round 2026-09-24 to 10-08 &middot; Claude Code against Ollama &middot; generated {datetime.now():%Y-%m-%d %H:%M} from results/ &middot; details: ROUND_2026-09-24.md</div>

<div class="picks">{''.join(picks)}</div>

<div class="panel"><table>
<tr>{th("model","model")}{th("Terminal-Bench","tb")}{th("held-out tests","hidden")}{th("T5 &times;8","t5")}{th("session","session")}{th("tok/s","tps")}{th("VRAM GB","vram")}</tr>
{''.join(trs)}
</table></div>
<ul class="small muted">{''.join(f"<li>{n}</li>" for n in notes)}</ul>
<p class="small muted">Verdict ({E(vwhen)}): {E(vline)}. Click a column to sort.</p>
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
