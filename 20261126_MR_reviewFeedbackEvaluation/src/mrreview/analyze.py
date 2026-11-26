# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Semantic analysis of substantive threads with the local LLM (REQ-LLM-1 to REQ-LLM-3).

A classification is reused while the thread input hash, the prompt version, the schema version
and the model stay the same. Only changed or failed threads are sent again.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any

from mrreview import db, llm
from mrreview.collect import StopRun
from mrreview.config import Config
from mrreview.diffs import new_side_lines, window
from mrreview.http import HttpError, TransportError
from mrreview.identity import mask_names
from mrreview.textutil import truncate

MAX_ATTEMPTS = 3
MAX_CONSECUTIVE_TRANSPORT_ERRORS = 3
Progress = Callable[[str], None]


@dataclass(frozen=True)
class AnalyzeStats:
    todo: int
    ok: int
    invalid: int
    failed: int
    reused: int


def _role_map(
    conn: sqlite3.Connection, thread: sqlite3.Row, author_ids: list[int | None]
) -> dict[int | None, str]:
    mr_author = conn.execute(
        "SELECT author_id FROM merge_requests WHERE project_id=? AND iid=?",
        (thread["project_id"], thread["mr_iid"]),
    ).fetchone()[0]
    kinds = {r[0]: r[1] for r in conn.execute("SELECT id, kind FROM users")}
    roles: dict[int | None, str] = {mr_author: "mr_author"}
    if thread["giver_id"] != mr_author:
        roles[thread["giver_id"]] = "reviewer"
    n = 0
    for uid in author_ids:
        if uid in roles:
            continue
        if kinds.get(uid) == "bot":
            roles[uid] = "bot"
        else:
            n += 1
            roles[uid] = f"participant_{n}"
    return roles


def thread_context(
    conn: sqlite3.Connection, thread: sqlite3.Row, cfg: Config
) -> tuple[dict[str, Any], set[int]]:
    """The minimum context for one thread, with names replaced by role labels."""
    notes = conn.execute(
        "SELECT id, author_id, body, created_at FROM notes WHERE discussion_id=? AND system=0 "
        "ORDER BY created_at, id LIMIT ?",
        (thread["id"], cfg.max_thread_notes),
    ).fetchall()
    roles = _role_map(conn, thread, [n["author_id"] for n in notes])
    users = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT id, username, name FROM users")}

    def clean(text: str, limit: int) -> str:
        masked = mask_names(text, users)
        for uid in users:
            masked = masked.replace(f"⟦u:{uid}⟧", "@" + roles.get(uid, "someone"))
        return truncate(masked, limit)

    title = conn.execute(
        "SELECT title FROM merge_requests WHERE project_id=? AND iid=?",
        (thread["project_id"], thread["mr_iid"]),
    ).fetchone()[0]
    payload: dict[str, Any] = {"merge_request_title": clean(title, 200)}
    if thread["new_path"]:
        payload["file"] = thread["new_path"]
        payload["line"] = thread["new_line"]
        row = conn.execute(
            """SELECT d.diff FROM version_diffs d JOIN mr_versions v ON v.project_id=d.project_id
            AND v.mr_iid=d.mr_iid AND v.version_id=d.version_id
            WHERE d.project_id=? AND d.mr_iid=? AND d.new_path=? AND v.created_at <= ?
            ORDER BY v.created_at DESC LIMIT 1""",
            (thread["project_id"], thread["mr_iid"], thread["new_path"], thread["created_at"]),
        ).fetchone()
        if row and thread["new_line"]:
            ctx = window(new_side_lines(row[0]), int(thread["new_line"]), 6)
            payload["code_context"] = "\n".join(f"{k}: {truncate(v, 160)}" for k, v in ctx.items())
    payload["notes"] = [
        {
            "id": n["id"],
            "author_role": roles.get(n["author_id"], "someone"),
            "time": n["created_at"],
            "text": clean(n["body"], cfg.max_note_graphemes),
        }
        for n in notes
    ]
    return payload, {int(n["id"]) for n in notes}


def cache_key(llm_hash: str, model: str) -> str:
    """A classification is valid for one thread text, prompt, schema and model."""
    return f"{llm_hash}|{llm.PROMPT_VERSION}|{llm.SCHEMA_VERSION}|{model}"


def _focus_id(conn: sqlite3.Connection) -> int:
    """User id of the focus user, or -1. Threads that involve the focus user are classified first."""
    name = db.get_meta(conn, "focus_username") or ""
    row = conn.execute("SELECT id FROM users WHERE lower(username)=lower(?)", (name,)).fetchone()
    return int(row[0]) if row else -1


def _todo(conn: sqlite3.Connection, model: str, limit: int | None) -> tuple[list[sqlite3.Row], int]:
    rows = conn.execute(
        """SELECT t.*, c.input_hash AS c_hash, c.prompt_version AS c_pv, c.schema_version AS c_sv,
        c.model AS c_model, c.status AS c_status, f.cache_key AS f_key, f.attempts AS f_attempts
        FROM threads t LEFT JOIN classifications c ON c.thread_id = t.id
        LEFT JOIN classification_failures f ON f.thread_id = t.id
        WHERE t.substantive = 1
        ORDER BY (t.giver_id = :focus OR t.recipient_id = :focus) DESC, t.created_at DESC, t.id""",
        {"focus": _focus_id(conn)},
    ).fetchall()
    todo: list[sqlite3.Row] = []
    reused = 0
    for r in rows:
        key = cache_key(r["llm_hash"], model)
        current = (
            r["c_status"] == "ok"
            and r["c_hash"] == r["llm_hash"]
            and (r["c_pv"], r["c_sv"], r["c_model"])
            == (llm.PROMPT_VERSION, llm.SCHEMA_VERSION, model)
        )
        if current:
            reused += 1
        elif not (r["f_key"] == key and r["f_attempts"] >= MAX_ATTEMPTS):
            todo.append(r)
    return (todo[:limit] if limit is not None else todo), reused


def _store_ok(
    conn: sqlite3.Connection,
    thread: sqlite3.Row,
    model: llm.ModelInfo,
    result: list[dict[str, Any]],
    duration: float,
) -> None:
    with db.tx(conn):
        conn.execute(
            """INSERT OR REPLACE INTO classifications(thread_id, input_hash, prompt_version,
            schema_version, model, model_digest, status, result_json, error, raw_excerpt, attempts,
            duration_s, created_at) VALUES (?, ?, ?, ?, ?, ?, 'ok', ?, NULL, NULL, 1, ?, ?)""",
            (
                thread["id"],
                thread["llm_hash"],
                llm.PROMPT_VERSION,
                llm.SCHEMA_VERSION,
                model.name,
                model.digest,
                json.dumps(result, ensure_ascii=False),
                duration,
                db.utcnow(),
            ),
        )
        conn.execute("DELETE FROM classification_failures WHERE thread_id=?", (thread["id"],))
        db.set_work(conn, "classify", thread["id"], "done", input_hash=thread["llm_hash"])


def _store_failure(
    conn: sqlite3.Connection,
    thread: sqlite3.Row,
    model: llm.ModelInfo,
    status: str,
    error: str,
    raw: str | None,
) -> None:
    """Record a failed attempt. An earlier valid classification stays untouched."""
    key = cache_key(thread["llm_hash"], model.name)
    attempts = (int(thread["f_attempts"] or 0) if thread["f_key"] == key else 0) + 1
    with db.tx(conn):
        conn.execute(
            "INSERT OR REPLACE INTO classification_failures VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                thread["id"],
                key,
                status,
                attempts,
                error[:300],
                truncate(raw, 500) if raw else None,
                db.utcnow(),
            ),
        )
        db.set_work(
            conn,
            "classify",
            thread["id"],
            "failed",
            input_hash=thread["llm_hash"],
            error=error[:300],
        )


def run_analyze(
    conn: sqlite3.Connection,
    cfg: Config,
    client: llm.OllamaClient,
    progress: Progress = lambda _m: None,
    *,
    limit: int | None = None,
) -> AnalyzeStats:
    """Classify every substantive thread that has no valid, current classification."""
    try:
        model = client.model_info(cfg.ollama_model)
    except (TransportError, HttpError) as exc:
        raise StopRun(f"Ollama unreachable, analysis stopped: {exc}") from None
    with db.tx(conn):
        db.set_meta(conn, "ollama_model", model.name)
        db.set_meta(conn, "ollama_digest", model.digest or "")
        db.set_meta(conn, "ollama_version", model.server_version or "")
    todo, reused = _todo(conn, model.name, limit)
    progress(f"analyze: {len(todo)} threads to classify, {reused} reused")
    counts = {"ok": 0, "invalid": 0, "failed": 0}
    streak = 0

    def job(
        payload: dict[str, Any], ids: set[int]
    ) -> tuple[list[dict[str, Any]] | None, str | None, str | None, float]:
        start = time.monotonic()
        try:
            comp = client.chat(
                model.name,
                llm.build_messages(payload),
                schema=llm.OUTPUT_SCHEMA,
                options=cfg.ollama_options,
                keep_alive=cfg.ollama_keep_alive,
            )
        except llm.InvalidOutput as exc:
            return None, str(exc), None, time.monotonic() - start
        try:
            return llm.validate(comp.content, ids), None, comp.content, time.monotonic() - start
        except llm.InvalidOutput as exc:
            return None, str(exc), comp.content, time.monotonic() - start

    pending = list(todo)
    with ThreadPoolExecutor(max_workers=cfg.ollama_concurrency) as pool:
        running: dict[Future[Any], sqlite3.Row] = {}
        while pending or running:
            while pending and len(running) < cfg.ollama_concurrency:
                t = pending.pop(0)
                payload, ids = thread_context(conn, t, cfg)
                running[pool.submit(job, payload, ids)] = t
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for fut in done:
                thread = running.pop(fut)
                try:
                    result, error, raw, dur = fut.result()
                except TransportError as exc:
                    streak += 1
                    _store_failure(conn, thread, model, "failed", f"transport: {exc}", None)
                    counts["failed"] += 1
                    if streak >= MAX_CONSECUTIVE_TRANSPORT_ERRORS:
                        pending.clear()
                        for f in running:
                            f.cancel()
                        raise StopRun(f"Ollama unreachable, analysis stopped: {exc}") from None
                    continue
                except (HttpError, ValueError, KeyError, TypeError, AttributeError) as exc:
                    streak = 0
                    _store_failure(
                        conn, thread, model, "failed", f"{type(exc).__name__}: {exc}", None
                    )
                    counts["failed"] += 1
                    continue
                streak = 0
                if result is not None:
                    _store_ok(conn, thread, model, result, dur)
                    counts["ok"] += 1
                else:
                    _store_failure(conn, thread, model, "invalid", error or "invalid", raw)
                    counts["invalid"] += 1
            n = sum(counts.values())
            if n and n % 10 == 0:
                progress(f"analyze: {n}/{len(todo)}")
    progress(f"analyze: {counts['ok']} ok, {counts['invalid']} invalid, {counts['failed']} failed")
    return AnalyzeStats(len(todo), counts["ok"], counts["invalid"], counts["failed"], reused)
