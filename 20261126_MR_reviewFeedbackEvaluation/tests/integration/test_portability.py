# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration: moving the database between machines and tool versions (REQ-DB-4, D-018)."""

import gzip
import json
import sqlite3
from pathlib import Path

import pytest

from mrreview import db, portability
from mrreview.cli import main


def filled(path: Path) -> sqlite3.Connection:
    conn = db.connect(path)
    with db.tx(conn):
        conn.execute("INSERT INTO users VALUES (1, 'a', 'Ana Ñ', 'human', NULL)")
        conn.execute("INSERT INTO meta VALUES ('k', 'v')")
        conn.execute(
            "INSERT INTO projects(id, name, path, web_url, discovered_at) VALUES (5, 'p', 'g/p', 'u', 'x')"
        )
    return conn


def test_export_import_roundtrip(tmp_path: Path) -> None:
    conn = filled(tmp_path / "a.sqlite3")
    out = tmp_path / "dump.jsonl.gz"
    n = portability.export_db(conn, out)
    assert n >= 3
    conn.close()
    target = tmp_path / "b.sqlite3"
    stats = portability.import_db(out, target)
    assert stats["users"] == 1
    c2 = db.connect(target)
    assert c2.execute("SELECT name FROM users").fetchone()[0] == "Ana Ñ"
    assert c2.execute("SELECT focus_mrs FROM projects").fetchone()[0] == 0
    c2.close()


def test_import_converts_an_older_layout(tmp_path: Path) -> None:
    out = tmp_path / "old.jsonl.gz"
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"format": portability.FORMAT, "schema": 1, "tool": "0.1.0"}) + "\n")
        # schema 1 projects had no focus_mrs column; an unknown old column is dropped
        row = {
            "id": 9,
            "name": "n",
            "path": "g/n",
            "web_url": "u",
            "selected": 1,
            "discovered_at": "x",
            "retired_column": "ignored",
        }
        fh.write(json.dumps({"table": "projects", "row": row}) + "\n")
    stats = portability.import_db(out, tmp_path / "new.sqlite3")
    assert stats == {"projects": 1}
    c = db.connect(tmp_path / "new.sqlite3")
    assert tuple(c.execute("SELECT id, selected, focus_mrs FROM projects").fetchone()) == (9, 1, 0)
    c.close()


def test_import_refuses_newer_or_foreign_files(tmp_path: Path) -> None:
    out = tmp_path / "new.jsonl.gz"
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"format": portability.FORMAT, "schema": 999, "tool": "9"}) + "\n")
    with pytest.raises(ValueError, match="newer"):
        portability.import_db(out, tmp_path / "x.sqlite3")
    bad = tmp_path / "bad.jsonl.gz"
    with gzip.open(bad, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"format": "other"}) + "\n")
    with pytest.raises(ValueError, match="not an mrreview export"):
        portability.import_db(bad, tmp_path / "y.sqlite3")
    existing = tmp_path / "exists.sqlite3"
    filled(existing).close()
    with pytest.raises(ValueError, match="exists"):
        portability.import_db(out, existing)


def test_migration_keeps_a_backup(tmp_path: Path) -> None:
    path = tmp_path / "v1.sqlite3"
    raw = sqlite3.connect(path)
    raw.executescript(db.MIGRATIONS[0] + "PRAGMA user_version = 1;")
    raw.execute("INSERT INTO users VALUES (1, 'a', 'A', 'human', NULL)")
    raw.commit()
    raw.close()
    conn = db.connect(path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.close()
    backups = list(tmp_path.glob("v1.sqlite3.schema1-*.bak"))
    assert len(backups) == 1
    old = sqlite3.connect(backups[0])
    assert old.execute("PRAGMA user_version").fetchone()[0] == 1
    old.close()


def test_pack_and_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    filled(tmp_path / "a.sqlite3").close()
    dbp = str(tmp_path / "a.sqlite3")
    assert main(["--db", dbp, "db-pack", "--out", str(tmp_path / "copy.sqlite3")]) == 0
    c = sqlite3.connect(tmp_path / "copy.sqlite3")
    assert c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    c.close()
    assert main(["--db", dbp, "db-export", "--out", str(tmp_path / "e.jsonl.gz")]) == 0
    assert (
        main(["--db", str(tmp_path / "n.sqlite3"), "db-import", str(tmp_path / "e.jsonl.gz")]) == 0
    )
    assert "imported" in capsys.readouterr().err
