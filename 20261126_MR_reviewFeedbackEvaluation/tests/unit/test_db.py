# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the SQLite layer (REQ-DB-1, REQ-DB-2)."""

import sqlite3
from pathlib import Path

import pytest

from mrreview import db


def test_migrations_set_user_version(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"projects", "merge_requests", "notes", "work", "findings", "gaps"} <= tables


def test_reconnect_does_not_rerun_migrations(tmp_path: Path) -> None:
    p = tmp_path / "a.sqlite3"
    db.connect(p).close()
    c = db.connect(p)
    assert c.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    c.close()


def test_newer_schema_is_refused(tmp_path: Path) -> None:
    p = tmp_path / "b.sqlite3"
    c = db.connect(p)
    c.execute("PRAGMA user_version = 999")
    c.close()
    with pytest.raises(RuntimeError, match="newer"):
        db.connect(p)


def test_tx_commits_and_rolls_back(conn: sqlite3.Connection) -> None:
    with db.tx(conn):
        conn.execute("INSERT INTO meta(key, value) VALUES ('a', '1')")
    with pytest.raises(ZeroDivisionError), db.tx(conn):
        conn.execute("INSERT INTO meta(key, value) VALUES ('b', '2')")
        _ = 1 / 0
    keys = [r[0] for r in conn.execute("SELECT key FROM meta")]
    assert keys == ["a"]


def test_work_states(conn: sqlite3.Connection) -> None:
    with db.tx(conn):
        db.set_work(conn, "mr", "1:2", "pending", input_hash="h1")
        db.set_work(conn, "mr", "1:3", "failed", error="boom")
        db.set_work(conn, "mr", "1:3", "failed", error="boom2")
    w = db.get_work(conn, "mr", "1:3")
    assert w is not None
    assert w.status == "failed"
    assert w.attempts == 2
    assert w.last_error == "boom2"
    assert db.get_work(conn, "mr", "9:9") is None
    assert db.work_summary(conn) == {"mr": {"pending": 1, "failed": 1}}
    with pytest.raises(ValueError, match="status"):
        db.set_work(conn, "mr", "x", "weird")


def test_meta_roundtrip(conn: sqlite3.Connection) -> None:
    assert db.get_meta(conn, "k") is None
    assert db.get_meta(conn, "k", "d") == "d"
    with db.tx(conn):
        db.set_meta(conn, "k", "v")
        db.set_meta(conn, "k", "w")
    assert db.get_meta(conn, "k") == "w"


def test_record_gap_dedupes(conn: sqlite3.Connection) -> None:
    with db.tx(conn):
        db.record_gap(conn, "mr", "1:2", "diff_too_large", "a.py")
        db.record_gap(conn, "mr", "1:2", "diff_too_large", "a.py")
    assert conn.execute("SELECT COUNT(*) FROM gaps").fetchone()[0] == 1
