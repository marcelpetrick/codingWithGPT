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
    indirect: str | None = None
    for v in later:
        cur = diffs(v["version_id"])
        if path:
            old, new = base_diffs.get(path), cur.get(path)
            if old == new:
                continue
            if old is None or new is None or not line:
                indirect = indirect or v["created_at"]
                continue
            old_lines, new_lines = new_side_lines(old), new_side_lines(new)
            near = window(old_lines, int(line), LINE_RADIUS)
            surviving = set(new_lines.values())
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
        "SELECT id, author_id, created_at FROM notes WHERE discussion_id=? AND system=0 "
        "ORDER BY created_at, id",
        (thread["id"],),
    ).fetchall()
    kinds = {r[0]: r[1] for r in conn.execute("SELECT id, kind FROM users")}
    start = thread["created_at"]
    times = {n["id"]: n["created_at"] for n in notes}
    first_response = next(
        (
            n["created_at"]
            for n in notes[1:]
            if n["author_id"] != thread["giver_id"] and kinds.get(n["author_id"]) != "bot"
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


def run_evaluate(conn: sqlite3.Connection, cfg: Config) -> dict[str, int]:
    """Rebuild the findings table from valid classifications. Returns counts per outcome."""
    cutoff = db.get_meta(conn, "snapshot_at")
    if cutoff is None:
        raise RuntimeError("no snapshot: run collect first")
    cal = BusinessCalendar(
        cfg.zone(), cfg.business_start_hour, cfg.business_end_hour, frozenset(cfg.holidays)
    )
    rows = conn.execute("""SELECT t.*, c.result_json, m.state AS mr_state FROM threads t
        JOIN classifications c ON c.thread_id = t.id AND c.status = 'ok' AND c.input_hash = t.input_hash
        JOIN merge_requests m ON m.project_id = t.project_id AND m.iid = t.mr_iid
        WHERE t.substantive = 1""").fetchall()
    counts: dict[str, int] = {}
    now = db.utcnow()
    with db.tx(conn):
        conn.execute("DELETE FROM findings")
        for t in rows:
            ev = code_evidence(conn, t)
            for idx, f in enumerate(json.loads(t["result_json"])):
                outcome, verification = decide(f["text_outcome"], f["abstain"], ev)
                cens = censoring(outcome, t["mr_state"], t["last_note_at"], cutoff, cfg.censor_days)
                tm = timings(conn, t, f, cal, ev, outcome, cutoff)
                conn.execute(
                    """INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        t["id"],
                        idx,
                        f["summary"],
                        f["intent"],
                        f["actionability"],
                        f["validity"],
                        f["tone"],
                        f["criticism_target"],
                        json.dumps({"acts": f["responses"], "primary": f["primary_response"]}),
                        f["text_outcome"],
                        outcome,
                        verification,
                        int(ev.level in ("direct", "indirect")),
                        cens,
                        f["deferral_ref"],
                        f["decision_note_id"],
                        json.dumps(f["evidence_note_ids"]),
                        f["rationale"],
                        int(f["abstain"]),
                        json.dumps(tm),
                        now,
                    ),
                )
                counts[outcome] = counts.get(outcome, 0) + 1
        db.set_meta(conn, "evaluated_at", now)
    return counts
