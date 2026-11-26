# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Outcome verification, censoring and timings per finding (REQ-OUT-1, REQ-OUT-2, REQ-TIME-1).

The text of a thread says what people claim. The MR versions show what changed in the code.
This step keeps both apart and grades the evidence:

- direct: a commented line changed in a later MR version.
- indirect: the commented file (or, for a general comment, any file) changed later.
- textual_only: someone claims a change, but no later version shows one.
- unavailable: the diffs needed to check are missing (an API gap).

A changed line is not proof that the finding was fixed correctly. It is evidence only.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from mrreview import db
from mrreview.bizhours import BusinessCalendar
from mrreview.config import Config
from mrreview.diffs import new_side_lines, window
from mrreview.textutil import is_routine

CHANGE_OUTCOMES = frozenset({"implemented", "alternative_implemented", "partially_implemented"})
TEXT_TO_OUTCOME = {
    "implemented_claimed": "implemented",
    "alternative_claimed": "alternative_implemented",
    "partial_claimed": "partially_implemented",
    "promised": "open",
    "justified_no_change": "justified_no_change",
    "optional_declined": "optional_declined",
    "declined_unjustified": "declined_unjustified",
    "deferred": "deferred",
    "open": "open",
    "unknown": "unknown",
}
DECISION_ACTS = frozenset(
    {
        "agreement",
        "partial_agreement",
        "reasoned_disagreement",
        "explanation",
        "alternative_proposal",
        "unsupported_rejection",
        "deferral",
    }
)
LINE_RADIUS = 2
SHIFT_RADIUS = 60  # a commented line that moved by more lines than this counts as changed


@dataclass(frozen=True)
class Evidence:
    level: str  # direct, indirect, none, unavailable
    at: str | None


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def code_evidence(conn: sqlite3.Connection, thread: sqlite3.Row | dict[str, Any]) -> Evidence:
    """Did the code change after the thread started, and where?"""
    pid, iid, start = thread["project_id"], thread["mr_iid"], thread["created_at"]
    versions = conn.execute(
        "SELECT version_id, created_at, diffs_complete FROM mr_versions WHERE project_id=? AND mr_iid=? "
        "ORDER BY created_at, version_id",
        (pid, iid),
    ).fetchall()
    if not versions:
        return Evidence("unavailable", None)
    before = [v for v in versions if v["created_at"] <= start] or versions[:1]
    base = before[-1]
    head_sha = None
    if "first_note_id" in thread.keys():  # noqa: SIM118 - "in" on a sqlite3.Row tests values
        row = conn.execute(
            "SELECT head_sha FROM notes WHERE id=?", (thread["first_note_id"],)
        ).fetchone()
        head_sha = row[0] if row else None
    if head_sha:  # the version the comment was written on is the exact base
        exact = conn.execute(
            "SELECT version_id, created_at, diffs_complete FROM mr_versions "
            "WHERE project_id=? AND mr_iid=? AND head_sha=?",
            (pid, iid, head_sha),
        ).fetchone()
        base = exact or base
    later = [v for v in versions if v["created_at"] > start]
    if not later:
        return Evidence("none", None)

    def diffs(vid: int) -> dict[str, str]:
        return {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT new_path, diff FROM version_diffs WHERE project_id=? AND mr_iid=? AND version_id=?",
                (pid, iid, vid),
            )
        }

    base_diffs = diffs(base["version_id"])
    incomplete = not base["diffs_complete"] or any(not v["diffs_complete"] for v in later)
    path, line = thread["new_path"], thread["new_line"]
    if path and path not in base_diffs and not base["diffs_complete"]:
        return Evidence("unavailable", None)  # the base diff of the commented file is missing
    indirect: str | None = None
    for v in later:
        cur = diffs(v["version_id"])
        if path:
            old, new = base_diffs.get(path), cur.get(path)
            if old == new:
                continue
            if new is None and not v["diffs_complete"]:
                continue  # missing in an incomplete version: no evidence either way
            if old is None or new is None or not line:
                indirect = indirect or v["created_at"]
                continue
            old_lines, new_lines = new_side_lines(old), new_side_lines(new)
            near = window(old_lines, int(line), LINE_RADIUS)
            surviving = set(window(new_lines, int(line), SHIFT_RADIUS).values())
            if any(text not in surviving for text in near.values()):
                return Evidence("direct", v["created_at"])
            indirect = indirect or v["created_at"]
        elif cur != base_diffs:
            return Evidence("indirect", v["created_at"])
    if indirect:
        return Evidence("indirect", indirect)
    return Evidence("unavailable" if incomplete else "none", None)


def decide(text_outcome: str, abstained: bool, evidence: Evidence) -> tuple[str, str]:
    """Return (outcome, verification) from the stated outcome and the code evidence."""
    if abstained:
        return "unknown", "not_applicable"
    outcome = TEXT_TO_OUTCOME[text_outcome]
    if text_outcome == "promised":
        if evidence.level == "direct":
            return "implemented", "direct"
        return "open", "textual_only"
    if outcome not in CHANGE_OUTCOMES:
        return outcome, "not_applicable"
    if evidence.level in ("direct", "indirect"):
        return outcome, evidence.level
    if evidence.level == "unavailable":
        return outcome, "unavailable"
    return outcome, "textual_only"


def censoring(
    outcome: str, mr_state: str, last_activity: str, cutoff: str, censor_days: int
) -> str | None:
    """'recent' when an open finding is on an open MR with activity in the last censor_days."""
    if outcome not in ("open", "unknown"):
        return None
    if mr_state == "opened" and _dt(cutoff) - _dt(last_activity) <= timedelta(days=censor_days):
        return "recent"
    return None


def _span(cal: BusinessCalendar, start: str, end: str | None, cutoff: str) -> dict[str, Any]:
    if end is None:
        return {
            "state": "pending",
            "open_h": round((_dt(cutoff) - _dt(start)).total_seconds() / 3600, 2),
        }
    s, e = _dt(start), _dt(end)
    e = max(e, s)
    return {
        "state": "observed",
        "wall_h": round((e - s).total_seconds() / 3600, 3),
        "biz_h": round(cal.seconds(s, e) / 3600, 3),
    }


def timings(
    conn: sqlite3.Connection,
    thread: sqlite3.Row,
    finding: dict[str, Any],
    cal: BusinessCalendar,
    evidence: Evidence,
    outcome: str,
    cutoff: str,
) -> dict[str, Any]:
    """Elapsed times from the first note. A missing event is pending, never zero."""
    notes = conn.execute(
        "SELECT id, author_id, created_at, body FROM notes WHERE discussion_id=? AND system=0 "
        "ORDER BY created_at, id",
        (thread["id"],),
    ).fetchall()
    kinds = {r[0]: r[1] for r in conn.execute("SELECT id, kind FROM users")}
    start = thread["created_at"]
    # A decision must come after the opening note and not from the giver (the model can point anywhere).
    times = {
        n["id"]: n["created_at"]
        for n in notes
        if n["created_at"] > start and n["author_id"] != thread["giver_id"]
    }
    first_response = next(
        (
            n["created_at"]
            for n in notes[1:]
            if n["author_id"] != thread["giver_id"]
            and kinds.get(n["author_id"]) != "bot"
            and not is_routine(n["body"])
        ),
        None,
    )
    decision = times.get(finding.get("decision_note_id") or -1)
    if decision is None:
        decision = next(
            (
                times.get(r["note_id"])
                for r in finding.get("responses", [])
                if r["act"] in DECISION_ACTS and r["note_id"] in times
            ),
            None,
        )
    implemented = (
        evidence.at
        if evidence.level in ("direct", "indirect") and (outcome in CHANGE_OUTCOMES)
        else None
    )
    out = {
        "first_response": _span(cal, start, first_response, cutoff),
        "decision": _span(cal, start, decision, cutoff),
        "implementation": (
            _span(cal, start, implemented, cutoff)
            if outcome in CHANGE_OUTCOMES
            else {"state": "n/a"}
        ),
        "resolution": (
            _span(cal, start, thread["resolved_at"], cutoff)
            if thread["resolvable"]
            else {"state": "n/a"}
        ),
    }
    return out


def _role(author: int | None, thread: sqlite3.Row) -> str:
    """Who wrote a response note: the recipient, the giver, or someone else."""
    if author is not None and author == thread["recipient_id"]:
        return "recipient"
    if author is not None and author == thread["giver_id"]:
        return "giver"
    return "other"


def run_evaluate(conn: sqlite3.Connection, cfg: Config) -> dict[str, int]:
    """Rebuild the findings table from valid classifications. Returns counts per outcome."""
    cutoff = db.get_meta(conn, "snapshot_at")
    if cutoff is None:
        raise RuntimeError("no snapshot: run collect first")
    cal = BusinessCalendar(
        cfg.zone(), cfg.business_start_hour, cfg.business_end_hour, frozenset(cfg.holidays)
    )
    rows = conn.execute("""SELECT t.*, c.result_json, m.state AS mr_state FROM threads t
        JOIN classifications c ON c.thread_id = t.id AND c.status = 'ok' AND c.input_hash = t.llm_hash
        JOIN merge_requests m ON m.project_id = t.project_id AND m.iid = t.mr_iid
        WHERE t.substantive = 1""").fetchall()
    counts: dict[str, int] = {}
    now = db.utcnow()
    authors = {int(r[0]): r[1] for r in conn.execute("SELECT id, author_id FROM notes")}
    with db.tx(conn):
        conn.execute("DELETE FROM findings")
        for t in rows:
            ev = code_evidence(conn, t)
            for idx, f in enumerate(json.loads(t["result_json"])):
                outcome, verification = decide(f["text_outcome"], f["abstain"], ev)
                cens = censoring(outcome, t["mr_state"], t["last_note_at"], cutoff, cfg.censor_days)
                tm = timings(conn, t, f, cal, ev, outcome, cutoff)
                acts = [{**r, "by": _role(authors.get(r["note_id"]), t)} for r in f["responses"]]
                row = {
                    "thread_id": t["id"],
                    "idx": idx,
                    "summary": f["summary"],
                    "intent": f["intent"],
                    "actionability": f["actionability"],
                    "validity": f["validity"],
                    "tone": f["tone"],
                    "criticism_target": f["criticism_target"],
                    "responses": json.dumps({"acts": acts, "primary": f["primary_response"]}),
                    "text_outcome": f["text_outcome"],
                    "outcome": outcome,
                    "verification": verification,
                    "code_changed_after": int(ev.level in ("direct", "indirect")),
                    "evidence_level": ev.level,
                    "censored": cens,
                    "deferral_ref": f["deferral_ref"],
                    "decision_note_id": f["decision_note_id"],
                    "evidence_note_ids": json.dumps(f["evidence_note_ids"]),
                    "rationale": f["rationale"],
                    "abstained": int(f["abstain"]),
                    "timings": json.dumps(tm),
                    "evaluated_at": now,
                }
                conn.execute(
                    f"INSERT INTO findings({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})",
                    tuple(row.values()),
                )
                counts[outcome] = counts.get(outcome, 0) + 1
        db.set_meta(conn, "evaluated_at", now)
    return counts
