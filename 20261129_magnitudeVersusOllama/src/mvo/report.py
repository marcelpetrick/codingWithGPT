# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate report.md and dashboard.html from results/*.jsonl and arms.json.

Never edit the outputs by hand. Run ``mvo report`` after every stage.
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mvo.stats import Summary, quality_verdict, ratio, speed_verdict, summarize

COLUMNS: dict[str, str] = {
    "site": "Where the run happened. 'laptop' is the RTX A2000 8 GB. 'box' is 192.168.100.67.",
    "workload": "A = vendor replication (repeat a passage). B = realistic coding (new code). "
    "C = quality (20 tasks with unit tests).",
    "ctx": "Context size of the cell in tokens. The prompt fills it minus the output room.",
    "arm": "The labelled configuration (engine, model tag, drafter). Arms never pool.",
    "engine_version": "Engine version recorded in each row of this cell.",
    "n": "Good rows / failed rows. A failed row is an error, an empty answer or thinking that was "
    "not off. Failed rows never count as speed.",
    "decode": "Median generated tokens per second after the first token, client side, with the "
    "min-max range. Higher is better.",
    "prefill": "Median prompt tokens per second up to the first visible token, client side "
    "(includes HTTP and scheduling). Higher is better.",
    "ttft": "Median time to the first visible token in seconds. Lower is better.",
    "passed": "Workload C only: tasks whose unit tests passed (greedy, one answer per task).",
    "pair": "Arm a against arm b in the same cell.",
    "decode_ratio": "Median decode of a divided by median decode of b.",
    "decode_verdict": "Fixed rule: 'faster' needs a median at least 25% higher and min-max ranges "
    "that do not overlap, with n >= 5 per arm. Else 'tie'.",
    "prefill_ratio": "Median prefill of a divided by median prefill of b.",
    "prefill_verdict": "Same fixed rule as decode_verdict, on prefill.",
    "status": "Gate result: does the model load and answer at all on this site.",
}


@dataclass
class Cell:
    """All rows of one arm in one (site, workload, ctx) cell."""

    ok: list[dict[str, Any]]
    failed: int

    def metric(self, name: str) -> Summary:
        """Summarize one numeric field over the good rows."""
        return summarize([float(r[name]) for r in self.ok])


def load_rows(results_dir: Path) -> list[dict[str, Any]]:
    """Read every row of every results/*.jsonl file except the gate file."""
    rows: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*.jsonl")):
        if path.name == "gate.jsonl":
            continue
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return rows


def load_gate(results_dir: Path) -> list[dict[str, Any]]:
    """Read the gate rows (load / refuse results)."""
    path = results_dir / "gate.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def group(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Cell]]:
    """Group rows by (site, workload, ctx) and then by arm."""
    cells: dict[tuple[str, str, int], dict[str, Cell]] = defaultdict(dict)
    for row in rows:
        cell = cells[(row["site"], row["workload"], int(row["ctx"]))].setdefault(row["arm"], Cell([], 0))
        if row.get("ok"):
            cell.ok.append(row)
        else:
            cell.failed += 1
    return dict(cells)


def _fmt(s: Summary, digits: int = 1) -> str:
    return f"{s.median:.{digits}f} [{s.low:.{digits}f}–{s.high:.{digits}f}]" if s.n else "–"


def arm_table(cells: dict[tuple[str, str, int], dict[str, Cell]]) -> list[dict[str, str]]:
    """One line per (cell, arm)."""
    lines = []
    for (site, workload, ctx), arms in sorted(cells.items()):
        for label, cell in sorted(arms.items()):
            versions = sorted({str(r.get("engine_version", "")) for r in cell.ok}) or ["–"]
            passed = sum(1 for r in cell.ok if r.get("passed")) if workload == "C" else None
            lines.append(
                {
                    "site": site,
                    "workload": workload,
                    "ctx": str(ctx),
                    "arm": label,
                    "engine_version": ", ".join(versions),
                    "n": f"{len(cell.ok)}/{cell.failed}",
                    "decode": _fmt(cell.metric("decode_tps")),
                    "prefill": _fmt(cell.metric("prefill_tps"), 0),
                    "ttft": _fmt(cell.metric("ttft_s"), 2),
                    "passed": "–" if passed is None else f"{passed}/{len(cell.ok)}",
                }
            )
    return lines


def comparisons(cells: dict[tuple[str, str, int], dict[str, Cell]]) -> list[dict[str, str]]:
    """Every Magnitude arm against every Ollama arm in the same cell."""
    lines = []
    for (site, workload, ctx), arms in sorted(cells.items()):
        mags = sorted(a for a in arms if a.startswith("magnitude"))
        olls = sorted(a for a in arms if a.startswith("ollama"))
        for a in mags:
            for b in olls:
                ca, cb = arms[a], arms[b]
                line = {"site": site, "workload": workload, "ctx": str(ctx), "pair": f"{a} vs {b}"}
                if workload == "C":
                    pa = sum(1 for r in ca.ok if r.get("passed"))
                    pb = sum(1 for r in cb.ok if r.get("passed"))
                    line.update(
                        decode_ratio="–",
                        decode_verdict=f"quality: {quality_verdict(pa, pb)} ({pa} vs {pb})",
                        prefill_ratio="–",
                        prefill_verdict="–",
                    )
                else:
                    da, db = ca.metric("decode_tps"), cb.metric("decode_tps")
                    pfa, pfb = ca.metric("prefill_tps"), cb.metric("prefill_tps")
                    line.update(
                        decode_ratio=f"{ratio(da, db):.2f}x",
                        decode_verdict=speed_verdict(da, db),
                        prefill_ratio=f"{ratio(pfa, pfb):.2f}x",
                        prefill_verdict=speed_verdict(pfa, pfb),
                    )
                lines.append(line)
    return lines


def overall(comps: list[dict[str, str]]) -> str:
    """Rule 4 of PLAN.md: better only if clearly faster on every B cell and not worse on C."""
    b_cells = [c for c in comps if c["workload"] == "B"]
    c_cells = [c for c in comps if c["workload"] == "C"]
    if not b_cells or not c_cells:
        return "No verdict yet: workload B and workload C must both have Magnitude and Ollama rows."
    faster = all(c["decode_verdict"] == "a faster" for c in b_cells)
    not_worse = all("b better" not in c["decode_verdict"] for c in c_cells)
    if faster and not_worse:
        return "Magnitude is better here: clearly faster on every B cell and not worse on quality."
    reasons = []
    if not faster:
        reasons.append("not clearly faster on every B cell")
    if not not_worse:
        reasons.append("worse on quality (C)")
    return "Magnitude is not better here: " + " and ".join(reasons) + "."


def _md_table(lines: list[dict[str, str]], cols: list[str]) -> str:
    if not lines:
        return "_No rows yet._\n"
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(line.get(c, "") for c in cols) + " |" for line in lines]
    return "\n".join(out) + "\n"


ARM_COLS = ["site", "workload", "ctx", "arm", "engine_version", "n", "decode", "prefill", "ttft", "passed"]
CMP_COLS = ["site", "workload", "ctx", "pair", "decode_ratio", "decode_verdict", "prefill_ratio", "prefill_verdict"]
GATE_COLS = ["site", "engine", "model", "status", "detail"]


def render_markdown(arms_doc: dict[str, Any], rows: list[dict[str, Any]], gate: list[dict[str, Any]]) -> str:
    """Return report.md."""
    cells = group(rows)
    comps = comparisons(cells)
    gate_lines = [{k: str(g.get(k, "")) for k in GATE_COLS} for g in gate]
    parts = [
        "# Report: Magnitude versus Ollama\n",
        "Generated by `mvo report` from `results/*.jsonl`. Do not edit.\n",
        f"## Verdict\n\n{overall(comps)}\n",
        "## Gate: does it load here\n",
        _md_table(gate_lines, GATE_COLS),
        "## Comparisons (fixed rule)\n",
        _md_table(comps, CMP_COLS),
        "## Arms per cell\n",
        _md_table(arm_table(cells), ARM_COLS),
        "## Arms\n",
        "\n".join(f"- `{a['label']}`: {a.get('note', '')}" for a in arms_doc.get("arms", [])) + "\n",
        "## Columns\n",
        "\n".join(f"- `{k}`: {v}" for k, v in COLUMNS.items()) + "\n",
    ]
    return "\n".join(parts)


def _html_table(table_id: str, lines: list[dict[str, str]], cols: list[str], notes: dict[str, str]) -> str:
    head = "".join(
        f"<th onclick=\"sortTable('{table_id}',{i})\">{html.escape(c)}"
        f' <span class="info" title="{html.escape(COLUMNS.get(c, ""))}">ⓘ</span></th>'
        for i, c in enumerate(cols)
    )
    body = []
    for line in lines:
        cells = []
        for c in cols:
            value = html.escape(line.get(c, ""))
            if c in ("arm", "pair") and notes:
                tip = " / ".join(notes.get(p.strip(), "") for p in line.get(c, "").split(" vs "))
                value += f' <span class="info" title="{html.escape(tip)}">ⓘ</span>'
            cells.append(f"<td>{value}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    if not body:
        body.append(f'<tr><td colspan="{len(cols)}">No rows yet.</td></tr>')
    return f'<table id="{table_id}"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def render_html(arms_doc: dict[str, Any], rows: list[dict[str, Any]], gate: list[dict[str, Any]]) -> str:
    """Return dashboard.html: sortable tables, an (i) note on every column and every arm."""
    notes = {a["label"]: a.get("note", "") for a in arms_doc.get("arms", [])}
    cells = group(rows)
    comps = comparisons(cells)
    gate_lines = [{k: str(g.get(k, "")) for k in GATE_COLS} for g in gate]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Magnitude vs Ollama</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#ddd;--head:#f3f3f3}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151515;--fg:#e8e8e8;--muted:#999;--line:#333;--head:#222}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0 16px 40px;max-width:1200px}}
table{{border-collapse:collapse;width:100%;margin:8px 0 24px;display:block;overflow-x:auto}}
th,td{{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;white-space:nowrap}}
th{{background:var(--head);cursor:pointer;user-select:none}}
.info{{color:var(--muted);cursor:help}} .verdict{{font-size:1.1em;font-weight:600}}
</style></head><body>
<h1>Magnitude vs Ollama</h1>
<p>Generated by <code>mvo report</code> from <code>results/*.jsonl</code>. Do not edit. Click a header to sort.</p>
<p class="verdict">{html.escape(overall(comps))}</p>
<h2>Gate: does it load here</h2>{_html_table("gate", gate_lines, GATE_COLS, {})}
<h2>Comparisons (fixed rule)</h2>{_html_table("cmp", comps, CMP_COLS, notes)}
<h2>Arms per cell</h2>{_html_table("arms", arm_table(cells), ARM_COLS, notes)}
<script>
function sortTable(id,col){{const t=document.getElementById(id),b=t.tBodies[0],rows=[...b.rows];
const dir=t.dataset.col==col&&t.dataset.dir=="asc"?"desc":"asc";t.dataset.col=col;t.dataset.dir=dir;
const key=r=>{{const s=r.cells[col]?r.cells[col].innerText:"";const n=parseFloat(s);return isNaN(n)?s:n}};
rows.sort((x,y)=>{{const a=key(x),c=key(y);const r=a<c?-1:a>c?1:0;return dir=="asc"?r:-r}});
rows.forEach(r=>b.appendChild(r))}}
</script></body></html>
"""


def write_reports(root: Path) -> tuple[Path, Path]:
    """Read root/results and root/arms.json, write root/report.md and root/dashboard.html."""
    arms_doc = json.loads((root / "arms.json").read_text(encoding="utf-8"))
    rows = load_rows(root / "results")
    gate = load_gate(root / "results")
    md = root / "report.md"
    page = root / "dashboard.html"
    md.write_text(render_markdown(arms_doc, rows, gate), encoding="utf-8")
    page.write_text(render_html(arms_doc, rows, gate), encoding="utf-8")
    return md, page
