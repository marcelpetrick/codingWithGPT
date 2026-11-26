# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the annotation sample and agreement figures (REQ-LLM-4)."""

import csv
import sqlite3
from pathlib import Path

import pytest

from mrreview import db, quality


def seed(conn: sqlite3.Connection) -> None:
    with db.tx(conn):
        conn.execute(
            "INSERT INTO merge_requests(project_id, iid, id, title, state, created_at, updated_at, "
            "web_url, fetched_at) VALUES (1, 1, 1, 't', 'merged', 'x', 'x', 'http://g/mr/1', 'x')"
        )
        for i, outcome in enumerate(["open", "implemented", "open", "deferred"]):
            conn.execute(
                "INSERT INTO threads(id, project_id, mr_iid, first_note_id, giver_kind, responders, "
                "created_at, last_note_at, n_notes, n_human_notes, has_reply, substantive, reason, "
                "resolvable, resolved, input_hash) VALUES (?, 1, 1, ?, 'human', '[]', 'x', 'x', 1, 1, 0, 1, "
                "'substantive', 1, 0, 'h')",
                (f"t{i}", 100 + i),
            )
            conn.execute(
                "INSERT INTO findings VALUES (?, 0, 's', 'defect', 'change_request', 'supported', "
                "'neutral', 'code', ?, 'open', ?, 'not_applicable', 0, NULL, NULL, NULL, '[]', 'r', 0, "
                "'{}', 'x')",
                (f"t{i}", '{"acts": [], "primary": "agreement"}', outcome),
            )


def test_write_sample_and_agreement(conn: sqlite3.Connection, tmp_path: Path) -> None:
    seed(conn)
    out = tmp_path / "s.csv"
    assert quality.write_sample(conn, out, 3) == 3
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert {r["model_outcome"] for r in rows} == {"open", "implemented", "deferred"}
    assert rows[0]["url"].startswith("http://g/mr/1#note_")
    for r in rows:
        r["human_intent"] = "defect"
        r["human_outcome"] = "open"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    res = quality.agreement(out)
    assert res["intent"]["n"] == 3
    assert res["intent"]["agreement"] == 1.0
    assert res["intent"]["kappa"] is None
    assert res["outcome"]["agreement"] == pytest.approx(1 / 3)
    assert res["validity"]["n"] == 0
    assert res["validity"]["agreement"] is None
    assert len(res["outcome"]["top_confusions"]) == 2


def test_cohen_kappa() -> None:
    assert quality.cohen_kappa([]) is None
    assert quality.cohen_kappa([("a", "a"), ("b", "b")]) == 1.0
    assert quality.cohen_kappa([("a", "b"), ("b", "a")]) == -1.0
    assert quality.cohen_kappa([("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]) == pytest.approx(
        0.5
    )
