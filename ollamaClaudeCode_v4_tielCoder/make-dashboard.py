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
# task count of the parity arm, read from the frozen subset rather than hard-coded
N_TASKS = len([l for l in (HERE / "terminalbench" / "official" / "subset.txt").read_text().splitlines()
               if l.strip() and not l.lstrip().startswith("#")])


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
    # the bold verdict, then its dated italic note -- on the same line or the next
    m = re.search(r"## Verdict so far\s+\*\*(.+?)\*\*\s*\*\((.+?)\)\*", s, re.S)
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
          "the tasks' own tests. A frozen subset of 10 tasks, run 3 times each; 8 are scored because nginx-request-logging and "
          "polyglot-c-py contradict their own tests. Thinking is on for every model, only complete passes count, and infrastructure failures are void, "
          "not zero. The small line shows solved/trials and the 95% interval.",
    "ci": "The 95% Wilson confidence interval of the Terminal-Bench rate, drawn on a 0-100% axis: the band is the interval, the dot "
          "the measured rate. With only 24 trials per model the band is about 35 points wide. Two models whose bands overlap are "
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
    "rb_model": "The Ollama tag, exactly as run.",
    "rb_n": "How many ledger sessions ran for this model in the re-baseline. Five are planned per model, all on the same Claude Code version, back to back, so the client cannot differ between models.",
    "rb_range": "Fastest to slowest of the five sessions. 'Clearly faster' requires the ranges of two models not to overlap AND a median at least 25% lower -- a threshold fixed before these runs.",
    "rb_rule": "The quality rule fixed before these runs: the median of the held-out scores must be 18/18 and no single run may fall below 16/18.",
    "t5": "Gate T5 re-run eight times: fill a nested schema exactly (an 'edits' array of two objects), the shape Claude Code's edit tools send. At least 7 of 8 is required -- one miss in eight is sampling noise, more is a defect.",
    "ref": "A setting tested on the current pick, one variable at a time, against the same model without it.",
    "ref_res": "R1: share of input tokens NOT served from the prompt cache, lower is better. R3: generation speed with the penalty on, to see whether Ollama applies it at all. R5: what the model does when the prompt exceeds its window -- refusing is safe, silently halving is not.",
    "ext": "Terminal-Bench on 30 extra tasks drawn with a fixed seed before any result, minus any task whose own reference solution fails. Two attempts each. The pooled comparison with the 9 original tasks and the paired sign test are in results/s11-ext.log.",
    "note": "The model's reported capabilities (tools, thinking, vision), or the reason it was cut.",
}


# ------------------------------------------------ re-run with new settings (09-25)
GATE_RERUN_HISTORY = 2


def rerun_section(E):
    """The runs the 09-25 review made mandatory, each read from its own data file,
    each showing 'pending' until its data exists."""
    import glob, json
    parts = []
    # A. same-version re-baseline: cc-session-rb0925.tsv, ledger x5 per model
    rb = defaultdict(list)
    for r in rows("cc-session-rb0925.tsv"):
        if r.get("fixture") == "hard" and r.get("thinking") == "on":
            rb[r["model"]].append(r)
    body = []
    for m, rs in rb.items():
        rs = rs[-5:]
        w = [float(r["wall_s"]) for r in rs if r["wall_s"].replace(".", "", 1).isdigit()]
        h = [int(r["hidden"].split("/")[0]) for r in rs if "/" in r.get("hidden", "")]
        ok = bool(h) and statistics.median(h) == 18 and min(h) >= 16
        body.append(f"<tr><td data-v='{E(m)}'><b>{E(m)}</b>{minfo(m)}</td><td class='num' data-v='{len(rs)}'>{len(rs)}</td>"
                    f"<td class='num' data-v='{statistics.median(w) if w else ''}'>{f'{statistics.median(w):.0f} s' if w else '&mdash;'}</td>"
                    f"<td class='num' data-v='{min(w) if w else ''}'>{f'{min(w):.0f}&ndash;{max(w):.0f}' if w else '&mdash;'}</td>"
                    f"<td data-v='{statistics.mean(h) if h else ''}'>" + (" ".join(
                        f"<span class='chip {'good' if x == 18 else 'warn'}'>{x}/18</span>" for x in h) or "&mdash;") +
                    f"</td><td data-v='{int(ok)}'><span class='chip {'good' if ok else 'crit'}'>{'PASS' if ok else 'fail'}</span></td></tr>")
    parts.append("<h3>A. Same-version re-baseline: ledger &times;5 on one Claude Code version</h3>"
                 "<div class='panel'><table><tr>" + th("model", "rb_model") + th("runs", "rb_n") + th("median", "session")
                 + th("range", "rb_range") + th("held-out per run", "hidden") + th("quality rule", "rb_rule") + "</tr>"
                 + ("".join(body) or "<tr><td colspan='6' class='muted'>pending (s12-rebaseline.sh)</td></tr>")
                 + "</table></div>")
    # B. gate consistency: T5 x8 (gate-rerun.tsv has no header: model gate pass verdict)
    g = {}
    f = RES / "gate-rerun.tsv"
    if f.exists():
        # gate-rerun.tsv carries no date; its first GATE_RERUN_HISTORY lines are the 09-17
        # re-runs, which must not be shown as today's result (they were, for one render)
        for line in f.read_text().splitlines()[GATE_RERUN_HISTORY:]:
            c = line.split("\t")
            if len(c) >= 4 and c[1] == "T5":
                g[c[0]] = (c[2], c[3])
    wanted = ["kat-coder-v2.5:q5km-ctx256k-agentic", "tiel-coder:35b-q5-ctx256k-agentic",
              "occamy-1.0:q5km-ctx256k-agentic", "ornith-1.5-35b:q5km-ctx256k-agentic",
              "byteshape-qwen3.6-35b:q4ks-ctx256k-agentic"]
    gb = "".join(f"<tr><td data-v='{E(m)}'>{E(m)}{minfo(m)}</td><td data-v='{g[m][0] if m in g else ''}'>"
                 f"{E(g[m][0]) + ' ' + E(g[m][1]) if m in g else '<span class=muted>pending</span>'}</td></tr>" for m in wanted)
    parts.append("<h3>B. Tool-gate consistency: T5 nested schema &times;8</h3><div class='panel'><table><tr>"
                 + th("model", "rb_model") + th("T5 passes of 8", "t5") + "</tr>" + gb + "</table></div>")
    # C. refinements on the pick
    def arm(a):
        out = []
        for fn in sorted(glob.glob(str(RES / "cc" / f"kat-coder-v2.5_q5km-ctx256k-agentic-hard-thinkon-{a}-r[0-9]*.jsonl"))):
            for line in open(fn):
                i = line.find("{")
                if i < 0:
                    continue
                try:
                    d = json.loads(line[i:])
                except ValueError:
                    continue
                if d.get("type") == "result":
                    u = d.get("usage") or {}
                    tot = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                    out.append((100 * u.get("input_tokens", 0) / tot if tot else 0, d.get("duration_ms", 0) / 1000))
        return out
    cr = []
    for a, label in (("remindon", "reminder default"), ("remindoff", "CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off")):
        v = arm(a)
        cr.append(f"<tr><td data-v='{label}'>R1 caching: {E(label)}</td><td data-v='{len(v)}'>"
                  + (f"{len(v)} runs &middot; uncached {statistics.median([x for x, _ in v]):.1f}% &middot; "
                     f"median {statistics.median([y for _, y in v]):.0f} s" if v else "<span class=muted>pending</span>") + "</td></tr>")
    pp = [r for r in rows("tokrate.tsv") if r.get("model", "").endswith("-pp15") and r.get("prompt_words") == "2000"]
    cr.append("<tr><td data-v='R3'>R3 presence_penalty 1.5 vs 0 (KAT, 2k prompt)</td><td data-v='1'>"
              + (f"{pp[-1]['gen_tps']} tok/s with 1.5, against {tokrate().get(slug('kat-coder-v2.5:q5km-ctx256k-agentic'), 0):.0f} with 0" if pp
                 else "<span class=muted>pending</span>") + "</td></tr>")
    ov = [r for r in rows("overflow.tsv") if r.get("model", "").startswith("kat-coder")]
    cr.append("<tr><td data-v='R5'>R5 overflow past the window (KAT)</td><td data-v='1'>"
              + (f"{E(ov[-1]['regime'])} ({E(ov[-1]['detail'])})" if ov else "<span class=muted>pending</span>") + "</td></tr>")
    parts.append("<h3>C. Refinements, on the pick</h3><div class='panel'><table><tr>" + th("refinement", "ref")
                 + th("result", "ref_res") + "</tr>" + "".join(cr) + "</table></div>")
    # D. extended Terminal-Bench (arm thinkon-ext)
    ext = defaultdict(lambda: [0, 0])
    for r in rows("terminal-bench-official.tsv"):
        if r.get("arm") == "thinkon-ext" and r["task"] not in DEFECTIVE and r["failure_mode"] not in INFRA:
            ext[r["model"]][1] += 1
            ext[r["model"]][0] += r["resolved"] == "True"
    eb = "".join(f"<tr><td data-v='{E(m)}'>{E(m)}{minfo(m)}</td><td class='num' data-v='{100 * k / n if n else 0}'>{k}/{n} = "
                 f"{100 * k / n:.0f}% [{wilson(k, n)[0]:.0f}, {wilson(k, n)[1]:.0f}]</td></tr>" for m, (k, n) in ext.items() if n)
    parts.append("<h3>D. Extended Terminal-Bench: 30 seeded, oracle-checked tasks, n=2</h3><div class='panel'><table><tr>"
                 + th("model", "rb_model") + th("solved (extended tasks only)", "ext") + "</tr>"
                 + (eb or "<tr><td colspan='2' class='muted'>pending (s11-ext.sh, overnight)</td></tr>") + "</table></div>")
    return ("<h2>Re-run with new settings (2026-09-25)</h2><p class='small muted'>Everything below runs because "
            "review_20260925.md found the speed axis confounded with the Claude Code version and G2 applied unevenly. "
            "Rule fixed before these results: quality = median 18/18 and no run below 16; clearly faster = median "
            "&ge; 25% lower and non-overlapping 5-run ranges; correctness = non-overlapping pooled intervals, else a "
            "paired sign test p &lt; 0.05.</p>" + "".join(parts))


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
}
# candidate names used by the screen TSV
for _n, _t in (("occamy", "occamy-1.0:q5km-ctx256k-agentic"), ("kat-coder", "kat-coder-v2.5:q5km-ctx256k-agentic"),
               ("ornith15-35b", "ornith-1.5-35b:q5km-ctx256k-agentic"),
               ("byteshape", "byteshape-qwen3.6-35b:q4ks-ctx256k-agentic")):
    MODEL_FACTS[_n] = MODEL_FACTS[_t]


def minfo(key):
    """(i) with the model's fact card; accepts a tag, a Terminal-Bench slug or a screen name."""
    f = MODEL_FACTS.get(key) or next((v for k, v in MODEL_FACTS.items() if slug(k) == key), None)
    if not f:
        return ""
    return (f'<span class="info" tabindex="0" role="button" aria-label="About this model" '
            f'data-tip="{html.escape(f, quote=True)}">i</span>')


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
            "name": name, "note": note, "tag": tag,
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
            f"<tr><td data-v='{E(r['name'])}'><b>{E(r['name'])}</b>{minfo(r['tag'])}<div class='muted small'>{E(r['note'])}</div></td>"
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
            f"<tr><td data-v='{E(c['name'])}'><b>{E(c['name'])}</b>{minfo(c['name'])}<div class='muted small'>{E(c['source'])}</div></td>"
            f"<td data-v='{E(v)}'><span class='chip {tone}'>{E(v)}</span></td>"
            f"<td class='num' data-v='{cv('got_gib')}'>{E(c.get('got_gib') or '-')}</td>"
            f"<td class='num' data-v='{cv('vram_gb')}'>{E(c.get('vram_gb') or '-')}</td>"
            f"<td data-v='{cv('gates')}'>{E(c.get('gates') or '-')}</td>"
            f"<td class='num' data-v='{cv('gen_toks')}'>{E(c.get('gen_toks') or '-')}</td>"
            f"<td class='num' data-v='{cv('ledger_median_s')}'>{E(c.get('ledger_median_s') or '-')}</td>"
            f"<td data-v='{cv('ledger_hidden')}'>{E(c.get('ledger_hidden') or '-')}</td>"
            f"<td class='small' data-v='{E(c.get('note') or '')}'>{E(c.get('note') or '')}</td></tr>")
    queue = ["occamy", "kat-coder", "ornith15-35b", "byteshape", "laguna-xs21"]
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

{rerun_section(E)}

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
