# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export the analysed data as one JSON-ready dict for the dashboard (REQ-UI-*, REQ-DB-3).

Names and usernames inside free text are replaced by tokens ⟦u:ID⟧. The dashboard shows a
pseudonym or the real name for each token, depending on the identity toggle.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from mrreview import __version__, db, llm
from mrreview.analyze import cache_key, is_current
from mrreview.collect import collect_summary
from mrreview.config import Config
from mrreview.demo.fake_ollama import STUB_MODEL
from mrreview.identity import label_for, mask_exact, mask_names, mask_projects, project_label_for
from mrreview.textutil import is_thanks, reply_words, truncate

EXCERPT_GRAPHEMES = 320
_HALF_TOKEN = re.compile(r"⟦[^⟧]*…$")
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


def _status(
    thread: sqlite3.Row,
    cls: sqlite3.Row | None,
    fail: sqlite3.Row | None,
    model: str,
    digest: str | None = None,
) -> str:
    """Classification state of one thread against the current prompt, schema and model."""
    if not thread["substantive"]:
        return "not_needed"
    key = cache_key(thread["llm_hash"], model)
    if is_current(cls, thread["llm_hash"], model, digest):
        return "ok"
    if fail is not None and fail["cache_key"] == key:
        return str(fail["status"])
    if cls is not None and cls["status"] == "ok":
        return "stale"
    return "pending"


def _partial_reasons(
    conn: sqlite3.Connection, summary: dict[str, Any], statuses: dict[str, int]
) -> list[str]:
    """Why the data is not complete. An empty list means complete."""
    out: list[str] = []
    for status in ("pending", "stale", "failed", "invalid"):
        if statuses.get(status):
            out.append(
                f"{statuses[status]} substantive threads have classification state '{status}'"
            )
    for status in ("pending", "stale", "failed"):
        n = summary["work"].get("mr", {}).get(status)
        if n:
            out.append(f"{n} merge requests are '{status}' in collection")
    n_proj = summary["work"].get("project", {}).get("failed")
    if n_proj:
        out.append(f"{n_proj} projects could not be listed")
    if db.get_meta(conn, "bounded_sample") == "1":
        out.append("bounded sample: --max-projects or --max-mrs limited the collection")
    newest = conn.execute(
        "SELECT MAX(created_at) FROM classifications WHERE status='ok'"
    ).fetchone()[0]
    evaluated = db.get_meta(conn, "evaluated_at")
    if newest and (evaluated is None or newest > evaluated):
        out.append("findings are older than the newest classification: run evaluate")
    return out


def _prefix(text: str, n: int) -> str:
    """The first n characters, extended to the next whitespace, so no word (or name) is cut."""
    if len(text) <= n:
        return text
    end = n
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[:end]


def _focus_user(conn: sqlite3.Connection) -> int | None:
    name = db.get_meta(conn, "focus_username")
    if not name:
        return None
    row = conn.execute("SELECT id FROM users WHERE lower(username)=lower(?)", (name,)).fetchone()
    return int(row[0]) if row else None


def build_dataset(conn: sqlite3.Connection, cfg: Config) -> dict[str, Any]:
    """Collect everything the dashboard needs. The result is plain JSON data."""
    users = {r["id"]: r for r in conn.execute("SELECT * FROM users")}
    names = {uid: (r["username"], r["name"]) for uid, r in users.items() if r["kind"] != "bot"}
    # Bots too (REQ-UI-6, D-019): whole names only, so "CI Bot" does not mask the word "bot".
    bots = {uid: (r["username"], r["name"]) for uid, r in users.items() if r["kind"] == "bot"}

    proj_terms = {
        int(r[0]): (str(r[1]), str(r[1]).rsplit("/", 1)[-1])
        for r in conn.execute("SELECT id, path FROM projects")
    }

    def mask(text: str, limit: int) -> str:
        text = _prefix(text, limit * 3)  # mask only what can be shown (profiling: 10x faster)
        cut = truncate(mask_projects(mask_exact(mask_names(text, names), bots), proj_terms), limit)
        return _HALF_TOKEN.sub("…", cut)  # never show half a name token

    projects = [
        dict(r)
        for r in conn.execute(
            "SELECT id, name, path, web_url, last_activity_at, window_mrs, window_notes, selected, skip_reason, focus_mrs "
            "FROM projects ORDER BY id"
        )
    ]
    with db.tx(conn):
        for p in projects:
            p["label"] = project_label_for(conn, p["id"])
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
    cls = {r["thread_id"]: r for r in conn.execute("SELECT * FROM classifications")}
    fails = {r["thread_id"]: r for r in conn.execute("SELECT * FROM classification_failures")}
    model = cfg.ollama_model
    digest = db.get_meta(conn, "ollama_digest")
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
        status = _status(r, cls.get(r["id"]), fails.get(r["id"]), model, digest)
        own = [
            b
            for (b,) in conn.execute(
                "SELECT body FROM notes WHERE discussion_id=? AND system=0 AND author_id=? AND id != ?",
                (r["id"], r["recipient_id"], r["first_note_id"]),
            )
        ]
        threads.append(
            {
                "id": r["id"],
                # REQ-UI-7: the recipient's own replies (words, thanks); None when none
                "rw": sum(reply_words(b) for b in own) if own else None,
                "rthx": any(is_thanks(b) for b in own),
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
                "sub": bool(r["substantive"]),
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
                "racts": [a["act"] for a in resp["acts"] if a.get("by") == "recipient"],
                "ev": r["evidence_level"],
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
                "label": label_for(conn, uid) if users[uid]["kind"] in ("human", "bot") else None,
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
        if t["sub"]:
            statuses[t["cls"]] = statuses.get(t["cls"], 0) + 1
    partial = _partial_reasons(conn, summary, statuses)
    gap_total = sum(summary["gaps"].values()) + summary["work"].get("mr", {}).get("skipped", 0)
    state = "partial" if partial else ("complete_with_gaps" if gap_total else "complete")
    provenance = [
        dict(r)
        for r in conn.execute(
            "SELECT model, model_digest, prompt_version, schema_version, COUNT(*) AS n "
            "FROM classifications WHERE status='ok' GROUP BY 1, 2, 3, 4 ORDER BY n DESC"
        )
    ]
    meta = {
        "tool_version": __version__,
        "generated_at": db.utcnow(),
        "snapshot_at": summary["snapshot_at"],
        "window_start": summary["window_start"],
        "evaluated_at": db.get_meta(conn, "evaluated_at"),
        "model": model,
        "model_digest": db.get_meta(conn, "ollama_digest"),
        "ollama_version": db.get_meta(conn, "ollama_version"),
        "stub": any(p["model"] == STUB_MODEL for p in provenance),
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
            "complete": state != "partial",
            "state": state,
            "partial_reasons": partial,
            "bounded_sample": db.get_meta(conn, "bounded_sample") == "1",
        },
        "provenance": provenance,
        "focus_user": _focus_user(conn),
    }
    return {
        "meta": meta,
        "projects": projects,
        "people": people,
        "mrs": mrs,
        "threads": threads,
        "findings": findings,
    }
