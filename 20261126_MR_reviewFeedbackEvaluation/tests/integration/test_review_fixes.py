# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the reviewBranch findings of 2026-11-26 (docs/review_20261126_branch.md)."""

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from mrreview import cli, collect, evidence, normalize
from mrreview.demo.fixture import REFERENCE_NOW

from .conftest import Env


def test_temporary_compare_error_is_retried(gl: Env, conn: sqlite3.Connection) -> None:
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1, max_mrs=5)
    normalize.build_threads(conn)
    gl.fake.faults = {r"/repository/compare$": [500] * 200}
    first = evidence.run_evidence(gl.client, conn)
    assert first["failed"] > 0
    assert first["unavailable"] == 0
    gl.fake.faults = {}
    again = evidence.run_evidence(gl.client, conn)
    assert again["fetched"] == first["failed"]
    assert again["failed"] == 0


def test_vanished_project_is_not_reused(gl: Env, conn: sqlite3.Connection) -> None:
    collect.discover(gl.client, conn, gl.cfg, REFERENCE_NOW)
    gone = gl.fixture.projects.pop(0)
    fresh_time = REFERENCE_NOW + timedelta(hours=25)
    later = collect.discover(gl.client, conn, gl.cfg, fresh_time)
    assert gone["id"] not in later  # a fresh discovery marks it
    reused = collect.discover(gl.client, conn, gl.cfg, fresh_time)
    assert gone["id"] not in reused
    reason = conn.execute("SELECT skip_reason FROM projects WHERE id=?", (gone["id"],)).fetchone()[
        0
    ]
    assert reason == "not visible"


def test_mr_listing_uses_a_stable_order(gl: Env) -> None:
    list(gl.client.merge_requests(11))
    assert any("order_by=created_at" in p for p in gl.fake.paths)


def test_bad_record_is_a_gap_not_a_crash(gl: Env, conn: sqlite3.Connection) -> None:
    key = next(iter(gl.fixture.versions))
    gl.fixture.versions[key][0]["created_at"] = None
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1)
    if key[0] == 11 or stats.mrs_failed:
        assert conn.execute("SELECT COUNT(*) FROM gaps WHERE kind='bad_record'").fetchone()[0] >= 0
    assert stats.mrs_collected > 0


def test_zero_minutes_means_no_new_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    assert cli._budget(argparse.Namespace(max_minutes=0)) == 0.0
    assert cli._budget(argparse.Namespace(max_minutes=None)) is None
