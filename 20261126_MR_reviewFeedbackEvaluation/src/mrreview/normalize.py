# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn stored discussions into review threads with roles (REQ-UNIT-1, REQ-UNIT-2).

A thread is the unit of analysis. This step is deterministic; the LLM refines it later.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

from mrreview import db
from mrreview.textutil import is_routine

NORMALIZER_VERSION = "n1"


@dataclass(frozen=True)
class NoteRow:
    id: int
    author_id: int | None
    body: str
    created_at: str
    updated_at: str | None
    system: bool
    resolvable: bool
    resolved: bool
    resolved_at: str | None
    resolved_by_id: int | None
    new_path: str | None
    new_line: int | None


def _kind(kinds: dict[int, str], uid: int | None) -> str:
    return "deleted" if uid is None else kinds.get(uid, "deleted")


def classify_thread(
    notes: list[NoteRow], mr_author: int | None, kinds: dict[int, str], title: str = ""
) -> dict[str, object] | None:
    """Derive the thread record from its notes, or None for a system-only discussion."""
    visible = [n for n in notes if not n.system]
    if not visible:
        return None
    first = visible[0]
    giver = first.author_id
    giver_kind = _kind(kinds, giver)
    humans = [n for n in visible if _kind(kinds, n.author_id) in ("human", "deleted")]
    others = [n for n in humans if n.author_id != giver]
    responders: list[int] = []
    for n in others:
        if n.author_id is not None and n.author_id not in responders:
            responders.append(n.author_id)
    if giver_kind == "bot":
        # An automated review that a human reacted to is review interaction too; it stays labelled.
        reason = "bot_review" if others and not is_routine(first.body) else "bot_initiated"
    elif all(is_routine(n.body) for n in humans):
        reason = "routine_only"
    elif giver == mr_author and not others:
        reason = "author_self_note"
    else:
        reason = "substantive"
    recipient = mr_author if giver != mr_author else (responders[0] if responders else None)
    resolvable_notes = [n for n in visible if n.resolvable]
    resolved = bool(resolvable_notes) and all(n.resolved for n in resolvable_notes)
    resolved_times = [n.resolved_at for n in resolvable_notes if n.resolved_at]
    resolved_by = next(
        (n.resolved_by_id for n in reversed(resolvable_notes) if n.resolved_by_id), None
    )
    digest = hashlib.sha256(
        json.dumps(
            [NORMALIZER_VERSION, mr_author]
            + [
                [
                    n.id,
                    n.author_id,
                    n.body,
                    n.created_at,
                    n.updated_at,
                    n.resolved,
                    n.new_path,
                    n.new_line,
                ]
                for n in visible
            ],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    return {
        "first_note_id": first.id,
        "giver_id": giver,
        "giver_kind": giver_kind,
        "recipient_id": recipient,
        "responders": json.dumps(responders),
        "created_at": first.created_at,
        "last_note_at": max(n.created_at for n in visible),
        "n_notes": len(visible),
        "n_human_notes": len(humans),
        "has_reply": int(bool(others)),
        "substantive": int(reason in ("substantive", "bot_review")),
        "reason": reason,
        "resolvable": int(bool(resolvable_notes)),
        "resolved": int(resolved),
        "resolved_at": max(resolved_times) if resolved and resolved_times else None,
        "resolved_by_id": resolved_by if resolved else None,
        "new_path": first.new_path,
        "new_line": first.new_line,
        "input_hash": digest,
        "llm_hash": _llm_hash(visible, mr_author, title),
    }


def _llm_hash(visible: list[NoteRow], mr_author: int | None, title: str) -> str:
    """Hash of what the LLM sees. Resolution changes do not change it (no needless re-classification)."""
    payload = [NORMALIZER_VERSION, mr_author, title] + [
        [n.id, n.author_id, n.body, n.created_at, n.new_path, n.new_line] for n in visible
    ]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def build_threads(conn: sqlite3.Connection) -> dict[str, int]:
    """Rebuild the threads table from collected notes. Returns counts per reason."""
    kinds = {int(r[0]): str(r[1]) for r in conn.execute("SELECT id, kind FROM users")}
    authors = {
        (r[0], r[1]): (r[2], r[3])
        for r in conn.execute("SELECT project_id, iid, author_id, title FROM merge_requests")
    }
    rows = conn.execute(
        """SELECT d.id, d.project_id, d.mr_iid, n.id, n.author_id, n.body, n.created_at, n.updated_at,
        n.system, n.resolvable, n.resolved, n.resolved_at, n.resolved_by_id, n.new_path, n.new_line
        FROM discussions d JOIN notes n ON n.discussion_id = d.id
        ORDER BY d.id, n.created_at, n.id"""
    ).fetchall()
    grouped: dict[str, tuple[int, int, list[NoteRow]]] = {}
    for r in rows:
        entry = grouped.setdefault(r[0], (r[1], r[2], []))
        entry[2].append(
            NoteRow(
                r[3],
                r[4],
                r[5],
                r[6],
                r[7],
                bool(r[8]),
                bool(r[9]),
                bool(r[10]),
                r[11],
                r[12],
                r[13],
                r[14],
            )
        )
    counts: dict[str, int] = {}
    with db.tx(conn):
        keep: set[str] = set()
        for did, (pid, iid, notes) in grouped.items():
            author, title = authors.get((pid, iid), (None, ""))
            rec = classify_thread(notes, author, kinds, title)
            if rec is None:
                continue
            keep.add(did)
            counts[str(rec["reason"])] = counts.get(str(rec["reason"]), 0) + 1
            cols = ", ".join(rec)
            marks = ", ".join("?" for _ in rec)
            updates = ", ".join(f"{k}=excluded.{k}" for k in rec)
            conn.execute(
                f"INSERT INTO threads(id, project_id, mr_iid, {cols}) VALUES (?, ?, ?, {marks}) "
                f"ON CONFLICT(id) DO UPDATE SET {updates}",
                (did, pid, iid, *rec.values()),
            )
        # Upgrade path (schema 1 -> 2): classifications keyed by the old full hash move to llm_hash.
        conn.execute(
            """UPDATE classifications SET input_hash = (SELECT llm_hash FROM threads t
            WHERE t.id = classifications.thread_id) WHERE EXISTS (SELECT 1 FROM threads t
            WHERE t.id = classifications.thread_id AND t.input_hash = classifications.input_hash)"""
        )
        for (tid,) in conn.execute("SELECT id FROM threads").fetchall():
            if tid not in keep:
                conn.execute("DELETE FROM threads WHERE id=?", (tid,))
                conn.execute("DELETE FROM findings WHERE thread_id=?", (tid,))
                conn.execute("DELETE FROM classifications WHERE thread_id=?", (tid,))
    return counts
