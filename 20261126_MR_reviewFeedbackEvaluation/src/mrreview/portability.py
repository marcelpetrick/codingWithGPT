# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Move a database between machines and tool versions (REQ-DB-4, owner input D-018).

- `pack`: a consistent single-file copy (VACUUM INTO), safe while the WAL file exists.
- `export_db` / `import_db`: a portable gzip JSON-lines file. The import creates a database with
  the current schema and maps each row onto it: columns that exist now are filled, new columns get
  their defaults, columns that no longer exist are dropped. A file from a newer tool is refused.
- Schema migrations run automatically on open and keep a backup of the old file.
"""

from __future__ import annotations

import gzip
import json
import sqlite3
from pathlib import Path
from typing import Any

from mrreview import __version__, db

FORMAT = "mrreview-export-1"


def _tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(r[0]) for r in rows]


def pack(conn: sqlite3.Connection, out: Path) -> Path:
    """Write a compact, consistent copy of the database to out."""
    if out.exists():
        raise ValueError(f"{out} exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    conn.execute("VACUUM INTO ?", (str(out),))
    return out


def export_db(conn: sqlite3.Connection, out: Path) -> int:
    """Export every table as JSON lines; return the number of rows."""
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps({"format": FORMAT, "schema": version, "tool": __version__}) + "\n")
        for table in _tables(conn):
            for row in conn.execute(f"SELECT * FROM {table}"):
                fh.write(json.dumps({"table": table, "row": dict(row)}, ensure_ascii=False) + "\n")
                n += 1
    return n


def import_db(src: Path, target: Path) -> dict[str, int]:
    """Create target with the current schema and load an export into it."""
    if target.exists():
        raise ValueError(f"{target} exists; import only into a new database")
    with gzip.open(src, "rt", encoding="utf-8") as fh:
        header: dict[str, Any] = json.loads(fh.readline() or "{}")
        if header.get("format") != FORMAT:
            raise ValueError(f"{src} is not an mrreview export")
        if int(header["schema"]) > len(db.MIGRATIONS):
            raise ValueError("the export comes from a newer tool; update mrreview first")
        conn = db.connect(target)
        columns = {
            t: [str(c[1]) for c in conn.execute(f"PRAGMA table_info({t})")] for t in _tables(conn)
        }
        counts: dict[str, int] = {}
        with db.tx(conn):
            for line in fh:
                item = json.loads(line)
                table = str(item["table"])
                if table not in columns:
                    continue  # a table that no longer exists
                row = {k: v for k, v in item["row"].items() if k in columns[table]}
                cols = ", ".join(row)
                marks = ", ".join("?" for _ in row)
                conn.execute(
                    f"INSERT OR REPLACE INTO {table}({cols}) VALUES ({marks})", tuple(row.values())
                )
                counts[table] = counts.get(table, 0) + 1
        conn.close()
    return counts
