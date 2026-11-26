# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export the analysed data as one JSON-ready dict for the dashboard (REQ-UI-*, REQ-DB-3).

Names and usernames inside free text are replaced by tokens ⟦u:ID⟧. The dashboard shows a
pseudonym or the real name for each token, depending on the identity toggle.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from mrreview import __version__, db, llm
from mrreview.collect import collect_summary
from mrreview.config import Config
from mrreview.demo.fake_ollama import STUB_MODEL
from mrreview.identity import label_for, mask_names
from mrreview.textutil import truncate

EXCERPT_GRAPHEMES = 320
_TIMING_KEYS = {
    "first_response": "fr",
    "decision": "de",
    "implementation": "im",
    "resolution": "re",
}


def _tm(value: dict[str, Any]) -> list[Any]:
    state = value.get("state")
    if state == "observed":
        return ["o", value["wall_h"], value["biz_h"]]
    if state == "pending":
        return ["p", value["open_h"]]
    return ["n"]


def build_dataset(conn: sqlite3.Connection, cfg: Config) -> dict[str, Any]:
    """Collect everything the dashboard needs. The result is plain JSON data."""
    users = {r["id"]: r for r in conn.execute("SELECT * FROM users")}
    names = {uid: (r["username"], r["name"]) for uid, r in users.items() if r["kind"] != "bot"}

    def mask(text: str, limit: int) -> str:
        return truncate(mask_names(text, names), limit)

    projects = [
        dict(r)
        for r in conn.execute(
            "SELECT id, name, path, web_url, last_activity_at, window_mrs, window_notes, selected, skip_reason "
            "FROM projects ORDER BY path"
        )
    ]
    mrs = []
    for r in conn.execute("SELECT * FROM merge_requests ORDER BY project_id, iid"):
        n_appr = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE project_id=? AND mr_iid=?",
            (r["project_id"], r["iid"]),
        ).fetchone()[0]
        mrs.append(
            {
                "p": r["project_id"],
                "iid": r["iid"],
                "title": mask(r["title"], 160),
                "state": r["state"],
                "created": r["created_at"],
                "merged": r["merged_at"],
                "url": r["web_url"],
                "author": r["author_id"],
                "approvals": n_appr,
            }
        )
    mr_url = {(m["p"], m["iid"]): m["url"] for m in mrs}
    cls = {
        r["thread_id"]: r["status"]
        for r in conn.execute("SELECT thread_id, status FROM classifications")
    }
    threads = []
    seen_users: set[int] = set()
    for r in conn.execute("SELECT * FROM threads ORDER BY created_at, id"):
        body = conn.execute("SELECT body FROM notes WHERE id=?", (r["first_note_id"],)).fetchone()[
            0
        ]
        responders = json.loads(r["responders"])
        for uid in [r["giver_id"], r["recipient_id"], *responders]:
            if uid is not None:
                seen_users.add(uid)
        hashed = conn.execute(
            "SELECT input_hash FROM classifications WHERE thread_id=?", (r["id"],)
        ).fetchone()
        status = cls.get(r["id"], "pending") if r["substantive"] else "not_needed"
        if status == "ok" and hashed and hashed[0] != r["input_hash"]:
            status = "stale"
        threads.append(
            {
                "id": r["id"],
                "p": r["project_id"],
                "iid": r["mr_iid"],
                "url": f"{mr_url.get((r['project_id'], r['mr_iid']), '')}#note_{r['first_note_id']}",
                "giver": r["giver_id"],
                "gk": r["giver_kind"],
                "rec": r["recipient_id"],
                "resp": responders,
                "created": r["created_at"],
                "last": r["last_note_at"],
                "n": r["n_notes"],
                "reply": bool(r["has_reply"]),
                "reason": r["reason"],
                "resolvable": bool(r["resolvable"]),
                "resolved": bool(r["resolved"]),
                "resolvedAt": r["resolved_at"],
                "path": r["new_path"],
                "line": r["new_line"],
                "cls": status,
                "excerpt": mask(body, EXCERPT_GRAPHEMES),
            }
        )
    findings = []
    for r in conn.execute("SELECT * FROM findings ORDER BY thread_id, idx"):
        resp = json.loads(r["responses"])
        tm = json.loads(r["timings"])
        findings.append(
            {
                "t": r["thread_id"],
                "i": r["idx"],
                "summary": mask(r["summary"], 200),
                "intent": r["intent"],
                "act": r["actionability"],
                "validity": r["validity"],
                "tone": r["tone"],
                "target": r["criticism_target"],
                "primary": resp["primary"],
                "acts": [a["act"] for a in resp["acts"]],
                "text": r["text_outcome"],
                "outcome": r["outcome"],
                "ver": r["verification"],
                "changed": bool(r["code_changed_after"]),
                "cens": r["censored"],
                "ref": r["deferral_ref"],
                "decision": r["decision_note_id"],
                "evidence": json.loads(r["evidence_note_ids"]),
                "why": mask(r["rationale"], 500),
                "abstain": bool(r["abstained"]),
                "tm": {_TIMING_KEYS[k]: _tm(v) for k, v in tm.items()},
            }
        )
    for m in mrs:
        if m["author"] is not None:
            seen_users.add(m["author"])
    seen_users |= set(names)
    with db.tx(conn):
        people = {
            str(uid): {
                "label": label_for(conn, uid) if users[uid]["kind"] == "human" else None,
                "name": users[uid]["name"],
                "username": users[uid]["username"],
                "kind": users[uid]["kind"],
            }
            for uid in sorted(seen_users)
            if uid in users
        }
    summary = collect_summary(conn)
    reasons: dict[str, int] = {}
    for t in threads:
        reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
    statuses: dict[str, int] = {}
    for t in threads:
        if t["reason"] == "substantive":
            statuses[t["cls"]] = statuses.get(t["cls"], 0) + 1
    model = db.get_meta(conn, "ollama_model") or ""
    complete = statuses.get("ok", 0) == reasons.get("substantive", 0) and not any(
        s in summary["work"].get("mr", {}) for s in ("pending", "failed", "stale")
    )
    meta = {
        "tool_version": __version__,
        "generated_at": db.utcnow(),
        "snapshot_at": summary["snapshot_at"],
        "window_start": summary["window_start"],
        "evaluated_at": db.get_meta(conn, "evaluated_at"),
        "model": model,
        "model_digest": db.get_meta(conn, "ollama_digest"),
        "ollama_version": db.get_meta(conn, "ollama_version"),
        "stub": model == STUB_MODEL,
        "prompt_version": llm.PROMPT_VERSION,
        "schema_version": llm.SCHEMA_VERSION,
        "timezone": cfg.timezone,
        "hours": [cfg.business_start_hour, cfg.business_end_hour],
        "holidays": [d.isoformat() for d in cfg.holidays],
        "censor_days": cfg.censor_days,
        "window_months": cfg.window_months,
        "coverage": {
            "projects_visible": summary["projects_visible"],
            "projects_selected": summary["projects_selected"],
            "mrs": summary["mrs"],
            "notes": summary["notes"],
            "gaps": summary["gaps"],
            "work": summary["work"],
            "thread_reasons": reasons,
            "classification": statuses,
            "complete": complete,
        },
    }
    return {
        "meta": meta,
        "projects": projects,
        "people": people,
        "mrs": mrs,
        "threads": threads,
        "findings": findings,
    }
