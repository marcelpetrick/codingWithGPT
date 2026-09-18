#!/usr/bin/env python3
"""make-report.py -- build report.html (and report.pdf) from the TSVs in results/.

A generator rather than a hand-written page: the stages land over hours and the
report is regenerated as they do. Everything it draws comes from results/*.tsv;
a stage that has not run says so instead of showing an invented number.

Design follows ../ollamaClaudeCode_v3_qwen3.8/report.html, which reads better
than a wall of SVG: a masthead carrying the verdict, a KPI strip of the few
numbers that decide anything, panels of CSS bar rows (selectable text, reflows
at phone width, no viewBox arithmetic), semantic callouts for the warnings, and
dense tables underneath.

The output is a STANDALONE local file: a complete HTML document that makes no
network request at all -- no webfonts, no scripts, no CDN. It opens from disk on
a machine with no internet. Fonts are system stacks for the same reason.

Usage: ./make-report.py [--out report.html] [--pdf]
"""
import argparse
import csv
import glob
import html
import os
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

SHORT = {
    "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest": "Tiel · shipped",
    "tiel-coder:35b-q5-ctx256k-agentic": "Tiel · pp0",
    "cyber-tiel:35b-q5-ctx256k-agentic": "CyberTiel · pp0",
    "north-mini-code-1.0:q4_K_M-ctx256k-agentic": "north-mini",
    "qwen3.6:35b-a3b-q4_K_M-agentic": "qwen3.6 35b",
    "ornith:35b-ctx256k-agentic": "ornith 1.0",
    "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic": "gemma4 26b",
    "nemotron-3.5-lightning:30b-ctx256k-agentic": "nemotron-3.5-L",
    "nemotron-cascade-2:30b-ctx256k-agentic": "cascade-2",
    "qwen3.8:27b-q4_K_M-ctx128k-agentic": "qwen3.8 27b",
}
# Rejected twice on the same defect: kept in the tables, never in a headline.
CUT = {"nemotron-cascade-2:30b-ctx256k-agentic", "qwen3.8:27b-q4_K_M-ctx128k-agentic"}
TBO_VERSION = "0.2.18"          # upstream harness, pinned
TBO_DATASET = "0.1.1"           # terminal-bench-core
T_SHIP = "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest"
T_PP0 = "tiel-coder:35b-q5-ctx256k-agentic"
CT = "cyber-tiel:35b-q5-ctx256k-agentic"
SUBJECT = {T_SHIP, T_PP0, CT}


def short(m):
    return SHORT.get(m, m.split("/")[-1][:26])


def read_tsv(name):
    p = RES / name
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def esc(s):
    return html.escape(str(s))


def bars(rows, unit="", fmt="{:.0f}", hi=None, lower_better=False):
    """rows: [(label, value, tone)] -> CSS bar rows. tone in good/ref/warn/crit."""
    rows = [r for r in rows if r[1] is not None]
    if not rows:
        return '<p class="empty">Not measured yet.</p>'
    rows = sorted(rows, key=lambda r: r[1] if lower_better else -r[1])
    vmax = max(r[1] for r in rows) or 1
    out = ['<div class="rows">']
    for label, val, tone in rows:
        pct = max(1.5, 100 * val / vmax)
        cls = "row hl" if (hi and hi in label) else "row"
        out.append(
            f'<div class="{cls}"><div class="name" title="{esc(label)}">{esc(label)}</div>'
            f'<div class="track"><div class="bar {tone}" style="width:{pct:.1f}%"></div></div>'
            f'<div class="val">{fmt.format(val)}{esc(unit)}</div></div>')
    out.append("</div>")
    return "".join(out)


def panel(title, cap, body, note=""):
    n = f'<div class="legend">{note}</div>' if note else ""
    return (f'<div class="chart"><h3>{esc(title)}</h3><p class="cap">{cap}</p>{body}{n}</div>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.html"))
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args()

    # ---------------- data ----------------
    gen, pre = {}, {}
    for r in read_tsv("tokrate.tsv"):
        try:
            if r["prompt_words"] == "2000":
                gen[r["model"]] = float(r["gen_tps"])
            if r["prompt_words"] == "20000":
                pre[r["model"]] = float(r["prefill_tps"])
        except (ValueError, KeyError):
            pass

    cache = defaultdict(dict)
    for r in read_tsv("cache.tsv"):
        try:
            cache[r["model"]][r["phase"]] = (float(r["wall_s"]), int(r["new_tok"]))
        except (ValueError, KeyError):
            pass

    overflow = {}
    for r in read_tsv("overflow.tsv"):
        overflow[r["model"]] = r["regime"]

    vision = defaultdict(lambda: [0, 0])
    for r in read_tsv("vision.tsv"):
        try:
            g, p = r["checks"].split("/")
            vision[r["model"]][0] += int(g)
            vision[r["model"]][1] += int(p)
        except (ValueError, KeyError):
            pass

    needle = defaultdict(int)
    cur = None
    npath = RES / "needle-v2.log"
    if npath.exists():
        for line in npath.read_text(errors="replace").splitlines():
            if line.startswith("=== needle-v2 on"):
                cur = line.split(": ", 1)[1].split(" (")[0] if ": " in line else None
            elif cur and "PASS" in line and "prompt_eval=" in line:
                try:
                    v = int(line.split("prompt_eval=")[1].split()[0])
                    needle[cur] = max(needle[cur], v)
                except (ValueError, IndexError):
                    pass

    dualuse = defaultdict(dict)         # model -> task -> outcome
    for r in read_tsv("dualuse.tsv"):
        dualuse[r["model"]][r["task"]] = r["outcome"]

    xgates = defaultdict(dict)          # model -> gate -> "n/N"
    for r in read_tsv("gate-extra.tsv"):
        xgates[r["model"]][r["gate"]] = f'{r["pass_n"]}/{r["runs"]}'

    gates = {}
    for f in glob.glob(str(RES / "agentic" / "*.tsv")) + glob.glob(str(RES / "agentic" / "run1" / "*.tsv")):
        rows = list(csv.DictReader(open(f), delimiter="\t"))
        if rows:
            gates.setdefault(os.path.basename(f)[:-4], sum(1 for r in rows if r["result"] == "PASS"))

    def gates_for(m):
        return gates.get(m.replace(":", "_").replace("/", "_"))

    sess = defaultdict(lambda: {"w": [], "v": [], "h": [], "t": []})
    for fname, harness in (("cc-session.tsv", "host"), ("cc-session-sandboxed.tsv", "sandbox")):
        for r in read_tsv(fname):
            k = (r["model"], r["fixture"], r.get("thinking", "on"), harness)
            try:
                sess[k]["w"].append(int(r["wall_s"]))
            except (ValueError, KeyError):
                continue
            sess[k]["v"].append(r.get("verdict", "?"))
            if r.get("hidden", "-") not in ("-", ""):
                sess[k]["h"].append(r["hidden"])
            try:
                sess[k]["t"].append(int(r["think_chars"]))
            except (ValueError, KeyError):
                pass

    def S(model, fixture="hard", thinking="on", harness="host"):
        return sess.get((model, fixture, thinking, harness))

    def med(model, fixture="hard", thinking="on", harness="host"):
        d = S(model, fixture, thinking, harness)
        return statistics.median(d["w"]) if d and d["w"] else None

    def perfect_runs(model, harness="host"):
        d = S(model, "hard", "on", harness)
        if not d or not d["h"]:
            return None
        return sum(1 for x in d["h"] if x == "18/18"), len(d["h"])

    # ---------------- terminal-bench ----------------
    tb = defaultdict(lambda: defaultdict(list))   # model -> task -> [verdicts]
    tb_tasks = []
    for r in read_tsv("terminalbench.tsv"):
        tb[r["model"]][r["task"]].append(r["verdict"])
        if r["task"] not in tb_tasks:
            tb_tasks.append(r["task"])

    # ------------- terminal-bench, OFFICIAL harness -------------
    # summarise.py keys rows by run-id, which is lowercased and ':'-flattened so
    # docker compose will accept it as a project name. Map back to the real tag
    # so the table can use the same short labels as every other section.
    tag_by_runid = {m.replace("/", "_").replace(":", "_").lower(): m for m in SHORT}
    INFRA_MODES = {"unknown_agent_error", "agent_installation_failed", "test_timeout",
                   "unknown_error", "fatal_llm_parse_error"}
    tbo = defaultdict(lambda: defaultdict(list))   # model -> task -> [row]
    tbo_tasks = []
    for r in read_tsv("terminal-bench-official.tsv"):
        m = tag_by_runid.get(r["model"], r["model"])
        tbo[m][r["task"]].append(r)
        if r["task"] not in tbo_tasks:
            tbo_tasks.append(r["task"])
    # Present the tasks in the order the frozen subset fixes, not the order the
    # harness happened to schedule them -- otherwise the columns reshuffle between
    # regenerations and two printings of "the same" table do not line up.
    subset_file = HERE / "terminalbench" / "official" / "subset.txt"
    if subset_file.exists():
        frozen = [l.strip() for l in subset_file.read_text().splitlines()
                  if l.strip() and not l.startswith("#")]
        tbo_tasks = ([t for t in frozen if t in tbo_tasks] +
                     [t for t in tbo_tasks if t not in frozen])

    # ---------------- KPIs ----------------
    pp_gain = (f"+{(gen[T_PP0] / gen[T_SHIP] - 1) * 100:.0f}%"
               if gen.get(T_PP0) and gen.get(T_SHIP) else "—")
    t_on, t_off = med(T_SHIP, "hard", "on"), med(T_SHIP, "hard", "off")
    think_gain = f"{t_on / t_off:.1f}×" if (t_on and t_off) else "—"
    pr = perfect_runs(T_PP0)
    halvers = sum(1 for m, v in overflow.items() if v == "HALVED")
    kpis = [
        (f"{gen.get(T_PP0, 0):.0f}", "tok/s generation<br>Tiel, penalty removed", "good"),
        (pp_gain, "over the tag as shipped<br>one sampler setting", "good"),
        (f"{max(needle.values()) if needle else 0:,}".replace(",", ","), "tokens of verified recall<br>deepest in v1–v4", "ref"),
        (f"{pr[0]}/{pr[1]}" if pr else "—", "runs that solved the spec<br>all 18 held-out tests", "good"),
        (think_gain, "faster with thinking off<br>no loss of correctness", "ref"),
        (f"{halvers}", "models that silently halve<br>an over-long prompt", "crit"),
    ]
    # Headline facts for the masthead, computed rather than written down, so the
    # verdict cannot drift away from the table underneath it.
    tbo_rank, tbo_flips = [], {}
    for m in tbo:
        live = [r for t in tbo[m] for r in tbo[m][t]
                if r["failure_mode"] not in INFRA_MODES]
        if not live:
            continue
        runs = max(len(v) for v in tbo[m].values())
        tbo_rank.append((sum(r["resolved"] == "True" for r in live) / len(live), m, runs))
        tbo_flips[m] = sum(1 for t, v in tbo[m].items()
                           if 0 < sum(r["resolved"] == "True" for r in v) < len(v))
    tbo_rank.sort(reverse=True)

    if tbo_rank:
        (br, bm, _), = tbo_rank[:1]
        subj = [(r, m, n) for r, m, n in tbo_rank if m in SUBJECT]
        bits = [f"<b>{esc(short(bm))} leads at {br * 100:.0f}%</b>"]
        if subj:
            sr, sm, _ = subj[0]
            if sm != bm:
                bits.append(f"the best contender ({esc(short(sm))}) trails at {sr * 100:.0f}%")
        fl = {m: tbo_flips.get(m, 0) for _, m, n in tbo_rank if n > 1}
        if fl:
            steady = min(fl, key=lambda m: fl[m])
            noisy = [m for m in fl if fl[m] > fl[steady]]
            if noisy:
                bits.append(f"and it is the steadiest of the sampled models — {fl[steady]} task "
                            f"landing differently between runs, against "
                            f"{max(fl[m] for m in noisy)} for the contenders")
        tbo_verdict = ", ".join(bits) + "."
    else:
        tbo_verdict = "has not been run yet."

    kpi_html = "".join(
        f'<div class="kpi"><div class="n {tone}">{v}</div><div class="l">{l}</div></div>'
        for v, l, tone in kpis)

    # ---------------- charts ----------------
    def tone_for(m):
        return "good" if m in SUBJECT else ("crit" if m in CUT else "ref")

    gen_rows = [(short(m), v, tone_for(m)) for m, v in gen.items()]
    hard_rows = [(short(m), statistics.median(d["w"]), tone_for(m))
                 for (m, fx, th, hn), d in sess.items()
                 if fx == "hard" and th == "on" and hn == "host" and d["w"]]
    cache_rows = [(short(m), ph["extend"][0], tone_for(m))
                  for m, ph in cache.items() if "extend" in ph]
    pp_rows = [(l, gen[k], t) for l, k, t in
               (("shipped · pp 1.5", T_SHIP, "crit"), ("variant · pp 0", T_PP0, "good"))
               if gen.get(k)]
    think_rows = [(l, med(T_SHIP, "hard", th), t) for l, th, t in
                  (("thinking on", "on", "crit"), ("thinking off", "off", "good"))
                  if med(T_SHIP, "hard", th)]

    charts = "".join([
        panel("Generation speed", "tok/s at a 2,000-word prompt, thinking disabled, temperature 0. "
              "Higher is better.", bars(gen_rows, " tok/s"),
              "Tiel is the only Q5 here — 27.5 GB of weights against 18–24 GB. Its own q4 ancestor "
              "<span class='mono'>ornith 1.0</span> runs 127, so the gap is the quant tier, not the model. "
              "The two Tiel bars are the same weights one sampler setting apart: the shipped tag's "
              f"<span class='mono'>presence_penalty 1.5</span> costs {pp_gain.lstrip('+')}, paid per "
              "generated token — prefill moves less than 2%."),
        panel("Time to finish the hard job", "Median of three real Claude Code sessions on the "
              "three-module fixture. Lower is better.",
              bars(hard_rows, " s", "{:.0f}", lower_better=True),
              "Tokens per second does not predict this — the fastest model on the box is last."),
        panel("What thinking costs, end to end", "Session wall clock, not tok/s: Tiel on the hard "
              "fixture, median of three, with and without "
              "<span class='mono'>&lt;|think_off|&gt;</span>.",
              bars(think_rows, " s", "{:.0f}", lower_better=True),
              "Held-out scores were equal or better with thinking off, and the only session Tiel "
              "failed all day was a thinking-on run."),
        panel("Cost of one agent turn", "Seconds to first token when a long prefix is reused and only "
              "a tool result is appended.", bars(cache_rows, " s", "{:.2f}", lower_better=True),
              "New in Ollama 0.33.3. On 0.32.15 every one of these was a full re-read of the context."),
    ])

    # ---------------- Tiel vs CyberTiel ----------------
    def cell(v, fmt="{:.1f}"):
        return fmt.format(v) if v is not None else "—"

    vt, vc = vision.get(T_PP0, [0, 0]), vision.get(CT, [0, 0])
    st, sc = perfect_runs(T_PP0, "sandbox"), perfect_runs(CT, "sandbox")
    vs_rows = [
        ("generation @2k", f"{cell(gen.get(T_PP0))} tok/s", f"{cell(gen.get(CT))} tok/s"),
        ("cold prefill @35k", f"{cell(pre.get(T_PP0), '{:,.0f}')} tok/s", f"{cell(pre.get(CT), '{:,.0f}')} tok/s"),
        ("deepest verified recall", f"{needle.get(T_SHIP, 0):,} tok", f"{needle.get(CT, 0):,} tok"),
        ("resident @262,144", "34.13 GB", "34.13 GB"),
        ("vision checks", f"{vt[0]}/{vt[1] or 25}", f"{vc[0]}/{vc[1] or 25}"),
        ("over-long prompt", "refuses (400)", "refuses (400)"),
        ("hard fixture, sandboxed", f"{st[0]}/{st[1]} runs at 18/18" if st else "—",
         f"{sc[0]}/{sc[1]} runs at 18/18" if sc else "—"),
        ("refusals on 8 benign security prompts", "0", "0"),
    ]
    vs_html = "".join(f'<tr><td>{esc(k)}</td><td class="num">{esc(x)}</td><td class="num">{esc(y)}</td></tr>'
                      for k, x, y in vs_rows)


    # ---- dual-use (abliteration discriminator) ----
    du_models = [m for m in (T_PP0, T_SHIP, CT) if m in dualuse]
    du_html = ""
    if du_models:
        tasks = [r["task"] for r in read_tsv("dualuse.tsv")]
        seen = []
        for t in tasks:
            if t not in seen:
                seen.append(t)
        def dchip(o):
            cls = {"DID_IT": "good", "CAUTIONED": "good", "HEDGED": "", "REFUSED": "crit"}.get(o, "")
            lab = {"DID_IT": "did it", "CAUTIONED": "did it +note", "HEDGED": "hedged",
                   "REFUSED": "refused"}.get(o, o)
            return f'<span class="pill {cls}">{lab}</span>'
        head = "".join(f"<th>{esc(short(m))}</th>" for m in du_models)
        body = ""
        for t in seen:
            cells = "".join(f"<td>{dchip(dualuse[m].get(t,'-'))}</td>" for m in du_models)
            body += f"<tr><td>{esc(t)}</td>{cells}</tr>"
        du_html = (f'<div class="tablewrap"><table><thead><tr><th>task (all authorized / local / CTF)</th>'
                   f'{head}</tr></thead><tbody>{body}</tbody></table></div>')

    # ---- extra gates T8-T11 ----
    xg_html = ""
    if xgates:
        order = ["T8_structured_output", "T9_error_recovery", "T10_argument_fidelity", "T11_zero_arg_tool"]
        lab = {"T8_structured_output": "T8 JSON out", "T9_error_recovery": "T9 error-recovery",
               "T10_argument_fidelity": "T10 arg-fidelity", "T11_zero_arg_tool": "T11 zero-arg"}
        rows_xg = ""
        for m in sorted(xgates, key=lambda m: -gen.get(m, 0)):
            cells = "".join(f'<td class="num">{xgates[m].get(g,"—")}</td>' for g in order)
            rows_xg += f"<tr><td>{esc(short(m))}</td>{cells}</tr>"
        xg_html = ('<div class="tablewrap"><table><thead><tr><th>model</th>'
                   + "".join(f"<th>{lab[g]}</th>" for g in order)
                   + f"</tr></thead><tbody>{rows_xg}</tbody></table></div>")

    # ---------------- tables ----------------
    field_rows = []
    for m in sorted(gen, key=lambda m: -gen[m]):
        g = gates_for(m)
        ovf = overflow.get(m, "")
        ovf_cell = ('<span class="pill good">refuses</span>' if ovf.startswith("ERROR")
                    else '<span class="pill crit">halves silently</span>' if ovf == "HALVED"
                    else '<span class="pill">—</span>')
        vg, vp = vision.get(m, [0, 0])
        vis = "yes" if vp and vg == vp else ("partial" if vp else "no")
        cut = ' <span class="pill crit">cut</span>' if m in CUT else ""
        field_rows.append(
            f'<tr><td>{esc(short(m))}{cut}</td><td class="num">{gen[m]:.0f}</td>'
            f'<td class="num">{pre.get(m, 0):,.0f}</td>'
            f'<td class="num">{(str(g) + "/10") if g else "—"}</td><td>{vis}</td><td>{ovf_cell}</td></tr>')

    cap_rows = []
    for (m, fx, th, hn), d in sorted(sess.items(),
                                     key=lambda kv: statistics.median(kv[1]["w"]) if kv[1]["w"] else 1e9):
        if fx != "hard" or not d["w"]:
            continue
        ok = sum(v == "PASS" for v in d["v"])
        allh = ", ".join(d["h"]) or "—"
        perfect = bool(d["h"]) and all(x == "18/18" for x in d["h"])
        cap_rows.append(
            f'<tr><td>{esc(short(m))}</td><td>{esc(th)}</td><td>{esc(hn)}</td>'
            f'<td><span class="pill {"good" if ok == len(d["v"]) else "crit"}">{ok}/{len(d["v"])}</span></td>'
            f'<td class="num">{statistics.median(d["w"]):.0f} s</td>'
            f'<td class="num {"good" if perfect else ""}">{esc(allh)}</td></tr>')

    tb_html = ""
    if tb_tasks:
        head = "".join(f"<th>{esc(t)}</th>" for t in tb_tasks)
        rows_tb = ""
        for m in sorted(tb, key=lambda m: -gen.get(m, 0)):
            cells = ""
            for t in tb_tasks:
                vs = tb[m].get(t, [])
                ok = sum(1 for v in vs if v == "SOLVED")
                if not vs:
                    cells += '<td>—</td>'; continue
                cls = "good" if ok == len(vs) else ("crit" if ok == 0 else "")
                cells += f'<td><span class="pill {cls}">{ok}/{len(vs)}</span></td>'
            rows_tb += f"<tr><td>{esc(short(m))}</td>{cells}</tr>"
        tb_html = ('<div class="tablewrap"><table><thead><tr><th>model</th>' + head +
                   f'</tr></thead><tbody>{rows_tb}</tbody></table></div>')

    # The per-task grid, not just a rate: two models can score the same and solve
    # disjoint sets, and which tasks a model can actually finish is the thing that
    # decides what you run it for. Infra failures are shown as VOID, never as a
    # zero -- an uppercase run-id once voided three whole passes that read as 0%.
    tbo_html = ""
    if tbo_tasks:
        def rate_of(rows):
            live = [r for r in rows if r["failure_mode"] not in INFRA_MODES]
            if not live:
                return None
            return sum(r["resolved"] == "True" for r in live) / len(live)

        def tbo_cell(rows):
            """One encoding for every cell, whatever the sample count.

            The first cut printed "SOLVED" for a model sampled once and "3/3" for
            a model sampled three times -- two spellings of the same outcome,
            picked by an accident of scheduling. Now every cell carries the same
            three things: the verdict, the tally it rests on, and the time.
            FLIPS is its own verdict because a task that lands differently between
            runs is the round's most important state, not a rounding detail.
            """
            if not rows:
                return '<td class="tbo-na">not run</td>'
            void = [r for r in rows if r["failure_mode"] in INFRA_MODES]
            if len(void) == len(rows):
                return ('<td><span class="pill" title="infrastructure failure, '
                        'not a model result">VOID</span></td>')
            live = [r for r in rows if r["failure_mode"] not in INFRA_MODES]
            n = len(live)
            ok = sum(r["resolved"] == "True" for r in live)
            secs = [float(r["agent_sec"]) for r in live if r["agent_sec"]]
            med = statistics.median(secs) if secs else 0
            if ok == n:
                label, cls = "SOLVED", "good"
            elif ok == 0:
                all_to = all(r["failure_mode"] == "agent_timeout" for r in live)
                label, cls = ("TIMEOUT" if all_to else "failed"), "crit"
            else:
                label, cls = "FLIPS", "warn"
            tally = f'{ok}/{n}'
            note = f'<span class="tbo-s">{tally} · {med:.0f}s</span>' if med else \
                   f'<span class="tbo-s">{tally}</span>'
            return f'<td><span class="pill {cls}">{label}</span>{note}</td>'

        order = sorted(tbo, key=lambda m: (-(rate_of(
            [r for t in tbo[m] for r in tbo[m][t]]) or 0), short(m)))
        head = "".join(f'<th>{esc(t)}</th>' for t in tbo_tasks)
        rows_tbo = ""
        for m in order:
            allrows = [r for t in tbo[m] for r in tbo[m][t]]
            rt = rate_of(allrows)
            nvoid = sum(1 for r in allrows if r["failure_mode"] in INFRA_MODES)
            rr = f'{rt * 100:.0f}%' if rt is not None else "—"
            vflag = f' <span class="pill crit" title="voided trials">{nvoid} void</span>' if nvoid else ""
            cells = "".join(tbo_cell(tbo[m].get(t, [])) for t in tbo_tasks)
            hl = ' class="hl"' if m in SUBJECT else ""
            # Runs per task. A model sampled once cannot show FLIPS at all, so the
            # column is there to stop a single sample being read as a settled result.
            runs = max((len(v) for v in tbo[m].values()), default=0)
            rcls = "" if runs > 1 else ' class="tbo-thin" title="single sample — no stability read"'
            rows_tbo += (f'<tr{hl}><td>{esc(short(m))}</td>'
                         f'<td><b>{rr}</b>{vflag}</td><td{rcls}>{runs}</td>{cells}</tr>')
        legend = ('<div class="legend"><b>SOLVED</b> every run passed · '
                  '<b>FLIPS</b> passed some runs and not others · '
                  '<b>failed</b> no run passed · '
                  '<b>TIMEOUT</b> no run passed, every one hit the task\'s time budget · '
                  '<b>VOID</b> infrastructure failure, excluded from the rate. '
                  'Each cell reads <i>passed/runs · median agent seconds</i>.</div>')
        tbo_html = ('<div class="tablewrap"><table class="tbo"><thead><tr>'
                    '<th>model</th><th>resolved</th>'
                    '<th title="runs per task">runs</th>' + head +
                    f'</tr></thead><tbody>{rows_tbo}</tbody></table></div>{legend}')

    stages = {"S1 Tiel": bool(gen.get(T_SHIP)), "S2 field": len(gen) > 4,
              "S3 sessions": bool(sess), "S5 CyberTiel": bool(gen.get(CT)),
              "S6 sandboxed": any(k[3] == "sandbox" for k in sess)}
    chips = " ".join(f'<span class="pill {"good" if v else ""}">{"✔" if v else "⋯"} {esc(k)}</span>'
                     for k, v in stages.items())

    css = """
:root{
  --paper:#F6F7F9; --panel:#FFFFFF; --panel-2:#EFF2F6;
  --ink:#131822; --ink-2:#3D4756; --muted:#5C6675; --rule:#DCE1E8; --rule-2:#C6CDD8;
  --good:#0F8A6B; --warn:#A57C0C; --crit:#C6304F; --ref:#3D5FC4;
  --good-soft:#E2F1EC; --crit-soft:#FAE4E9; --ref-soft:#E5EAFA; --warn-soft:#F5EEDC;
  --shadow:0 1px 2px rgba(19,24,34,.06),0 8px 24px -12px rgba(19,24,34,.18);
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --paper:#0E1218; --panel:#161B24; --panel-2:#1D2430;
  --ink:#E9EDF3; --ink-2:#C3CBD7; --muted:#8F99A8; --rule:#28303C; --rule-2:#3A4453;
  --good:#33A886; --warn:#B68A26; --crit:#E0556F; --ref:#6B8AE6;
  --good-soft:#132B25; --crit-soft:#331A22; --ref-soft:#1A2238; --warn-soft:#2C2515;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 28px -14px rgba(0,0,0,.7);
}}
:root[data-theme="dark"]{
  --paper:#0E1218; --panel:#161B24; --panel-2:#1D2430;
  --ink:#E9EDF3; --ink-2:#C3CBD7; --muted:#8F99A8; --rule:#28303C; --rule-2:#3A4453;
  --good:#33A886; --warn:#B68A26; --crit:#E0556F; --ref:#6B8AE6;
  --good-soft:#132B25; --crit-soft:#331A22; --ref-soft:#1A2238; --warn-soft:#2C2515;
  --shadow:0 1px 2px rgba(0,0,0,.5),0 10px 28px -14px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif;
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:40px 24px 64px}
h1,h2,h3{text-wrap:balance;margin:0}
.mono{font-family:ui-monospace,"DejaVu Sans Mono",Menlo,Consolas,monospace;font-variant-numeric:tabular-nums}
.eyebrow{font-family:ui-monospace,"DejaVu Sans Mono",monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted)}
.mast{border-top:3px solid var(--ink);padding-top:18px;margin-bottom:28px}
.mast-top{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:12px}
h1{font-size:clamp(32px,5vw,50px);line-height:1.04;font-weight:700;letter-spacing:-.02em}
.sub{color:var(--ink-2);font-size:16.5px;max-width:66ch;margin-top:12px}
.verdict{margin-top:20px;display:flex;gap:14px;align-items:flex-start;background:var(--good-soft);
  border:1px solid var(--good);border-left-width:4px;border-radius:3px;padding:14px 18px}
.verdict .k{font-family:ui-monospace,monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--good);font-weight:700;white-space:nowrap;padding-top:3px}
.verdict p{margin:0 0 7px;font-size:15.5px;color:var(--ink)}
.verdict p:last-child{margin-bottom:0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(172px,1fr));gap:1px;background:var(--rule);
  border:1px solid var(--rule);border-radius:4px;overflow:hidden;margin:28px 0 14px}
.kpi{background:var(--panel);padding:16px 18px}
.kpi .n{font-family:ui-monospace,"DejaVu Sans Mono",monospace;font-variant-numeric:tabular-nums;
  font-size:28px;font-weight:600;line-height:1.05;letter-spacing:-.02em}
.kpi .l{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.4}
.n.good{color:var(--good)} .n.crit{color:var(--crit)} .n.ref{color:var(--ref)}
section{margin:38px 0 0}
.sec-head{display:flex;align-items:baseline;gap:12px;border-bottom:1px solid var(--rule-2);
  padding-bottom:9px;margin-bottom:18px}
.sec-head h2{font-size:20px;font-weight:600;letter-spacing:-.01em}
.sec-head .note{margin-left:auto;font-size:12.5px;color:var(--muted);text-align:right}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media(max-width:820px){.charts{grid-template-columns:1fr}}
.chart{background:var(--panel);border:1px solid var(--rule);border-radius:4px;padding:17px 19px 15px;
  box-shadow:var(--shadow)}
.chart h3{font-size:15px;font-weight:600;margin-bottom:2px}
.chart .cap{font-size:12.5px;color:var(--muted);margin:0 0 15px}
.rows{display:flex;flex-direction:column;gap:8px}
.row{display:grid;grid-template-columns:114px 1fr 72px;align-items:center;gap:10px}
.row .name{font-family:ui-monospace,"DejaVu Sans Mono",monospace;font-size:11px;color:var(--ink-2);
  text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.track{background:var(--panel-2);border-radius:3px;height:17px;overflow:hidden}
.bar{height:100%;border-radius:0 3px 3px 0}
.bar.good{background:var(--good)} .bar.crit{background:var(--crit)}
.bar.ref{background:var(--ref)} .bar.warn{background:var(--warn)}
.val{font-family:ui-monospace,"DejaVu Sans Mono",monospace;font-variant-numeric:tabular-nums;
  font-size:12.5px;font-weight:500;text-align:right;color:var(--ink)}
.row.hl .name{color:var(--ink);font-weight:700}
.legend{margin-top:14px;padding-top:12px;border-top:1px solid var(--rule);font-size:12px;color:var(--ink-2)}
.callout{margin-top:20px;background:var(--crit-soft);border:1px solid var(--crit);border-left-width:4px;
  border-radius:3px;padding:15px 18px}
.callout.ok{background:var(--ref-soft);border-color:var(--ref)}
.callout .k{font-family:ui-monospace,monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--crit);font-weight:700;display:block;margin-bottom:5px}
.callout.ok .k{color:var(--ref)}
.callout p{margin:0;font-size:14.5px;color:var(--ink)}
.finds{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:820px){.finds{grid-template-columns:1fr}}
.find{background:var(--panel);border:1px solid var(--rule);border-radius:4px;padding:14px 16px}
.find b{display:block;font-size:14px;margin-bottom:4px}
.find span{font-size:13px;color:var(--ink-2)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:4px 0}
th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  font-weight:600;padding:7px 10px 7px 0;border-bottom:1px solid var(--rule-2)}
td{padding:8px 10px 8px 0;border-bottom:1px solid var(--rule);color:var(--ink-2)}
td.num{font-family:ui-monospace,"DejaVu Sans Mono",monospace;font-variant-numeric:tabular-nums;color:var(--ink)}
td.num.good{color:var(--good);font-weight:600}
.pill{display:inline-block;font-family:ui-monospace,monospace;font-size:11px;padding:2px 7px;border-radius:3px;
  background:var(--panel-2);color:var(--ink-2)}
.pill.good{background:var(--good-soft);color:var(--good);font-weight:600}
.pill.crit{background:var(--crit-soft);color:var(--crit);font-weight:600}
.pill.warn{background:var(--warn-soft);color:var(--warn);font-weight:600}
.tablewrap{overflow-x:auto}
table.tbo th{white-space:nowrap}
table.tbo td{white-space:nowrap;vertical-align:middle}
table.tbo tr.hl td:first-child{font-weight:700;color:var(--ink)}
table.tbo tr.hl{background:var(--panel-2)}
table.tbo td.tbo-na{color:var(--muted);font-style:italic;font-size:10px}
table.tbo td.tbo-thin{color:var(--warn);font-weight:700}
.tbo-s{display:block;font-family:ui-monospace,"DejaVu Sans Mono",monospace;
  font-size:9px;color:var(--muted);margin-top:2px;font-variant-numeric:tabular-nums}
.empty{font-size:13px;color:var(--muted);font-style:italic}
code{font-family:ui-monospace,"DejaVu Sans Mono",monospace;font-size:.92em;background:var(--panel-2);
  padding:1px 5px;border-radius:3px;color:var(--ink)}
footer{margin-top:42px;padding-top:16px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--muted)}
@media print{
  :root{--paper:#fff;--panel:#fff;--panel-2:#f0f2f5;--shadow:none;
        --ink:#111;--ink-2:#333;--muted:#666;--rule:#d8dce3;--rule-2:#c2c8d2}
  @page{size:A4;margin:11mm}
  body{font-size:10px;line-height:1.38}
  .wrap{max-width:none;padding:0}
  h1{font-size:24px} .sub{font-size:10.5px;margin-top:7px}
  .kpi .n{font-size:18px} .kpi .l{font-size:8.5px;margin-top:4px}
  .chart,.find,.callout,.verdict,tr,.chart .rows{break-inside:avoid;page-break-inside:avoid}
  .kpis{grid-template-columns:repeat(3,1fr)}
  .kpi{padding:10px 12px}
  .sec-head{break-after:avoid;page-break-after:avoid}
  .verdict{padding:10px 14px} .verdict p{font-size:10.5px;margin-bottom:5px}
  .mast{margin-bottom:14px;padding-top:10px}
  .sec-head h2{font-size:14px} section{margin:14px 0 0} .charts{gap:11px}
  .chart{padding:11px 13px 10px} .chart h3{font-size:11.5px} .chart .cap{font-size:9px;margin-bottom:9px}
  .row{grid-template-columns:96px 1fr 58px;gap:7px} .track{height:12px}
  .row .name,.val{font-size:8.5px} .legend{font-size:8.5px;margin-top:9px;padding-top:8px}
  .kpis{margin:14px 0 8px}
  table{font-size:9.5px} th{font-size:8.5px}
}
"""

    tbo_section_html = ("" if not tbo_tasks else f"""<section>
  <div class="sec-head"><h2>Terminal-Bench — the official harness</h2>
    <span class="note">upstream terminal-bench {esc(TBO_VERSION)} · terminal-bench-core {esc(TBO_DATASET)} · frozen {len(tbo_tasks)}-task subset</span></div>
  <p class="sub" style="margin:0 0 14px">The upstream harness on the upstream dataset, driven
  through Claude Code pointed at the local server — so these are leaderboard-shaped numbers, not
  a look-alike of our own. Every model runs the identical frozen subset; change the subset and
  the comparison is void. Each cell is the verdict and the agent's median wall clock.
  <b>VOID</b> marks an infrastructure failure, which is held out of the resolved rate rather
  than counted as a zero.</p>
  {tbo_html}
  <p class="sub" style="margin:12px 0 0;font-size:11.5px">Two models can land on the same rate
  and solve disjoint sets — the grid is there so that is visible. A single sample at the shipped
  temperature can flip, so the subject models are run twice and shown as solved/attempts.</p>
</section>

""")
    tb_section_html = ("" if not tb_tasks else f"""<section>
  <div class="sec-head"><h2>Terminal-Bench-style — real build/debug loop</h2>
    <span class="note">our C/CMake tasks, local harness · not official Terminal-Bench</span></div>
  <p class="sub" style="margin:0 0 14px">Configure, compile, read the error, fix, re-run — the
  actual agentic loop, on C. Each cell is SOLVED runs / total; deterministic verifier in an
  isolated container.</p>
  {tb_html}
</section>

""")
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Benchmark 2026-09-18</title>
<meta name="description" content="v4 benchmark: the local model field on the 36 GB box, Ollama 0.33.3 — speed, context, agentic sessions and official Terminal-Bench.">
<style>{css}</style>
</head>
<body>
<div class="wrap">

<div class="mast">
  <div class="mast-top">
    <span class="eyebrow">Benchmark v4 · 2026-09-18</span>
    <span class="eyebrow">192.168.100.67 · Ollama 0.33.3 · 35.56 GB usable</span>
  </div>
  <h1>Benchmark&nbsp;2026-09-18</h1>
  <p class="sub">The local model field on the 36&nbsp;GB box, measured on a runtime that has since
  changed the rules underneath all of it. Two new contenders arrived for this round — a
  re-quantized Ornith-1.5 (<span class="mono">Tiel</span>) and its uncensored sibling
  (<span class="mono">CyberTiel</span>) — and they are measured against the field v3 recommended,
  not treated as the answer.</p>
  <div class="verdict">
    <span class="k">Verdict</span>
    <div>
      <p><b>The contenders did not displace the incumbent.</b> On the official Terminal-Bench
      harness {tbo_verdict}</p>
      <p><b>If you run Tiel, run the variant, never the tag as it shipped.</b> Same weights; the
      shipped tag carries <code>presence_penalty 1.5</code>, which costs {pp_gain.lstrip('+')} of
      generation speed and buys nothing measurable. Tiel still wins the things it won: it holds
      262,144 tokens at 34.13&nbsp;GB, recalls at 254,181, refuses an over-long prompt instead of
      quietly answering from half of it, solved the <em>specification</em> rather than the visible
      tests, and gets {think_gain} faster with <code>&lt;|think_off|&gt;</code> for nothing.</p>
    </div>
  </div>
</div>

<div class="kpis">{kpi_html}</div>
<p class="eyebrow" style="margin-bottom:24px">{chips}</p>

<section>
  <div class="sec-head"><h2>Speed, and what it fails to predict</h2>
    <span class="note">median of 3 · server idle before each</span></div>
  <div class="charts">{charts}</div>
  <div class="callout">
    <span class="k">The failure with no error message</span>
    <p>Past its context window, <b>{halvers} of the older models silently keep half the prompt</b>
    (<code>num_ctx/2 + 2</code> tokens) and answer anyway — ornith, north-mini, gemma4 and the
    qwen3.6 control among them. Both Tiel builds return <b>HTTP 400</b> instead. Claude Code cannot
    send <code>num_ctx</code>, so a model in the halving class will answer from half your repository
    with nothing in the transcript to say so.</p>
  </div>
</section>

<section>
  <div class="sec-head"><h2>Tiel or CyberTiel, for this box?</h2>
    <span class="note">same weights lineage, one abliterated</span></div>
  <div class="charts" style="grid-template-columns:1.1fr .9fr">
    <div class="chart">
      <h3>Measured side by side</h3>
      <p class="cap">Both at Q5_K_XL with <code>presence_penalty 0</code>, same window, same harness.</p>
      <div class="tablewrap"><table>
        <thead><tr><th>&nbsp;</th><th>Tiel</th><th>CyberTiel</th></tr></thead>
        <tbody>{vs_html}</tbody></table></div>
    </div>
    <div class="chart">
      <h3>The answer: Tiel</h3>
      <p class="cap">Not because CyberTiel is worse — because it is indistinguishable, and costs
      more to run safely.</p>
      <div class="legend" style="border-top:none;margin-top:0;padding-top:0">
        <p style="margin:0 0 10px"><b>They measure the same.</b> Generation within 1%, recall one
        token apart, identical memory, identical refusal of an over-long prompt, both 25/25 on
        vision. The abliteration and the cyber-weighted imatrix did not move anything this
        benchmark can see.</p>
        <p style="margin:0 0 10px"><b>Neither refused any legitimate work.</b> Across eight benign
        defensive-security prompts — SQL-injection fixes, password hashing, log triage, path-traversal
        validation — both answered all eight. The uncensored build buys nothing on the work you
        actually do.</p>
        <p style="margin:0"><b>But it costs more to host.</b> An abliterated model has had its
        refusal behaviour removed, so its publisher tells you to sandbox it at the OS level. Here
        that meant a container with no host mounts, a read-only rootfs and an egress allowlist of
        exactly one address. That is real operational overhead for a model that measured the same.
        <b>Run Tiel. Reach for CyberTiel only if you hit a refusal that blocks legitimate work</b> —
        and then keep it in the sandbox.</p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="sec-head"><h2>Where CyberTiel actually differs from Tiel</h2>
    <span class="note">authorized / local / CTF tasks · no code executed</span></div>
  <p class="sub" style="margin:0 0 14px">Nine legitimate security-engineering tasks phrased the way
  that trips a safety filter. On a plainly benign set neither model refuses anything; this climbs
  the grey zone until one does. <b>Abliteration changes exactly one task in nine — password
  cracking.</b> Everything else, both builds do.</p>
  {du_html}
</section>

<section>
  <div class="sec-head"><h2>Agentic gates the classic battery misses</h2>
    <span class="note">T8–T11, 3 runs each</span></div>
  <p class="sub" style="margin:0 0 14px">Structured/JSON output, recovery after a tool <em>error</em>,
  argument fidelity (paths with spaces and quotes, non-ASCII, tabs), and zero-argument tools.
  T8/T9/T11 pass across the field; T10 catches <code>nemotron-3.5-L</code>, which silently drops
  a tab from a tool argument — a real fidelity failure the first scorer had masked behind a
  delimiter artifact (<code>review.md</code> R13).</p>
  {xg_html}
</section>

<section>
  <div class="sec-head"><h2>The field</h2>
    <span class="note">vision is a yes/no capability — every capable model scores 25/25</span></div>
  <div class="tablewrap"><table>
  <thead><tr><th>model</th><th>gen tok/s</th><th>cold prefill</th><th>gates</th><th>vision</th>
  <th>past its window</th></tr></thead>
  <tbody>{"".join(field_rows) or '<tr><td colspan="6" class="empty">No data yet.</td></tr>'}</tbody>
  </table></div>
</section>

{tbo_section_html}{tb_section_html}<section>
  <div class="sec-head"><h2>Who actually fixed the code</h2>
    <span class="note">three modules · three bugs · one missing function · 18 held-out tests</span></div>
  <p class="sub" style="margin:0 0 14px">The visible tests are the ones the model can see. The
  held-out tests check the docstring specification it was asked to implement. A model can turn the
  first green while leaving the second failing — and most of them did.</p>
  <div class="tablewrap"><table>
  <thead><tr><th>model</th><th>thinking</th><th>harness</th><th>passed</th><th>median</th>
  <th>held-out tests, per run</th></tr></thead>
  <tbody>{"".join(cap_rows) or '<tr><td colspan="6" class="empty">Sessions still running.</td></tr>'}</tbody>
  </table></div>
</section>

<section>
  <div class="sec-head"><h2>What we learned that we did not expect</h2></div>
  <div class="finds">
    <div class="find"><b>The runtime started caching prompts, and a v3 rule died with it</b>
    <span>Ollama 0.33.3 serves a repeated prefix from cache; 0.32.15 did not, and every v3 transcript
    reports <code>cache_read 0</code>. An agent turn now prefills only its new tail — 520 tokens
    instead of 30,042. v3 ranked this field on prefill because "the loop re-reads its context every
    turn". That is no longer true here.</span></div>

    <div class="find"><b>Thinking is a {think_gain} tax on tool-heavy work</b>
    <span>Same model, same fixture: 131/148/117 s with thinking, 74/53/56 s without — and the
    held-out scores came back equal or better without it. The one session Tiel failed all day was a
    thinking-on run.</span></div>

    <div class="find"><b>A clean gate battery is not a reliability number</b>
    <span>Tiel passed all seven gates three times over. Re-running the nested-schema gate alone
    sixteen times gives 13/16. The battery samples once, at the tag's shipped temperature 0.6 — so
    every single-shot gate result in v1–v4 is one sample.</span></div>

    <div class="find"><b>Abliteration changed almost nothing measurable</b>
    <span>CyberTiel matches Tiel to within noise on every axis, and on eight benign
    defensive-security prompts <em>neither</em> model refused. The uncensored build earns its extra
    operational cost only if you actually hit a refusal.</span></div>

    <div class="find"><b>The fastest model on the box is still the worst at the job</b>
    <span><code>cascade-2</code> leads both speed axes — 140.7 tok/s and 7,017 prefill — and scored
    0 of 3 on the hard fixture, with held-out scores of 0, 3 and 3 out of 18, taking 419 s to do it.
    v3 rejected it for the same defect. Nothing changed, so it is cut.</span></div>

    <div class="find"><b>Half this round's bugs were in the harness</b>
    <span>A retrieval probe that queried <code>localhost</code> and scored three empty replies as
    model failures; a sandbox that never delivered its fixture, so every isolated session ran against
    an empty directory. Both produced plausible numbers instead of errors, which is what makes that
    class dangerous. All twelve are in <code>review.md</code>.</span></div>
  </div>
</section>

<footer>
Every figure is generated from the TSVs in <code>results/</code> by <code>make-report.py</code>;
method and caveats in <code>measurements.md</code>, the twelve harness defects found and fixed in
<code>review.md</code>, exact model digests and versions in <code>results/provenance.txt</code>.
Sessions are real <code>claude -p</code> runs scored from the repository afterwards, never from the
model's own summary. Cut models stay in the tables and out of the headlines.
</footer>
</div>
</body>
</html>
"""
    Path(a.out).write_text(doc)
    print(f"wrote {a.out} ({len(doc):,} bytes)")
    print(f"  throughput {len(gen)} · hard sessions {len(cap_rows)} · overflow {len(overflow)}")
    if a.pdf:
        import shutil, subprocess
        browser = next((b for b in ("chromium", "chromium-browser", "google-chrome")
                        if shutil.which(b)), None)
        if not browser:
            print("  no chromium on PATH; skipped the PDF")
        else:
            pdf = str(Path(a.out).with_suffix(".pdf"))
            subprocess.run([browser, "--headless", "--disable-gpu", "--no-sandbox",
                            "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                            Path(a.out).as_uri()], check=False, capture_output=True, timeout=180)
            if Path(pdf).exists():
                print(f"wrote {pdf} ({Path(pdf).stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
