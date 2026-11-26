# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Manual quality check of the classifications (REQ-LLM-4).

1. `mrreview sample` writes a stratified sample as CSV with empty human columns.
2. A person fills the human columns with the rubric in docs/annotation_rubric.md.
3. `mrreview agreement` reports agreement and Cohen's kappa per dimension.
"""

from __future__ import annotations

import csv
import json
import random
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

DIMENSIONS = ("intent", "actionability", "validity", "primary_response", "outcome")
_MODEL_COL = {
    "intent": "intent",
    "actionability": "actionability",
    "validity": "validity",
    "primary_response": "primary",
    "outcome": "outcome",
}


def write_sample(conn: sqlite3.Connection, out: Path, n: int, seed: int = 1) -> int:
    """Write up to n findings, spread over projects and outcomes (round robin per stratum)."""
    rows = conn.execute(
        """SELECT f.thread_id, f.idx, f.intent, f.actionability, f.validity, f.outcome, f.verification,
        f.responses, f.rationale, t.project_id, t.mr_iid, t.first_note_id, m.web_url
        FROM findings f JOIN threads t ON t.id=f.thread_id
        JOIN merge_requests m ON m.project_id=t.project_id AND m.iid=t.mr_iid ORDER BY f.thread_id, f.idx"""
    ).fetchall()
    rng = random.Random(seed)  # noqa: S311 - sampling, not security
    strata: dict[tuple[int, str], list[sqlite3.Row]] = {}
    for r in rows:
        strata.setdefault((r["project_id"], r["outcome"]), []).append(r)
    for items in strata.values():
        rng.shuffle(items)
    picked: list[sqlite3.Row] = []
    keys = sorted(strata)
    while len(picked) < n and any(strata[k] for k in keys):
        for k in keys:
            if strata[k] and len(picked) < n:
                picked.append(strata[k].pop())
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "thread_id",
                "finding_idx",
                "url",
                *[f"model_{d}" for d in DIMENSIONS],
                "model_verification",
                "model_rationale",
                *[f"human_{d}" for d in DIMENSIONS],
                "human_note",
            ]
        )
        for r in picked:
            primary = json.loads(r["responses"])["primary"]
            vals = {
                "intent": r["intent"],
                "actionability": r["actionability"],
                "validity": r["validity"],
                "primary_response": primary,
                "outcome": r["outcome"],
            }
            w.writerow(
                [
                    r["thread_id"],
                    r["idx"],
                    f"{r['web_url']}#note_{r['first_note_id']}",
                    *[vals[d] for d in DIMENSIONS],
                    r["verification"],
                    r["rationale"],
                    *[""] * len(DIMENSIONS),
                    "",
                ]
            )
    return len(picked)


def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa for two raters. None when undefined (no pairs or one category only)."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    expected = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def agreement(path: Path) -> dict[str, Any]:
    """Agreement between model and human columns of an annotated sample file."""
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out: dict[str, Any] = {}
    for d in DIMENSIONS:
        pairs = [
            (r[f"model_{d}"], r[f"human_{d}"].strip())
            for r in rows
            if r.get(f"human_{d}", "").strip()
        ]
        confusions = Counter((a, b) for a, b in pairs if a != b).most_common(3)
        out[d] = {
            "n": len(pairs),
            "agreement": (sum(a == b for a, b in pairs) / len(pairs)) if pairs else None,
            "kappa": cohen_kappa(pairs),
            "top_confusions": [f"{a} -> {b} ({c})" for (a, b), c in confusions],
        }
    return out
