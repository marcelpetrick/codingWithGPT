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

import gate_score

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


def info(note, label):
    return f'<span class="info" tabindex="0" role="button" aria-label="{esc(label)}" data-tip="{esc(note)}">i</span>'


def model_cell(tag):
    note = f"Model tag: {tag}. The displayed value applies only to the stated test conditions."
    return f'<td data-v="{esc(model_name(tag))}"><b>{esc(model_name(tag))}</b>{info(note, "About this model")}</td>'


def text_cell(value, sort=None):
    css = ' class="num"' if sort is not None else ""
    return f'<td{css} data-v="{esc(value if sort is None else sort)}">{esc(value)}</td>'


def header(label, note):
    return f'<th tabindex="0">{esc(label)}{info(note, "About this column")}</th>'


def table(title, description, columns, rows):
    headings = "".join(header(*col) for col in columns)
    return f'<section><h2>{esc(title)}</h2><p class="muted small">{esc(description)}</p><div class="panel"><table><thead><tr>{headings}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'


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


def gate_counts(rows):
    verdicts = [gate_score.t1(row.get("response", {}))[0] for row in rows]
    return (
        verdicts.count("PASS"),
        len(verdicts) - verdicts.count("ERROR"),
        verdicts.count("ERROR"),
    )


def gate_table(
    extra,
    basic,
    short,
    stock,
    adaptive,
    reason_arm,
    parser_arm,
    deep,
    raw_gates,
    strict_t5,
):
    body = []
    for label, rows in (
        ("Stock template", stock),
        ("Corrected template", short),
        ("Adaptive thinking", adaptive),
        ("Reasoning instruction", reason_arm),
        ("Qwen3 parser", parser_arm),
    ):
        if not rows:
            continue
        passed, valid, invalid = gate_counts(rows)
        body.append(
            "<tr>"
            + model_cell(rows[0]["model"])
            + text_cell("T1 · write file")
            + text_cell(label)
            + text_cell(f"{passed}/{valid}", passed / valid if valid else -1)
            + text_cell(invalid)
            + "</tr>"
        )
    if strict_t5:
        verdicts = [gate_score.t5(row.get("response", {}))[0] for row in strict_t5]
        valid = len(verdicts) - verdicts.count("ERROR")
        passed = verdicts.count("PASS")
        body.append(
            "<tr>"
            + model_cell(strict_t5[0]["model"])
            + text_cell("T5 · nested schema")
            + text_cell("Strict rerun")
            + text_cell(f"{passed}/{valid}", passed / valid if valid else -1)
            + text_cell(verdicts.count("ERROR"))
            + "</tr>"
        )
    for model, row in deep:
        if row["test"] not in ("T3_multiturn", "T7_tool_at_long_ctx"):
            continue
        count = (
            row["detail"].split("_at_")[0]
            if row["test"].startswith("T7")
            else row.get("detail", "").split("_at_")[0]
            if row.get("configuration")
            else ("1/1" if row["result"] == "PASS" else "0/1")
        )
        body.append(
            "<tr>"
            + model_cell(model)
            + text_cell(row["test"].replace("_", " · ", 1))
            + text_cell(row.get("configuration", "Long-context run"))
            + text_cell(count, int(count.split("/")[0]) / int(count.split("/")[1]))
            + text_cell("—")
            + "</tr>"
        )
    for row in basic:
        passed, total = row["passes"].split("/")
        if row["gate"] == "T5":
            matching = [
                item
                for item in raw_gates
                if item["model"] == row["model"] and item["gate"] == "T5"
            ]
            verdicts = [gate_score.t5(item["response"])[0] for item in matching]
            passed, total = (
                str(verdicts.count("PASS")),
                str(len(verdicts) - verdicts.count("ERROR")),
            )
        if int(total) == 0:
            continue
        body.append(
            "<tr>"
            + model_cell(row["model"])
            + text_cell(row["gate"])
            + text_cell(
                "Corrected" if row["model"].startswith("kolibri1:") else "Control"
            )
            + text_cell(f"{passed}/{total}", int(passed) / int(total))
            + text_cell("—")
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
            + text_cell(
                f"{row['pass_n']}/{row['runs']}", int(row["pass_n"]) / int(row["runs"])
            )
            + text_cell("—")
            + "</tr>"
        )
    columns = [
        ("Model", "The exact tag is shown beside each model."),
        (
            "Gate",
            "The v4 tool or structured-output test. T1 and T5 use stricter argument checks.",
        ),
        ("Configuration", "The template or control used for this arm."),
        (
            "Valid passes",
            "Passes divided by scoreable responses. Three trials are preliminary.",
        ),
        (
            "Empty",
            "Empty API content is invalid and excluded from the pass count. A dash means the original log lacks enough detail.",
        ),
    ]
    return table(
        "Agentic gates",
        "Empty API responses are invalid. T1 retains eight raw responses per original arm; other gates have three trials per model.",
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


def optional_number(row, key):
    value = row.get(key, "")
    if str(value).isdigit():
        return text_cell(f"{int(value):,}", int(value))
    return text_cell("—")


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
            + optional_number(row, "calls")
            + optional_number(row, "out_tok")
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
        ("API calls", "The number of model API calls made during the session."),
        ("Output tokens", "The total generated tokens across all model calls."),
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
    reason_arm,
    parser_arm,
    deep,
    coding,
    corrections,
    history,
    residency,
    needle,
    bilingual,
    raw_gates,
    strict_t5,
):
    full = max(r["context"] for r in residency if r["full_gpu"])
    recall = max(
        r["prompt_eval_count"]
        for r in needle
        if "CRIMSON-PANGOLIN-4471" in r["message"]["content"].upper()
    )
    gate_passes, gate_total, gate_empty = gate_counts(short)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = (
        speed_table(speed)
        + gate_table(
            extra,
            basic,
            short,
            stock,
            adaptive,
            reason_arm,
            parser_arm,
            deep,
            raw_gates,
            strict_t5,
        )
        + coding_table(coding, corrections)
        + history_table(history)
        + (bilingual_table(bilingual) if bilingual else "")
    )
    static = Path(__file__).resolve().parent
    style = (static / "dashboard_style.css").read_text(encoding="utf-8")
    script = (static / "dashboard_ui.js").read_text(encoding="utf-8")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="60"><title>Kolibri Q3 benchmark</title><style>'
        + style
        + "</style></head><body><main><h1>Local agentic coding on .67: Kolibri Q3</h1>"
        + '<div class="muted small">Ollama 0.40.11 · Claude Code · generated '
        + esc(built)
        + " from result files · refreshes every 60 seconds</div>"
        + '<div class="verdict"><b>Kolibri runs and retrieves long context.</b><br>'
        + "It passed the hard Python fixture, but tool-call delivery needs more work. Qwen remains the safer default.</div>"
        + '<h2>Current findings</h2><div class="picks"><div class="pick"><div class="muted small">FULL GPU ALLOCATION'
        + info(
            "Largest tested context with size_vram equal to size. The next 1,024-token step spilled.",
            "About full GPU allocation",
        )
        + "</div><b>"
        + f"{full:,}"
        + '</b><div class="small">tokens on the current server</div></div>'
        + '<div class="pick"><div class="muted small">VERIFIED RETRIEVAL'
        + info(
            "Largest non-overflowing v4 needle prompt that returned the expected fact.",
            "About verified retrieval",
        )
        + "</div><b>"
        + f"{recall:,}"
        + '</b><div class="small">prompt tokens</div></div>'
        + '<div class="pick"><div class="muted small">FIRST TOOL GATE'
        + info(
            "The corrected-template arm was tested on the T1 file-write call. Empty API responses are invalid.",
            "About the first tool gate",
        )
        + "</div><b>"
        + f"{gate_passes} / {gate_total}"
        + '</b><div class="small">correct among valid responses; '
        + str(gate_empty)
        + " empty</div></div></div>"
        + body
        + '<p class="small muted">Results may be incomplete while tests run. See <a href="KOLIBRI_Q3_RUN.md">the run record</a> and <a href="../ollamaClaudeCode_v4_tielCoder/dashboard.html">the v4 dashboard</a>. Click a column to sort.</p></main>'
        + '<div id="tip" role="tooltip"></div><script>'
        + script
        + "</script></body></html>"
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
    reason_path = MEASUREMENTS / "reason-effort-t1.jsonl"
    reason_arm = read_jsonl(reason_path) if reason_path.exists() else []
    parser_path = MEASUREMENTS / "parser-arm-t1.jsonl"
    parser_arm = read_jsonl(parser_path) if parser_path.exists() else []
    deep = []
    for filename, tag in (
        ("deep-kolibri.tsv", "kolibri1:q3ks-ctx147456-nothink-ab"),
        ("deep-qwen.tsv", "qwen3.6:35b-a3b-q4_K_M-agentic"),
    ):
        path = MEASUREMENTS / filename
        if path.exists():
            deep.extend((tag, row) for row in read_tsv(path))
    targeted_path = MEASUREMENTS / "targeted-gates.jsonl"
    if targeted_path.exists():
        groups = {}
        for row in read_jsonl(targeted_path):
            groups.setdefault((row["model"], row["gate"]), []).append(row)
        for (model, gate), rows in groups.items():
            valid = [row for row in rows if row["verdict"] in ("PASS", "FAIL")]
            passed = sum(row["verdict"] == "PASS" for row in valid)
            if valid:
                deep.append(
                    (
                        model,
                        {
                            "test": "T7_tool_at_long_ctx"
                            if gate == "T7"
                            else "T3_multiturn",
                            "detail": f"{passed}/{len(valid)}_at_targeted",
                            "result": "PASS" if passed == len(valid) else "FAIL",
                            "configuration": "Targeted · temperature 0",
                        },
                    )
                )
    bilingual_path = MEASUREMENTS / "bilingual.jsonl"
    bilingual = read_jsonl(bilingual_path) if bilingual_path.exists() else []
    strict_path = MEASUREMENTS / "strict-t5.jsonl"
    strict_t5 = read_jsonl(strict_path) if strict_path.exists() else []
    page = render(
        read_tsv(MEASUREMENTS / "speed.tsv"),
        extra,
        basic,
        read_jsonl(MEASUREMENTS / "nothink-t1-eight.jsonl"),
        read_jsonl(MEASUREMENTS / "stock-t1-eight.jsonl"),
        adaptive,
        reason_arm,
        parser_arm,
        deep,
        coding,
        json.loads((MEASUREMENTS / "coding-rescores.json").read_text()),
        read_tsv(HISTORY),
        read_jsonl(MEASUREMENTS / "residency.jsonl")
        + read_jsonl(MEASUREMENTS / "refinement.jsonl"),
        read_jsonl(MEASUREMENTS / "needle-near.jsonl"),
        bilingual,
        read_jsonl(MEASUREMENTS / "agentic-gates.raw.jsonl"),
        strict_t5,
    )
    target = ROOT / "dashboard.html"
    temporary = ROOT / "dashboard.html.new"
    temporary.write_text(page, encoding="utf-8")
    os.replace(temporary, target)


if __name__ == "__main__":
    main()
