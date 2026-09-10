# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""SQLite archive of normalised events.

The archive makes restarts instant (files are tailed from their last offset)
and keeps history after Claude Code deletes old transcripts. Duplicate records
are merged by key, keeping the copy with the larger total: Claude writes
streaming copies of a message before the final one.
"""

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tokenusage2.model import Account, Event, QuotaWindow, Tool, Usage

SCHEMA_VERSION = 3
_TOOLS = {tool.value: tool for tool in Tool}
_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY, account TEXT NOT NULL, inode INTEGER NOT NULL,
    size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, offset INTEGER NOT NULL,
    ctx TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(
    key TEXT PRIMARY KEY, ts REAL NOT NULL, tool TEXT NOT NULL, account TEXT NOT NULL,
    model TEXT NOT NULL, route TEXT NOT NULL, project TEXT NOT NULL, session TEXT NOT NULL,
    input INTEGER NOT NULL, cache_read INTEGER NOT NULL, cache_write INTEGER NOT NULL,
    output INTEGER NOT NULL, reasoning INTEGER NOT NULL, unsplit INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS events_account_ts ON events(account, ts);
CREATE TABLE IF NOT EXISTS quotas(
    account TEXT NOT NULL, window TEXT NOT NULL, used_percent REAL NOT NULL,
    resets_at REAL, observed_at REAL NOT NULL, source TEXT NOT NULL, plan TEXT,
    PRIMARY KEY(account, window));
CREATE TABLE IF NOT EXISTS accounts(
    id TEXT PRIMARY KEY, tool TEXT NOT NULL, label TEXT NOT NULL, home TEXT NOT NULL,
    identity TEXT, plan TEXT, last_seen REAL NOT NULL);
"""
_TOTAL = "{t}.input + {t}.cache_read + {t}.cache_write + {t}.output + {t}.unsplit"
_UPSERT = f"""
INSERT INTO events(key, ts, tool, account, model, route, project, session,
                   input, cache_read, cache_write, output, reasoning, unsplit)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(key) DO UPDATE SET
    ts = excluded.ts, model = excluded.model, route = excluded.route,
    project = excluded.project, session = excluded.session,
    input = excluded.input, cache_read = excluded.cache_read,
    cache_write = excluded.cache_write, output = excluded.output,
    reasoning = excluded.reasoning, unsplit = excluded.unsplit
WHERE {_TOTAL.format(t="excluded")} > {_TOTAL.format(t="events")}
"""


class StoreError(RuntimeError):
    """The archive exists but cannot be used by this version."""


_OWN_CLAUDE_PREFIX = "substr(key, 1, length(account) + 8) = 'claude:' || account || ':'"


def _claude_keys_without_account(conn: sqlite3.Connection) -> None:
    """Schema 1 → 2: Claude keys drop the account, so a copied home collapses.

    Where two homes held the same message, the first renamed row wins and the
    other, which could not take the shared key, is removed.
    """
    conn.execute(
        "UPDATE OR IGNORE events SET key = 'claude:' || substr(key, length(account) + 9) "
        f"WHERE tool = 'claude' AND {_OWN_CLAUDE_PREFIX}"
    )
    conn.execute(f"DELETE FROM events WHERE tool = 'claude' AND {_OWN_CLAUDE_PREFIX}")


def _backend_becomes_route(conn: sqlite3.Connection) -> None:
    """Schema 2 → 3: store what the log says, not a display label.

    Labels are resolved when displaying, so config and launcher changes relabel
    history. Claude rows keep only whether Anthropic's API answered.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
    if "backend" in columns:
        conn.execute("ALTER TABLE events RENAME COLUMN backend TO route")
    conn.execute(
        "UPDATE events SET route = CASE WHEN route = 'anthropic' THEN 'anthropic' ELSE '' END "
        "WHERE tool = 'claude'"
    )


#: ``MIGRATIONS[n]`` upgrades an archive from schema ``n`` to ``n + 1``.
MIGRATIONS = {1: _claude_keys_without_account, 2: _backend_becomes_route}


@dataclass(slots=True)
class FileState:
    path: str
    account: str
    inode: int
    size: int
    mtime_ns: int
    offset: int
    ctx: dict


def _row(event: Event) -> tuple:
    u = event.usage
    return (
        event.key,
        event.ts,
        str(event.tool),
        event.account,
        event.model,
        event.route,
        event.project,
        event.session,
        u.input,
        u.cache_read,
        u.cache_write,
        u.output,
        u.reasoning,
        u.unsplit,
    )


class Store:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.conn = sqlite3.connect(str(path) if path else ":memory:", timeout=5.0)
        if path is not None:
            self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        stored = self.get_meta("schema")
        if stored is not None:
            version = int(stored) if stored.isdigit() else -1
            while version < SCHEMA_VERSION and version in MIGRATIONS:
                MIGRATIONS[version](self.conn)
                version += 1
            if version != SCHEMA_VERSION:
                self.conn.close()
                raise StoreError(
                    f"archive schema {stored} is not supported (expected "
                    f"{SCHEMA_VERSION}); move {path} aside to rebuild it"
                )
        self.set_meta("schema", str(SCHEMA_VERSION))
        self.commit()

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def get_meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def load_file_states(self) -> dict[str, FileState]:
        rows = self.conn.execute(
            "SELECT path, account, inode, size, mtime_ns, offset, ctx FROM files"
        )
        return {row[0]: FileState(*row[:6], json.loads(row[6])) for row in rows}

    def save_file_state(self, state: FileState) -> None:
        self.conn.execute(
            "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET "
            "account = excluded.account, inode = excluded.inode, size = excluded.size, "
            "mtime_ns = excluded.mtime_ns, offset = excluded.offset, ctx = excluded.ctx",
            (
                state.path,
                state.account,
                state.inode,
                state.size,
                state.mtime_ns,
                state.offset,
                json.dumps(state.ctx, sort_keys=True),
            ),
        )

    def upsert_events(self, events: Iterable[Event]) -> int:
        before = self.conn.total_changes
        self.conn.executemany(_UPSERT, (_row(event) for event in events))
        return self.conn.total_changes - before

    def delete_events(self, key_prefix: str, min_ts: float) -> int:
        escaped = key_prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cursor = self.conn.execute(
            "DELETE FROM events WHERE key LIKE ? ESCAPE '\\' AND ts >= ?", (escaped + "%", min_ts)
        )
        return cursor.rowcount

    def load_events(self) -> list[Event]:
        rows = self.conn.execute(
            "SELECT key, ts, tool, account, model, route, project, session, input, "
            "cache_read, cache_write, output, reasoning, unsplit FROM events ORDER BY ts"
        )
        return [
            Event(r[0], r[1], _TOOLS[r[2]], r[3], r[4], r[5], r[6], r[7], Usage(*r[8:]))
            for r in rows
        ]

    def upsert_quotas(self, quotas: Iterable[QuotaWindow]) -> int:
        before = self.conn.total_changes
        self.conn.executemany(
            "INSERT INTO quotas VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(account, window) "
            "DO UPDATE SET used_percent = excluded.used_percent, resets_at = excluded.resets_at,"
            " observed_at = excluded.observed_at, source = excluded.source, plan = excluded.plan"
            " WHERE excluded.observed_at > quotas.observed_at",
            (
                (q.account, q.window, q.used_percent, q.resets_at, q.observed_at, q.source, q.plan)
                for q in quotas
            ),
        )
        return self.conn.total_changes - before

    def load_quotas(self) -> list[QuotaWindow]:
        rows = self.conn.execute(
            "SELECT account, window, used_percent, resets_at, observed_at,"
            " source, plan FROM quotas ORDER BY account, window"
        )
        return [QuotaWindow(*row) for row in rows]

    def upsert_accounts(self, accounts: Iterable[Account], now: float) -> None:
        self.conn.executemany(
            "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "label = excluded.label, home = excluded.home, identity = excluded.identity, "
            "plan = excluded.plan, last_seen = excluded.last_seen",
            ((a.id, str(a.tool), a.label, str(a.home), a.identity, a.plan, now) for a in accounts),
        )

    def load_accounts(self) -> list[Account]:
        rows = self.conn.execute(
            "SELECT id, tool, label, home, identity, plan FROM accounts ORDER BY id"
        )
        return [Account(r[0], Tool(r[1]), Path(r[3]), r[2], r[4], r[5], "archive") for r in rows]

    def event_counts(self) -> dict[str, tuple[int, float, float]]:
        rows = self.conn.execute(
            "SELECT account, COUNT(*), MIN(ts), MAX(ts) FROM events GROUP BY account"
        )
        return {row[0]: (row[1], row[2], row[3]) for row in rows}
