# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration: code evidence through the GitLab compare API (REQ-OUT-1)."""

import sqlite3

from mrreview import collect, evaluate, evidence, normalize
from mrreview.demo.fixture import REFERENCE_NOW

from .conftest import Env


def test_compare_evidence_matches_fixture_truth(gl: Env, conn: sqlite3.Connection) -> None:
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1)
    normalize.build_threads(conn)
    stats = evidence.run_evidence(gl.client, conn)
    assert stats["ok"] + stats["same"] > 10
    checked = 0
    for t in conn.execute("SELECT * FROM threads WHERE substantive=1 AND new_path IS NOT NULL"):
        applied = gl.fixture.applied.get(t["id"])
        level = evaluate.code_evidence(conn, t).level
        if applied in ("direct", "silent"):
            assert level == "direct", t["id"]
            checked += 1
        elif applied == "file":
            assert level in ("indirect", "direct"), t["id"]
    assert checked > 3
    again = evidence.run_evidence(gl.client, conn)
    assert again["fetched"] == 0  # idempotent


def test_compare_failure_is_a_gap(gl: Env, conn: sqlite3.Connection) -> None:
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1, max_mrs=5)
    normalize.build_threads(conn)
    gl.fake.faults = {r"/repository/compare$": [404] * 50}
    stats = evidence.run_evidence(gl.client, conn)
    assert stats["unavailable"] > 0
    assert (
        conn.execute("SELECT COUNT(*) FROM gaps WHERE kind='compare_unavailable'").fetchone()[0] > 0
    )


def test_empty_version_is_incomplete(gl: Env, conn: sqlite3.Connection) -> None:
    key = next(k for k in gl.fixture.version_detail if k[0] == 11)
    gl.fixture.version_detail[key]["diffs"] = []
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1)
    row = conn.execute(
        "SELECT diffs_complete FROM mr_versions WHERE version_id=?", (key[2],)
    ).fetchone()
    assert row[0] == 0
    assert (
        conn.execute("SELECT COUNT(*) FROM gaps WHERE kind='version_without_files'").fetchone()[0]
        == 1
    )
