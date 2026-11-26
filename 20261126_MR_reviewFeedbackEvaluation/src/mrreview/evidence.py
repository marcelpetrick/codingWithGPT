# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Code evidence through the GitLab compare API (REQ-OUT-1).

For each diff comment, compare the commit the comment was written on (position head_sha) with the
final version of the MR. GitLab can drop the stored diffs of old MR versions; the compare API still
answers, because GitLab keeps the MR commits reachable.
"""

from __future__ import annotations

import sqlite3

from mrreview import db
from mrreview.collect import StopRun
from mrreview.gitlab import GitLabClient, JSONDict, NotAccessible
from mrreview.http import HttpError, TransportError

MAX_FILE_DIFF_BYTES = 200_000


def _targets(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT t.id, t.project_id, t.mr_iid, t.new_path, n.old_path, n.head_sha AS from_sha,
        (SELECT v.head_sha FROM mr_versions v WHERE v.project_id=t.project_id AND v.mr_iid=t.mr_iid
         ORDER BY v.created_at DESC, v.version_id DESC LIMIT 1) AS to_sha,
        (SELECT v.created_at FROM mr_versions v WHERE v.project_id=t.project_id AND v.mr_iid=t.mr_iid
         ORDER BY v.created_at DESC, v.version_id DESC LIMIT 1) AS to_created_at
        FROM threads t JOIN notes n ON n.id = t.first_note_id
        WHERE t.substantive = 1 AND t.new_path IS NOT NULL AND n.head_sha IS NOT NULL"""
    ).fetchall()


def _file_diff(diffs: list[JSONDict], path: str, old_path: str | None) -> JSONDict | None:
    for d in diffs:
        if d.get("new_path") == path or d.get("old_path") in (path, old_path):
            return d
    return None


def run_evidence(client: GitLabClient, conn: sqlite3.Connection) -> dict[str, int]:
    """Fetch the compare diff for every diff comment that has none for its current versions."""
    stats = {"fetched": 0, "ok": 0, "same": 0, "unavailable": 0, "failed": 0}
    cache: dict[tuple[int, str, str], list[JSONDict] | None] = {}
    errors: dict[tuple[int, str, str], str] = {}
    for t in _targets(conn):
        if not t["to_sha"]:
            continue
        key = f"{t['from_sha']}|{t['to_sha']}"
        w = db.get_work(conn, "evidence", t["id"])
        if w is not None and w.status == "done" and w.input_hash == key:
            continue
        stats["fetched"] += 1
        status, changed, text, detail = "same", 0, "", None
        if t["from_sha"] != t["to_sha"]:
            ck = (int(t["project_id"]), str(t["from_sha"]), str(t["to_sha"]))
            if ck not in cache:
                try:
                    cache[ck] = list(client.compare(*ck).get("diffs") or [])
                except NotAccessible as exc:  # final: the commits are gone or not visible
                    cache[ck] = None
                    errors[ck] = str(exc)[:200]
                except HttpError as exc:  # temporary: retried on the next run
                    with db.tx(conn):
                        db.set_work(
                            conn,
                            "evidence",
                            t["id"],
                            "failed",
                            input_hash=key,
                            error=str(exc)[:300],
                        )
                    stats["failed"] += 1
                    continue
                except TransportError as exc:
                    raise StopRun(f"GitLab unreachable, evidence stopped: {exc}") from None
            diffs = cache[ck]
            if diffs is None:
                status, detail = "unavailable", errors[ck]
            else:
                status = "ok"
                d = _file_diff(diffs, t["new_path"], t["old_path"])
                if d is not None:
                    changed = 1
                    text = str(d.get("diff") or "")
                    too_big = d.get("too_large") or d.get("collapsed")
                    if too_big or len(text.encode()) > MAX_FILE_DIFF_BYTES:
                        text, detail = "", "diff too large: only the file change is known"
        _store(conn, t, key, status, changed, text, detail)
        stats[status] += 1
    return stats


def _store(
    conn: sqlite3.Connection,
    t: sqlite3.Row,
    key: str,
    status: str,
    changed: int,
    text: str,
    detail: str | None,
) -> None:
    with db.tx(conn):
        conn.execute(
            "INSERT OR REPLACE INTO code_changes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                t["id"],
                t["from_sha"],
                t["to_sha"],
                t["to_created_at"],
                status,
                changed,
                text,
                detail,
                db.utcnow(),
            ),
        )
        if status == "unavailable":
            db.record_gap(conn, "thread", t["id"], "compare_unavailable", detail or "")
        db.set_work(conn, "evidence", t["id"], "done", input_hash=key)
