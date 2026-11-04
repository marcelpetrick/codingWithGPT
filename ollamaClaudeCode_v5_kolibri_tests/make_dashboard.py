#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate a sortable HTML report from the recorded benchmark results."""

import csv
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
MEASUREMENTS = ROOT / "measurements"
HISTORY = (
    ROOT.parent / "ollamaClaudeCode_v4_tielCoder" / "results" / "cc-session-rb0925.tsv"
)


def read_tsv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def esc(value):
    return html.escape(str(value), quote=True)


def model_name(tag):
    names = (
        ("kolibri1:", "Kolibri 1 · Q3_K_S"),
        ("qwen3.6:35b-a3b-q4_K_M-agentic-t06", "Qwen 3.6 · t0.6"),
        ("qwen3.6:", "Qwen 3.6 · control"),
        ("kat-coder", "KAT-Coder V2.5"),
        ("tiel-coder", "Tiel-Coder 35B"),
        ("gemma4:", "Gemma 4 26B"),
        ("byteshape-", "ByteShape Qwen 3.6"),
    )
    return next((label for prefix, label in names if tag.startswith(prefix)), tag)


def model_cell(tag):
    note = f"Model tag: {tag}. The displayed value applies only to the stated test conditions."
    return f'<td data-sort="{esc(model_name(tag))}">{esc(model_name(tag))} <span class="info" title="{esc(note)}" tabindex="0">i</span></td>'


def text_cell(value, sort=None):
    return f'<td data-sort="{esc(value if sort is None else sort)}">{esc(value)}</td>'


def header(label, note):
    return f'<th tabindex="0">{esc(label)} <span class="info" title="{esc(note)}">i</span><span class="arrow"> ↕</span></th>'


def table(title, description, columns, rows):
    headings = "".join(header(*col) for col in columns)
    return f'<section><div class="section-head"><h2>{esc(title)}</h2><p>{esc(description)}</p></div><div class="scroll"><table><thead><tr>{headings}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'


def speed_table(rows):
    groups = {}
    for row in rows:
        key = (row["model"], int(row["prompt_words"]))
        groups.setdefault(key, []).append(row)
    body = []
    for (model, words), values in sorted(
        groups.items(), key=lambda item: (item[0][1], item[0][0])
    ):
        generation = [float(v["gen_tps"]) for v in values]
        prefill = [float(v["prefill_tps"]) for v in values]
        median = statistics.median(generation)
        body.append(
            "<tr>"
            + model_cell(model)
            + text_cell(f"{words:,}", words)
            + text_cell(len(values))
            + text_cell(f"{median:.2f}", median)
            + text_cell(f"{min(generation):.2f}–{max(generation):.2f}", min(generation))
            + text_cell(
                f"{statistics.median(prefill):,.1f}", statistics.median(prefill)
            )
            + "</tr>"
        )
    columns = [
        ("Model", "The exact tag is shown beside each model."),
        (
            "Prompt words",
            "The v4 filler size in words. The token count differs by tokenizer.",
        ),
        ("Runs", "The number of independent cold samples."),
        ("Generation / s", "Median generated tokens per second. Higher is faster."),
        ("Range / s", "The minimum and maximum generation rates across runs."),
        (
            "Prefill / s",
            "Median prompt tokens per second. Very short prompts are noisy.",
        ),
    ]
    return table(
        "Cold throughput",
        "Same server and session, Ollama 0.40.11. Each sample starts with an unloaded model. The deployed context sizes differ.",
        columns,
        body,
    )


def gate_table(extra, basic, short, stock, adaptive, deep):
    body = []
    for label, rows in (("Stock template", stock), ("Corrected template", short)):
        passed = sum(r["verdict"] == "PASS" for r in rows)
        body.append(
            "<tr>"
            + model_cell(rows[0]["model"])
            + text_cell("T1 · write file")
            + text_cell(label)
            + text_cell(f"{passed}/{len(rows)}", passed)
            + "</tr>"
        )
    if adaptive:
        passed = sum(row["verdict"] == "PASS" for row in adaptive)
        body.append(
            "<tr>"
            + model_cell(adaptive[0]["model"])
            + text_cell("T1 · write file")
            + text_cell("Adaptive thinking")
            + text_cell(f"{passed}/{len(adaptive)}", passed)
            + "</tr>"
        )
    for model, row in deep:
        if row["test"] not in ("T3_multiturn", "T7_tool_at_long_ctx"):
            continue
        count = (
            row["detail"].split("_at_")[0]
            if row["test"].startswith("T7")
            else ("1/1" if row["result"] == "PASS" else "0/1")
        )
        body.append(
            "<tr>"
            + model_cell(model)
            + text_cell(row["test"].replace("_", " · ", 1))
            + text_cell("Long-context run")
            + text_cell(count)
            + "</tr>"
        )
    for row in basic:
        passed, total = row["passes"].split("/")
        body.append(
            "<tr>"
            + model_cell(row["model"])
            + text_cell(row["gate"])
            + text_cell(
                "Corrected" if row["model"].startswith("kolibri1:") else "Control"
            )
            + text_cell(f"{passed}/{total}", int(passed))
            + "</tr>"
        )
    for row in extra:
        body.append(
            "<tr>"
            + model_cell(row["model"])
            + text_cell(row["gate"].replace("_", " · ", 1))
            + text_cell(
                "Corrected" if row["model"].startswith("kolibri1:") else "Control"
            )
            + text_cell(f"{row['pass_n']}/{row['runs']}", int(row["pass_n"]))
            + "</tr>"
        )
    columns = [
        ("Model", "The exact tag is shown beside each model."),
        ("Gate", "The v4 tool or structured-output test."),
        ("Configuration", "The template or control used for this arm."),
        (
            "Passes",
            "Passes divided by trials. Three trials are preliminary; failures need eight reruns.",
        ),
    ]
    return table(
        "Agentic gates",
        "T1 was repeated eight times for both Kolibri templates. The other gates have three trials per model.",
        columns,
        body,
    )


def bilingual_table(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row["model"], row["language"]), []).append(row)
    body = []
    for (model, language), values in sorted(groups.items()):
        passed = sum(row["pass"] for row in values)
        body.append(
            "<tr>"
            + model_cell(model)
            + text_cell(language)
            + text_cell(f"{passed}/{len(values)}", passed)
            + "</tr>"
        )
    columns = [
        ("Model", "The exact tag is shown beside each model."),
        ("Language", "The language used in the arithmetic instruction."),
        ("Exact answers", "Correct exact-number answers out of the completed prompts."),
    ]
    return table(
        "English and German smoke checks",
        "Three simple arithmetic instructions per language. This is not a broad language-quality evaluation.",
        columns,
        body,
    )


def coding_table(rows, corrections):
    body = []
    for row in rows:
        matching = [
            c
            for c in corrections
            if all(c[k] == row[k] for k in ("model", "fixture", "run"))
            and c["recorded_verdict"] == row["verdict"]
        ]
        verdict = (
            matching[0]["corrected_verdict"] + " *" if matching else row["verdict"]
        )
        body.append(
            "<tr>"
            + model_cell(row["model"])
            + text_cell(row["fixture"])
            + text_cell(row["run"])
            + text_cell(verdict)
            + text_cell(row["hidden"])
            + text_cell(row["wall_s"], int(row["wall_s"]))
            + "</tr>"
        )
    columns = [
        ("Model", "The exact tag is shown beside each model."),
        (
            "Fixture",
            "Easy is the basic Python task. Hard is the ledger task with held-out tests.",
        ),
        ("Run", "The independent run number."),
        (
            "Verdict",
            "PASS means visible tests passed and source changed without test changes. An asterisk marks a documented rescore.",
        ),
        (
            "Held-out",
            "Hard-fixture tests passed out of 18. A dash means not applicable.",
        ),
        ("Seconds", "Wall time for the coding session, excluding warm load."),
    ]
    progress = (
        "All twelve sessions are recorded."
        if len(rows) >= 12
        else "Sessions are ongoing."
    )
    return table(
        "Current coding sessions",
        "Ollama 0.40.11, Claude Code 2.1.274, isolated container. "
        + progress
        + " * The first Kolibri verdict was corrected after it committed its fix.",
        columns,
        body,
    )


def history_table(rows):
    groups = {}
    for row in rows:
        if row["fixture"] == "hard" and row["thinking"] == "on":
            groups.setdefault(row["model"], []).append(row)
    body = []
    for model, values in sorted(groups.items()):
        times = [int(v["wall_s"]) for v in values]
        scores = ", ".join(v["hidden"] for v in values)
        median = statistics.median(times)
        body.append(
            "<tr>"
            + model_cell(model)
            + text_cell(len(values))
            + text_cell(f"{median:g}", median)
            + text_cell(f"{min(times)}–{max(times)}", min(times))
            + text_cell(scores)
            + "</tr>"
        )
    columns = [
        ("Model", "The exact historical tag is shown beside each model."),
        ("Runs", "The number of hard-fixture runs."),
        ("Median seconds", "Median session wall time. Lower is faster."),
        ("Range seconds", "Minimum and maximum session wall time."),
        ("Held-out scores", "Passed hidden ledger tests out of 18, in run order."),
    ]
    return table(
        "Historical v4 hard fixture",
        "2026-09-25, Ollama 0.33.3, host client. Do not rank these values against the current sandbox runs.",
        columns,
        body,
    )


def render(
    speed,
    extra,
    basic,
    short,
    stock,
    adaptive,
    deep,
    coding,
    corrections,
    history,
    residency,
    needle,
    bilingual,
):
    full = max(r["context"] for r in residency if r["full_gpu"])
    recall = max(
        r["prompt_eval_count"]
        for r in needle
        if "CRIMSON-PANGOLIN-4471" in r["message"]["content"].upper()
    )
    gate_passes = sum(row["verdict"] == "PASS" for row in short)
    gate_total = len(short)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = (
        speed_table(speed)
        + gate_table(extra, basic, short, stock, adaptive, deep)
        + coding_table(coding, corrections)
        + history_table(history)
        + (bilingual_table(bilingual) if bilingual else "")
    )
    return (
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="60"><title>Kolibri Q3 benchmark</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#0c1420;color:#eaf1f8}body{margin:0}main{max-width:1240px;margin:auto;padding:42px 28px 80px}header{border-bottom:1px solid #2a3b4d;padding-bottom:26px}.eyebrow{color:#76dbc4;font-size:.75rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase}h1{font-size:clamp(2rem,5vw,3.6rem);margin:.35em 0 .2em;letter-spacing:-.04em}header p{color:#a9b9c9;max-width:820px;line-height:1.6}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:26px 0}.card{background:#172536;border:1px solid #2a3b4d;border-radius:12px;padding:18px}.card small{color:#a9b9c9}.card strong{display:block;color:#7fe5ca;font-size:1.75rem;margin:.3em 0}.card p{font-size:.85rem;color:#a9b9c9;line-height:1.45;margin:0}section{margin-top:34px;background:#111e2c;border:1px solid #26384a;border-radius:12px;overflow:hidden}.section-head{padding:20px 20px 0}h2{font-size:1.15rem;margin:0}.section-head p{color:#a9b9c9;line-height:1.5;font-size:.88rem}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.88rem}th,td{text-align:left;padding:12px 20px;border-top:1px solid #26384a;white-space:nowrap}th{color:#a9b9c9;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;cursor:pointer}tr:hover td{background:#192b3d}.info{display:inline-grid;place-items:center;width:15px;height:15px;border:1px solid #668293;border-radius:50%;color:#9eb5c2;font-size:.65rem;font-weight:700;text-transform:none;cursor:help}.arrow{color:#678292}footer{color:#9aabba;font-size:.8rem;margin-top:30px;line-height:1.6}a{color:#7fe5ca}</style></head><body><main><header><div class="eyebrow">Local inference · experiment</div><h1>Kolibri Q3 benchmark</h1><p>Measured on the shared Ollama server. Long-context retrieval works; agentic reliability and coding sessions are still under investigation. Select a column heading to sort. Hover over an i for details.</p></header><div class="cards"><div class="card"><small>Full GPU allocation <span class="info" title="Largest tested context with size_vram equal to size. The next 1,024-token step spilled.">i</span></small><strong>"""
        + f"{full:,}"
        + """</strong><p>tokens, on the current server configuration</p></div><div class="card"><small>Verified retrieval <span class="info" title="Largest non-overflowing v4 needle prompt that returned the expected fact.">i</span></small><strong>"""
        + f"{recall:,}"
        + """</strong><p>prompt tokens in the longest successful test</p></div><div class="card"><small>First tool gate <span class="info" title="The corrected-template arm was tested on the T1 file-write call.">i</span></small><strong>"""
        + f"{gate_passes} / {gate_total}"
        + """</strong><p>correct calls with the corrected template</p></div></div>"""
        + body
        + """<footer>Generated from result files at """
        + esc(built)
        + """. Results may be incomplete while tests run. See <a href="KOLIBRI_Q3_RUN.md">the run record</a> and <a href="../ollamaClaudeCode_v4_tielCoder/dashboard.html">the v4 dashboard</a>.</footer></main><script>
document.querySelectorAll('th').forEach((head,index)=>{head.addEventListener('click',()=>{const table=head.closest('table');const column=[...head.parentNode.children].indexOf(head);const rows=[...table.tBodies[0].rows];const direction=head.dataset.direction==='asc'?'desc':'asc';table.querySelectorAll('th').forEach(x=>delete x.dataset.direction);head.dataset.direction=direction;rows.sort((a,b)=>{const av=a.cells[column].dataset.sort,bv=b.cells[column].dataset.sort;const an=Number(av),bn=Number(bv);const c=av.trim()!==''&&bv.trim()!==''&&!Number.isNaN(an)&&!Number.isNaN(bn)?an-bn:av.localeCompare(bv);return direction==='asc'?c:-c});rows.forEach(row=>table.tBodies[0].appendChild(row))});head.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();head.click()}})});
</script></body></html>"""
    )


def main():
    coding_path = MEASUREMENTS / "coding-current.tsv"
    coding = read_tsv(coding_path) if coding_path.exists() else []
    with (MEASUREMENTS / "agentic-gates.tsv").open(
        encoding="utf-8", newline=""
    ) as stream:
        basic = [
            dict(zip(("model", "gate", "passes", "status"), row))
            for row in csv.reader(stream, delimiter="\t")
        ]
    extra = read_tsv(MEASUREMENTS / "agentic-extra.tsv")
    fidelity = MEASUREMENTS / "fidelity.tsv"
    if fidelity.exists():
        extra += read_tsv(fidelity)
    adaptive_path = MEASUREMENTS / "adaptive-t1.jsonl"
    adaptive = read_jsonl(adaptive_path) if adaptive_path.exists() else []
    deep = []
    for filename, tag in (
        ("deep-kolibri.tsv", "kolibri1:q3ks-ctx147456-nothink-ab"),
        ("deep-qwen.tsv", "qwen3.6:35b-a3b-q4_K_M-agentic"),
    ):
        path = MEASUREMENTS / filename
        if path.exists():
            deep.extend((tag, row) for row in read_tsv(path))
    bilingual_path = MEASUREMENTS / "bilingual.jsonl"
    bilingual = read_jsonl(bilingual_path) if bilingual_path.exists() else []
    page = render(
        read_tsv(MEASUREMENTS / "speed.tsv"),
        extra,
        basic,
        read_jsonl(MEASUREMENTS / "nothink-t1-eight.jsonl"),
        read_jsonl(MEASUREMENTS / "stock-t1-eight.jsonl"),
        adaptive,
        deep,
        coding,
        json.loads((MEASUREMENTS / "coding-rescores.json").read_text()),
        read_tsv(HISTORY),
        read_jsonl(MEASUREMENTS / "residency.jsonl")
        + read_jsonl(MEASUREMENTS / "refinement.jsonl"),
        read_jsonl(MEASUREMENTS / "needle-near.jsonl"),
        bilingual,
    )
    target = ROOT / "dashboard.html"
    temporary = ROOT / "dashboard.html.new"
    temporary.write_text(page, encoding="utf-8")
    os.replace(temporary, target)


if __name__ == "__main__":
    main()
