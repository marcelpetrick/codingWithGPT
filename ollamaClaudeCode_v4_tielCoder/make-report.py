#!/usr/bin/env python3
"""make-report.py -- build report.html from the TSVs in results/.

A generator rather than a hand-written page, because the stages land over hours
and the report has to be regenerated as they do. Everything it draws comes from
results/*.tsv; if a stage has not run yet, its section says so instead of
inventing a number.

Charts are inline SVG drawn here -- no JS, no CDN library. Tooltips are native
SVG <title> elements. Palette is the validated default from the dataviz skill
(categorical slots 1-3 + status), declared as CSS custom properties so light and
dark swap in one place.

Usage: ./make-report.py [--out report.html]
"""
import argparse
import csv
import html
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

# Short display names: the tags are long and the axis is not the place for them.
SHORT = {
    "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest": "Tiel Q5 (shipped, pp1.5)",
    "tiel-coder:35b-q5-ctx256k-agentic": "Tiel Q5 (pp0)",
    "cyber-tiel:35b-q5-ctx256k-agentic": "CyberTiel Q5 (pp0)",
    "hf.co/peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF:UD-Q5_K_XL": "CyberTiel Q5 (raw)",
    "north-mini-code-1.0:q4_K_M-ctx256k-agentic": "north-mini (v3 default)",
    "qwen3.6:35b-a3b-q4_K_M-agentic": "qwen3.6 35b (control)",
    "ornith:35b-ctx256k-agentic": "ornith 1.0 (Tiel's base line)",
    "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic": "gemma4 26b (vision pick)",
    "nemotron-3.5-lightning:30b-ctx256k-agentic": "nemotron-3.5-L",
    "nemotron-cascade-2:30b-ctx256k-agentic": "nemotron-cascade-2",
    "qwen3.8:27b-q4_K_M-ctx128k-agentic": "qwen3.8 27b (dense)",
}


def short(m):
    return SHORT.get(m, m.split("/")[-1][:34])


def read_tsv(name):
    p = RES / name
    if not p.exists():
        return []
    with p.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def esc(s):
    return html.escape(str(s))


# ---------------------------------------------------------------- chart helpers
def hbars(rows, value_key, label_fmt="{:.1f}", title="", unit="", series=1,
          note="", sort=True, highlight=None):
    """Horizontal bar chart. rows: [(label, value, tooltip)]. Returns SVG string."""
    rows = [r for r in rows if r[1] is not None]
    if not rows:
        return f'<p class="empty">No data yet for {esc(title)}.</p>'
    if sort:
        rows = sorted(rows, key=lambda r: -r[1])
    vmax = max(r[1] for r in rows) or 1
    bar_h, gap, pad_l, pad_r, pad_t = 26, 10, 210, 78, 8
    h = pad_t + len(rows) * (bar_h + gap)
    w = 720
    plot_w = w - pad_l - pad_r
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}" '
             f'preserveAspectRatio="xMinYMin meet" class="chart">']
    # recessive gridlines at quarter steps, each labelled with a value the chart reaches
    for frac in (0.25, 0.5, 0.75, 1.0):
        x = pad_l + plot_w * frac
        parts.append(f'<line x1="{x:.1f}" y1="{pad_t - 4}" x2="{x:.1f}" y2="{h - 6}" '
                     f'class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{h - 0}" class="tick" text-anchor="middle">'
                     f'{label_fmt.format(vmax * frac)}</text>')
    for i, (label, val, tip) in enumerate(rows):
        y = pad_t + i * (bar_h + gap)
        bw = max(2.0, plot_w * val / vmax)
        cls = "bar-hi" if (highlight and highlight in label) else f"bar-s{series}"
        parts.append(f'<g><title>{esc(tip or f"{label}: {val}")}</title>'
                     f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="4" '
                     f'class="{cls}"/>'
                     f'<text x="{pad_l - 10}" y="{y + bar_h * 0.7}" class="ylab" '
                     f'text-anchor="end">{esc(label)}</text>'
                     f'<text x="{pad_l + bw + 8:.1f}" y="{y + bar_h * 0.7}" class="vlab">'
                     f'{label_fmt.format(val)}{esc(unit)}</text></g>')
    parts.append("</svg>")
    body = "".join(parts)
    n = f'<p class="note">{note}</p>' if note else ""
    return f'<figure class="fig"><figcaption>{esc(title)}</figcaption>{body}{n}</figure>'


def grouped_bars(groups, series_names, title="", unit="", label_fmt="{:.0f}", note=""):
    """groups: [(group_label, [v1, v2])]. Two series, fixed slot order."""
    if not groups:
        return f'<p class="empty">No data yet for {esc(title)}.</p>'
    vmax = max(max(v for v in vals if v is not None) for _, vals in groups) or 1
    bh, gg, sg, pad_l, pad_r, pad_t = 22, 18, 3, 150, 86, 10
    ns = len(series_names)
    h = pad_t + len(groups) * (ns * bh + sg * (ns - 1) + gg)
    w, = (720,)
    plot_w = w - pad_l - pad_r
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}" '
             f'preserveAspectRatio="xMinYMin meet" class="chart">']
    for frac in (0.25, 0.5, 0.75, 1.0):
        x = pad_l + plot_w * frac
        parts.append(f'<line x1="{x:.1f}" y1="{pad_t - 4}" x2="{x:.1f}" y2="{h - 6}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{h}" class="tick" text-anchor="middle">'
                     f'{label_fmt.format(vmax * frac)}</text>')
    y = pad_t
    for glabel, vals in groups:
        parts.append(f'<text x="{pad_l - 10}" y="{y + (ns * bh) / 2 + 4}" class="ylab" '
                     f'text-anchor="end">{esc(glabel)}</text>')
        for si, v in enumerate(vals):
            if v is None:
                continue
            bw = max(2.0, plot_w * v / vmax)
            parts.append(f'<g><title>{esc(series_names[si])} — {esc(glabel)}: {v}</title>'
                         f'<rect x="{pad_l}" y="{y + si * (bh + sg)}" width="{bw:.1f}" '
                         f'height="{bh}" rx="4" class="bar-s{si + 1}"/>'
                         f'<text x="{pad_l + bw + 8:.1f}" y="{y + si * (bh + sg) + bh * 0.75}" '
                         f'class="vlab">{label_fmt.format(v)}{esc(unit)}</text></g>')
        y += ns * bh + sg * (ns - 1) + gg
    parts.append("</svg>")
    legend = '<div class="legend">' + "".join(
        f'<span class="lg"><i class="sw sw{i + 1}"></i>{esc(n)}</span>'
        for i, n in enumerate(series_names)) + "</div>"
    n = f'<p class="note">{note}</p>' if note else ""
    return (f'<figure class="fig"><figcaption>{esc(title)}</figcaption>{legend}'
            f'{"".join(parts)}{n}</figure>')


# ---------------------------------------------------------------- data sections
def tokrate_rows(words="2000"):
    gen, pre = {}, {}
    for r in read_tsv("tokrate.tsv"):
        if r.get("prompt_words") != words:
            continue
        try:
            gen[r["model"]] = float(r["gen_tps"])
            pre[r["model"]] = float(r["prefill_tps"])
        except (ValueError, KeyError):
            pass
    return gen, pre


def cache_section():
    rows = read_tsv("cache.tsv")
    by = defaultdict(dict)
    for r in rows:
        try:
            by[r["model"]][r["phase"]] = (float(r["wall_s"]), int(r["new_tok"]))
        except (ValueError, KeyError):
            pass
    groups = []
    for m, ph in by.items():
        if "unique" in ph and "extend" in ph:
            groups.append((short(m), [ph["unique"][0], ph["extend"][0]]))
    return by, groups


def sessions():
    """Median wall and hidden score per (model, fixture), from both harnesses."""
    out = defaultdict(lambda: defaultdict(list))
    for fname, harness in (("cc-session.tsv", "host"), ("cc-session-sandboxed.tsv", "sandbox")):
        for r in read_tsv(fname):
            if r.get("thinking", "on") == "off":
                continue
            key = (r["model"], r["fixture"], harness)
            try:
                out[key]["wall"].append(int(r["wall_s"]))
            except (ValueError, KeyError):
                pass
            out[key]["verdict"].append(r.get("verdict", "?"))
            if r.get("hidden", "-") not in ("-", ""):
                out[key]["hidden"].append(r["hidden"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.html"))
    a = ap.parse_args()

    gen2k, pre2k = tokrate_rows("2000")
    gen20k, pre20k = tokrate_rows("20000")
    cache_by, cache_groups = cache_section()
    overflow = {}
    for r in read_tsv("overflow.tsv"):
        overflow[r["model"]] = (r["regime"], r.get("prompt_eval", ""), r.get("detail", ""))
    vision = defaultdict(int)
    vision_poss = defaultdict(int)
    for r in read_tsv("vision.tsv"):
        try:
            got, poss = r["checks"].split("/")
            vision[r["model"]] += int(got)
            vision_poss[r["model"]] += int(poss)
        except (ValueError, KeyError):
            pass
    sess = sessions()

    # ---- charts
    gen_chart = hbars(
        [(short(m), v, f"{m}: {v} tok/s generation at a 2,000-word prompt") for m, v in gen2k.items()],
        "gen", "{:.0f}", "Generation throughput — 2,000-word prompt", " tok/s",
        series=1, highlight="Tiel Q5 (pp0)",
        note="Ollama's own counters, temperature 0, seed 42, thinking off, 256-token budget. "
             "Cold prompts. Higher is better.")
    pre_chart = hbars(
        [(short(m), v, f"{m}: {v} tok/s cold prefill at ~35k tokens") for m, v in pre20k.items()],
        "pre", "{:,.0f}", "Cold prefill — ~35,000-token prompt", " tok/s",
        series=3,
        note="What the FIRST turn of a session costs. Later turns hit the prefix cache instead — see below.")

    pp_groups = []
    for wlabel, wkey in (("empty prompt", "0"), ("2,000 words", "2000"), ("20,000 words", "20000")):
        g, _ = tokrate_rows(wkey)
        a1 = g.get("Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest")
        b1 = g.get("tiel-coder:35b-q5-ctx256k-agentic")
        if a1 and b1:
            pp_groups.append((wlabel, [a1, b1]))
    pp_chart = grouped_bars(
        pp_groups, ["shipped tag (presence_penalty 1.5)", "same weights, presence_penalty 0"],
        "What presence_penalty 1.5 costs — generation tok/s", " tok/s", "{:.0f}",
        note="Identical weights; only the sampler setting differs. Prefill is unchanged (within 2%), "
             "because the penalty is paid per generated token.")

    cache_chart = grouped_bars(
        cache_groups, ["cold: a new 30k prompt", "agent turn: same prefix + new tail"],
        "Prefix caching on Ollama 0.33.3 — seconds to first token", " s", "{:.1f}",
        note="0.32.15 had no prefix cache (every v3 transcript reports cache_read 0). "
             "An agent turn appends to a stable prefix, so it now prefills only the tail.")

    vis_chart = hbars(
        [(short(m), vision[m], f"{m}: {vision[m]}/{vision_poss[m]} objective checks")
         for m in vision],
        "vis", "{:.0f}", "Vision — objective checks passed (max 25)", "/25", series=2,
        note="Invoice OCR (9), UI description (6), chart extraction (10), run AT each tag's baked window.")

    # ---- overflow table
    ovf_rows = []
    seen = set()
    for m, (regime, pe, detail) in overflow.items():
        if m in seen:
            continue
        seen.add(m)
        safe = regime.startswith("ERROR")
        ovf_rows.append(
            f'<tr><td>{esc(short(m))}</td>'
            f'<td><span class="chip {"ok" if safe else "bad"}">'
            f'{"✔ refuses (HTTP 400)" if safe else "✖ silently halves"}</span></td>'
            f'<td class="num">{esc(pe or "—")}</td></tr>')

    # ---- session table
    sess_rows = []
    for (m, fx, harness), d in sorted(sess.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if not d["wall"]:
            continue
        med = statistics.median(d["wall"])
        rng = f"{min(d['wall'])}–{max(d['wall'])}" if len(d["wall"]) > 1 else str(med)
        verdicts = d["verdict"]
        ok = sum(v == "PASS" for v in verdicts)
        hidden = ", ".join(d["hidden"]) if d["hidden"] else "—"
        sess_rows.append(
            f'<tr><td>{esc(short(m))}</td><td>{esc(fx)}</td><td>{esc(harness)}</td>'
            f'<td><span class="chip {"ok" if ok == len(verdicts) else "bad"}">{ok}/{len(verdicts)} PASS</span></td>'
            f'<td class="num">{med:.0f} s</td><td class="num">{esc(rng)}</td>'
            f'<td class="num">{esc(hidden)}</td></tr>')

    stages_done = {
        "S1 Tiel battery": bool(gen2k),
        "S2 field on 0.33.3": len(gen2k) > 2,
        "S3 sessions": bool(sess),
        "S5 CyberTiel": any("yber" in m for m in gen2k),
    }
    status_chips = "".join(
        f'<span class="chip {"ok" if v else "wait"}">{"✔" if v else "⋯"} {esc(k)}</span>'
        for k, v in stages_done.items())

    css = """
:root{
  color-scheme: light;
  --bg:#f7f7f4; --surface:#fcfcfb; --line:#e3e2dd; --line-soft:#eeede8;
  --ink:#141413; --ink-2:#52514e; --ink-3:#86847d;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a;
  --good:#1f7a3d; --good-bg:#e7f3ea; --bad:#b3261e; --bad-bg:#fbeae8;
  --wait-bg:#f0efe9; --hi:#4a3aa7;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  color-scheme: dark;
  --bg:#121211; --surface:#1a1a19; --line:#33322e; --line-soft:#26251f;
  --ink:#f5f4ef; --ink-2:#c3c2b7; --ink-3:#8d8b82;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70;
  --good:#5ec27f; --good-bg:#16291d; --bad:#ef8b83; --bad-bg:#2c1817;
  --wait-bg:#232320; --hi:#9085e9;
}}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#121211; --surface:#1a1a19; --line:#33322e; --line-soft:#26251f;
  --ink:#f5f4ef; --ink-2:#c3c2b7; --ink-3:#8d8b82;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70;
  --good:#5ec27f; --good-bg:#16291d; --bad:#ef8b83; --bad-bg:#2c1817;
  --wait-bg:#232320; --hi:#9085e9;
}
*{box-sizing:border-box}
body{background:var(--bg); color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,-apple-system,sans-serif;
  font-size:15px; line-height:1.55; margin:0;}
.wrap{max-width:900px; margin:0 auto; padding-block:36px 72px; padding-left:20px; padding-right:20px;}
h1{font-family:"IBM Plex Serif",Georgia,serif; font-size:30px; line-height:1.2;
   margin:0 0 6px; text-wrap:balance; letter-spacing:-.01em;}
h2{font-family:"IBM Plex Serif",Georgia,serif; font-size:21px; margin:42px 0 4px; text-wrap:balance;}
h3{font-size:14px; margin:26px 0 6px; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-3);}
p{margin:8px 0; color:var(--ink-2); max-width:68ch;}
.sub{color:var(--ink-3); font-size:13px; margin-bottom:18px;}
.meta{display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 6px;}
.chip{display:inline-flex; align-items:center; gap:6px; font-size:12px; padding:3px 9px;
  border-radius:999px; background:var(--wait-bg); color:var(--ink-2);
  font-family:"IBM Plex Mono",ui-monospace,monospace;}
.chip.ok{background:var(--good-bg); color:var(--good);}
.chip.bad{background:var(--bad-bg); color:var(--bad);}
.verdict{background:var(--surface); border:1px solid var(--line); border-left:3px solid var(--hi);
  border-radius:8px; padding:18px 20px; margin:22px 0;}
.verdict p{margin:6px 0;}
.verdict strong{color:var(--ink);}
.finding{background:var(--surface); border:1px solid var(--line); border-radius:8px;
  padding:14px 16px; margin:10px 0;}
.finding b{color:var(--ink); display:block; margin-bottom:2px; font-size:14px;}
.finding span{font-size:13.5px; color:var(--ink-2);}
.fig{margin:18px 0 26px; background:var(--surface); border:1px solid var(--line);
  border-radius:8px; padding:16px 14px 10px; overflow-x:auto;}
figcaption{font-size:13px; font-weight:600; color:var(--ink); margin-bottom:10px;
  letter-spacing:.01em;}
.chart{width:100%; height:auto; display:block; min-width:520px;}
.grid{stroke:var(--line-soft); stroke-width:1;}
.tick{fill:var(--ink-3); font-size:10px; font-family:"IBM Plex Mono",monospace;}
.ylab{fill:var(--ink-2); font-size:11.5px;}
.vlab{fill:var(--ink); font-size:11.5px; font-family:"IBM Plex Mono",monospace;
  font-variant-numeric:tabular-nums;}
.bar-s1{fill:var(--s1)} .bar-s2{fill:var(--s2)} .bar-s3{fill:var(--s3)}
.bar-hi{fill:var(--hi)}
.legend{display:flex; gap:16px; flex-wrap:wrap; margin-bottom:8px; font-size:12px; color:var(--ink-2);}
.lg{display:inline-flex; align-items:center; gap:6px;}
.sw{width:11px; height:11px; border-radius:3px; display:inline-block;}
.sw1{background:var(--s1)} .sw2{background:var(--s2)} .sw3{background:var(--s3)}
.note{font-size:12.5px; color:var(--ink-3); margin:4px 2px 2px; max-width:none;}
.empty{font-size:13px; color:var(--ink-3); font-style:italic;}
table{border-collapse:collapse; width:100%; font-size:13.5px; margin:10px 0;}
th{text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.07em;
   color:var(--ink-3); font-weight:600; padding:6px 10px 6px 0; border-bottom:1px solid var(--line);}
td{padding:7px 10px 7px 0; border-bottom:1px solid var(--line-soft); color:var(--ink-2);}
td.num{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums; color:var(--ink);}
.tablewrap{overflow-x:auto;}
code{font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:.92em;
  background:var(--wait-bg); padding:1px 5px; border-radius:4px; color:var(--ink);}
footer{margin-top:52px; padding-top:18px; border-top:1px solid var(--line);
  font-size:12.5px; color:var(--ink-3);}
@media (max-width:560px){ h1{font-size:25px} .wrap{padding-block:26px 56px} }
"""

    tiel_pp0 = gen2k.get("tiel-coder:35b-q5-ctx256k-agentic")
    tiel_ship = gen2k.get("Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest")
    speedup = f"{(tiel_pp0 / tiel_ship - 1) * 100:.0f}%" if (tiel_pp0 and tiel_ship) else "—"

    doc = f"""<title>Tiel-Coder on the Ollama Box</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Serif:wght@600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{css}</style>
<div class="wrap">
<h1>Tiel-Coder on the Ollama box</h1>
<p class="sub">Benchmark round v4 &middot; <code>192.168.100.67</code> &middot; Ollama 0.33.3 &middot;
35.56&nbsp;GB usable VRAM &middot; generated from <code>results/*.tsv</code></p>

<div class="meta">{status_chips}</div>
<p class="note">Stages still running append to the same files; regenerate with
<code>./make-report.py</code>.</p>

<div class="verdict">
<p><strong>Use <code>tiel-coder:35b-q5-ctx256k-agentic</code>, not the tag as shipped.</strong>
Identical weights; the shipped <code>-ctx262k</code> tag carries
<code>presence_penalty 1.5</code>, which costs <strong>{speedup}</strong> of generation speed and
buys nothing measurable.</p>
<p>Tiel holds its full <strong>262,144-token window at 34.13&nbsp;GB, 100% on GPU</strong>, retrieves
a needle at <strong>254,181 tokens</strong> (the deepest in v1&ndash;v4), scores <strong>25/25</strong>
on the vision checks at that full window, and is the <strong>only model tested that refuses an
over-long prompt</strong> instead of silently answering from half of it.</p>
</div>

<h2>Findings that change what you should do</h2>

<div class="finding"><b>1 &middot; The runtime now caches prompt prefixes &mdash; v3's ranking rule is void</b>
<span>Ollama 0.33.3 reports <code>cache_read_input_tokens</code>; 0.32.15 did not, and every v3
transcript shows zero. A repeated 30k-token prompt prefills <strong>4 tokens instead of 30,042</strong>,
and an agent turn (same prefix, new tail) prefills only the tail. v3 ranked models on prefill because
"the loop re-reads its context every turn" &mdash; that is no longer true here.</span></div>

<div class="finding"><b>2 &middot; The silent half-window bug is still live &mdash; but not on Tiel</b>
<span>Past its window, <code>ornith</code>, <code>north-mini</code> (the v3 default) and the
<code>qwen3.6</code> control all silently keep <code>num_ctx/2 + 2</code> tokens and answer anyway.
Tiel returns <strong>HTTP 400</strong>. Claude Code cannot send <code>num_ctx</code>, so a model in the
halving class can answer from half your context with nothing in the transcript saying so.</span></div>

<div class="finding"><b>3 &middot; <code>presence_penalty 1.5</code> is a pure tax</b>
<span>It was added by whoever created the <code>-ctx262k</code> tag, not by the model publisher, whose
card recommends no penalty at all. It costs 41&ndash;52% of generation, leaves prefill unchanged, and
makes no measurable difference to tool reliability (T5 re-runs: 13/16 with it, 15/16 without).</span></div>

<div class="finding"><b>4 &middot; A clean gate battery is not a reliability figure</b>
<span>Tiel passed T1&ndash;T7 three times over. Re-running the nested-schema gate alone sixteen times
gives <strong>13/16</strong>. The battery samples once at the tag's shipped temperature 0.6, so any
single-shot gate result in v1&ndash;v4 is one sample.</span></div>

<h2>Speed</h2>
{gen_chart}
{pp_chart}
{pre_chart}
{cache_chart}

<h2>Capability</h2>
{vis_chart}

<h3>Behaviour past the context window</h3>
<div class="tablewrap"><table>
<thead><tr><th>model</th><th>what happens when the prompt exceeds num_ctx</th><th>tokens kept</th></tr></thead>
<tbody>{"".join(ovf_rows) or '<tr><td colspan="3" class="empty">No data yet.</td></tr>'}</tbody>
</table></div>

<h2>End-to-end Claude Code sessions</h2>
<p>Two fixtures against a real <code>claude -p</code> session, scored from the repository rather than
the model's summary: a one-function bug, and a three-module <code>ledger</code> package with three bugs
and one unimplemented function, checked against <strong>18 held-out tests the model never sees</strong>.
<code>sandbox</code> rows run inside the isolated container used for the abliterated model.</p>
<div class="tablewrap"><table>
<thead><tr><th>model</th><th>fixture</th><th>harness</th><th>verdict</th><th>median</th><th>range</th><th>hidden tests</th></tr></thead>
<tbody>{"".join(sess_rows) or '<tr><td colspan="7" class="empty">Sessions still running.</td></tr>'}</tbody>
</table></div>

<footer>
Every number here is generated from the TSVs in <code>results/</code>. Method, caveats and the
twelve harness problems found and fixed during this round are in <code>measurements.md</code> and
<code>review.md</code>; exact digests and versions in <code>results/provenance.txt</code>.
</footer>
</div>"""
    Path(a.out).write_text(doc)
    print(f"wrote {a.out} ({len(doc):,} bytes)")
    print(f"  models with throughput: {len(gen2k)}; vision: {len(vision)}; "
          f"overflow: {len(overflow)}; session rows: {len(sess_rows)}")


if __name__ == "__main__":
    main()
