# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""SQLite persistence: schema migrations, transactions, work state (REQ-DB-1, REQ-DB-2)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

WORK_STATES = frozenset({"pending", "done", "stale", "failed", "skipped"})

MIGRATIONS: list[str] = [
    """
    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE projects (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL, web_url TEXT NOT NULL,
        last_activity_at TEXT, archived INTEGER NOT NULL DEFAULT 0,
        window_mrs INTEGER, window_notes INTEGER, selected INTEGER NOT NULL DEFAULT 0,
        skip_reason TEXT, discovered_at TEXT NOT NULL
    );
    CREATE TABLE users (
        id INTEGER PRIMARY KEY, username TEXT NOT NULL, name TEXT NOT NULL,
        kind TEXT NOT NULL, web_url TEXT
    );
    CREATE TABLE pseudonyms (user_id INTEGER PRIMARY KEY, label TEXT NOT NULL UNIQUE);
    CREATE TABLE merge_requests (
        project_id INTEGER NOT NULL, iid INTEGER NOT NULL, id INTEGER NOT NULL,
        title TEXT NOT NULL, state TEXT NOT NULL, author_id INTEGER,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, merged_at TEXT, closed_at TEXT,
        web_url TEXT NOT NULL, user_notes_count INTEGER, fetched_at TEXT NOT NULL,
        PRIMARY KEY (project_id, iid)
    );
    CREATE TABLE discussions (
        id TEXT PRIMARY KEY, project_id INTEGER NOT NULL, mr_iid INTEGER NOT NULL,
        individual_note INTEGER NOT NULL
    );
    CREATE TABLE notes (
        id INTEGER PRIMARY KEY, discussion_id TEXT NOT NULL, project_id INTEGER NOT NULL,
        mr_iid INTEGER NOT NULL, author_id INTEGER, body TEXT NOT NULL, created_at TEXT NOT NULL,
        updated_at TEXT, system INTEGER NOT NULL, type TEXT, resolvable INTEGER NOT NULL,
        resolved INTEGER NOT NULL, resolved_by_id INTEGER, resolved_at TEXT,
        new_path TEXT, old_path TEXT, new_line INTEGER, old_line INTEGER, head_sha TEXT
    );
    CREATE INDEX notes_by_discussion ON notes(discussion_id, created_at);
    CREATE TABLE approvals (
        project_id INTEGER NOT NULL, mr_iid INTEGER NOT NULL, user_id INTEGER NOT NULL,
        PRIMARY KEY (project_id, mr_iid, user_id)
    );
    CREATE TABLE mr_versions (
        project_id INTEGER NOT NULL, mr_iid INTEGER NOT NULL, version_id INTEGER NOT NULL,
        head_sha TEXT, base_sha TEXT, created_at TEXT NOT NULL, diffs_complete INTEGER NOT NULL,
        PRIMARY KEY (project_id, mr_iid, version_id)
    );
    CREATE TABLE version_diffs (
        project_id INTEGER NOT NULL, mr_iid INTEGER NOT NULL, version_id INTEGER NOT NULL,
        new_path TEXT NOT NULL, old_path TEXT, diff TEXT NOT NULL,
        PRIMARY KEY (project_id, mr_iid, version_id, new_path)
    );
    CREATE TABLE mr_commits (
        project_id INTEGER NOT NULL, mr_iid INTEGER NOT NULL, sha TEXT NOT NULL,
        author_name TEXT, created_at TEXT, title TEXT,
        PRIMARY KEY (project_id, mr_iid, sha)
    );
    CREATE TABLE gaps (
        scope TEXT NOT NULL, ref TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL,
        recorded_at TEXT NOT NULL, PRIMARY KEY (scope, ref, kind, detail)
    );
    CREATE TABLE work (
        kind TEXT NOT NULL, key TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL,
        input_hash TEXT, last_error TEXT, updated_at TEXT NOT NULL, PRIMARY KEY (kind, key)
    );
    CREATE TABLE threads (
        id TEXT PRIMARY KEY, project_id INTEGER NOT NULL, mr_iid INTEGER NOT NULL,
        first_note_id INTEGER NOT NULL, giver_id INTEGER, giver_kind TEXT NOT NULL,
        recipient_id INTEGER, responders TEXT NOT NULL, created_at TEXT NOT NULL,
        last_note_at TEXT NOT NULL, n_notes INTEGER NOT NULL, n_human_notes INTEGER NOT NULL,
        has_reply INTEGER NOT NULL, substantive INTEGER NOT NULL, reason TEXT NOT NULL,
        resolvable INTEGER NOT NULL, resolved INTEGER NOT NULL, resolved_at TEXT,
        resolved_by_id INTEGER, new_path TEXT, new_line INTEGER, input_hash TEXT NOT NULL
    );
    CREATE TABLE classifications (
        thread_id TEXT PRIMARY KEY, input_hash TEXT NOT NULL, prompt_version TEXT NOT NULL,
        schema_version TEXT NOT NULL, model TEXT NOT NULL, model_digest TEXT,
        status TEXT NOT NULL, result_json TEXT, error TEXT, raw_excerpt TEXT,
        attempts INTEGER NOT NULL, duration_s REAL, created_at TEXT NOT NULL
    );
    CREATE TABLE findings (
        thread_id TEXT NOT NULL, idx INTEGER NOT NULL, summary TEXT NOT NULL,
        intent TEXT NOT NULL, actionability TEXT NOT NULL, validity TEXT NOT NULL,
        tone TEXT NOT NULL, criticism_target TEXT NOT NULL, responses TEXT NOT NULL,
        text_outcome TEXT NOT NULL, outcome TEXT NOT NULL, verification TEXT NOT NULL,
        code_changed_after INTEGER NOT NULL, censored TEXT, deferral_ref TEXT,
        decision_note_id INTEGER, evidence_note_ids TEXT NOT NULL, rationale TEXT NOT NULL,
        abstained INTEGER NOT NULL, timings TEXT NOT NULL, evaluated_at TEXT NOT NULL,
        PRIMARY KEY (thread_id, idx)
    );
    """,
    """
    ALTER TABLE threads ADD COLUMN llm_hash TEXT NOT NULL DEFAULT '';
    ALTER TABLE findings ADD COLUMN evidence_level TEXT NOT NULL DEFAULT 'none';
    ALTER TABLE projects ADD COLUMN focus_mrs INTEGER NOT NULL DEFAULT 0;
    CREATE TABLE classification_failures (
        thread_id TEXT PRIMARY KEY, cache_key TEXT NOT NULL, status TEXT NOT NULL,
        attempts INTEGER NOT NULL, error TEXT, raw_excerpt TEXT, created_at TEXT NOT NULL
    );
    """,
]


@dataclass(frozen=True)
class Work:
    """One row of the work table."""

    kind: str
    key: str
    status: str
    attempts: int
    input_hash: str | None
    last_error: str | None


def utcnow() -> str:
    """Current time as an ISO 8601 UTC string."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the database and apply pending migrations."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version > len(MIGRATIONS):
        conn.close()
        raise RuntimeError(f"database schema {version} is newer than this program")
    for number in range(version, len(MIGRATIONS)):
        conn.executescript(
            "BEGIN;" + MIGRATIONS[number] + f"PRAGMA user_version = {number + 1};COMMIT;"
        )
    return conn


@contextmanager
def tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block in one write transaction; roll back on any error."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return str(row[0]) if row else default


def set_work(
    conn: sqlite3.Connection,
    kind: str,
    key: str,
    status: str,
    input_hash: str | None = None,
    error: str | None = None,
) -> None:
    """Insert or update a work item. A failure increments the attempt counter."""
    if status not in WORK_STATES:
        raise ValueError(f"unknown work status {status!r}")
    inc = 1 if status == "failed" else 0
    conn.execute(
        """
        INSERT INTO work(kind, key, status, attempts, input_hash, last_error, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(kind, key) DO UPDATE SET status=excluded.status,
            attempts=work.attempts + ?, input_hash=COALESCE(excluded.input_hash, work.input_hash),
            last_error=excluded.last_error, updated_at=excluded.updated_at
        """,
        (kind, key, status, inc, input_hash, error, utcnow(), inc),
    )


def get_work(conn: sqlite3.Connection, kind: str, key: str) -> Work | None:
    row = conn.execute(
        "SELECT kind, key, status, attempts, input_hash, last_error FROM work WHERE kind=? AND key=?",
        (kind, key),
    ).fetchone()
    return Work(*row) if row else None


def work_summary(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """Count work items per kind and status."""
    out: dict[str, dict[str, int]] = {}
    for kind, status, n in conn.execute(
        "SELECT kind, status, COUNT(*) FROM work GROUP BY kind, status ORDER BY kind, status"
    ):
        out.setdefault(kind, {})[status] = n
    return out


def record_gap(conn: sqlite3.Connection, scope: str, ref: str, kind: str, detail: str) -> None:
    """Record a data gap once (an API limit, a missing diff, a partial import)."""
    conn.execute(
        "INSERT OR IGNORE INTO gaps(scope, ref, kind, detail, recorded_at) VALUES (?, ?, ?, ?, ?)",
        (scope, ref, kind, detail, utcnow()),
    )
