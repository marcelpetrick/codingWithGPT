# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Project discovery and merge request collection (REQ-COL-1 to REQ-COL-6).

Every MR is written in one transaction, so an interruption loses at most the MR in flight.
A rerun skips MRs whose updated_at and note count did not change.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from mrreview import db
from mrreview.config import Config
from mrreview.gitlab import GitLabClient, JSONDict, NotAccessible
from mrreview.http import HttpError, TransportError
from mrreview.identity import user_kind

MAX_ATTEMPTS = 5
Progress = Callable[[str], None]


class StopRun(RuntimeError):
    """A server is unreachable. The job stops; nothing is booked as a result."""


@dataclass(frozen=True)
class CollectStats:
    projects_selected: int
    mrs_listed: int
    mrs_collected: int
    mrs_failed: int
    mrs_skipped: int


def _ts(value: Any) -> str | None:
    if not value:
        return None
    return (
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        .astimezone(UTC)
        .isoformat(timespec="seconds")
    )


def window_start(now: datetime, months: int) -> datetime:
    """The start of the rolling activity window (30.44 days per month)."""
    return now - timedelta(days=round(30.44 * months))


def upsert_user(conn: sqlite3.Connection, user: JSONDict | None) -> int | None:
    if not user or "id" not in user:
        return None
    conn.execute(
        """INSERT INTO users(id, username, name, kind, web_url) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET username=excluded.username, name=excluded.name,
        kind=excluded.kind, web_url=excluded.web_url""",
        (
            user["id"],
            user.get("username", ""),
            user.get("name", ""),
            user_kind(user),
            user.get("web_url"),
        ),
    )
    return int(user["id"])


def discover(
    client: GitLabClient,
    conn: sqlite3.Connection,
    cfg: Config,
    now: datetime,
    progress: Progress = lambda _m: None,
    max_projects: int | None = None,
) -> list[int]:
    """List all visible projects, measure window activity, select the active ones.

    Returns the selected project IDs, the most active first.
    """
    start = window_start(now, cfg.window_months).isoformat(timespec="seconds")
    found = list(
        client.projects(membership=cfg.discover_membership_only, archived=cfg.include_archived)
    )
    progress(f"discover: {len(found)} projects visible")
    ranked: list[tuple[int, int, int]] = []
    for p in found:
        pid = int(p["id"])
        try:
            mrs = list(client.merge_requests(pid, updated_after=start))
            n_mrs = len(mrs)
            n_notes = sum(int(m.get("user_notes_count") or 0) for m in mrs)
            skip = None if n_mrs >= cfg.min_window_mrs else f"no MR activity since {start[:10]}"
        except NotAccessible:
            n_mrs, n_notes, skip = 0, 0, "merge requests not accessible"
        with db.tx(conn):
            conn.execute(
                """INSERT INTO projects(id, name, path, web_url, last_activity_at, archived,
                window_mrs, window_notes, selected, skip_reason, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, path=excluded.path,
                web_url=excluded.web_url, last_activity_at=excluded.last_activity_at,
                archived=excluded.archived, window_mrs=excluded.window_mrs,
                window_notes=excluded.window_notes, skip_reason=excluded.skip_reason,
                discovered_at=excluded.discovered_at""",
                (
                    pid,
                    p.get("name_with_namespace") or p.get("name", ""),
                    p.get("path_with_namespace", ""),
                    p.get("web_url", ""),
                    _ts(p.get("last_activity_at")),
                    int(bool(p.get("archived"))),
                    n_mrs,
                    n_notes,
                    skip,
                    db.utcnow(),
                ),
            )
        if skip is None:
            ranked.append((n_notes, n_mrs, pid))
    ranked.sort(reverse=True)
    selected = [pid for _, _, pid in ranked]
    limited = selected[:max_projects] if max_projects is not None else selected
    with db.tx(conn):
        conn.execute("UPDATE projects SET selected = 0")
        for pid in selected:
            if pid in limited:
                conn.execute("UPDATE projects SET selected = 1 WHERE id = ?", (pid,))
            else:
                conn.execute(
                    "UPDATE projects SET skip_reason = 'outside the bounded sample' WHERE id = ?",
                    (pid,),
                )
        db.set_meta(conn, "window_start", start)
        db.set_work(conn, "discover", "all", "done")
    progress(f"discover: {len(limited)} selected, {len(found) - len(limited)} skipped")
    return limited


def _mr_hash(mr: JSONDict) -> str:
    raw = f"{mr.get('updated_at')}|{mr.get('user_notes_count')}|{mr.get('state')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def list_project_mrs(
    client: GitLabClient, conn: sqlite3.Connection, pid: int, max_mrs: int | None = None
) -> int:
    """Store MR metadata (full history) and queue MRs that are new or changed."""
    count = 0
    mrs = list(client.merge_requests(pid))
    if max_mrs is not None:
        mrs = sorted(mrs, key=lambda m: str(m.get("updated_at")), reverse=True)[:max_mrs]
    for mr in mrs:
        key = f"{pid}:{mr['iid']}"
        h = _mr_hash(mr)
        with db.tx(conn):
            author = upsert_user(conn, mr.get("author"))
            conn.execute(
                """INSERT INTO merge_requests(project_id, iid, id, title, state, author_id, created_at,
                updated_at, merged_at, closed_at, web_url, user_notes_count, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, iid) DO UPDATE SET title=excluded.title, state=excluded.state,
                author_id=excluded.author_id, updated_at=excluded.updated_at,
                merged_at=excluded.merged_at, closed_at=excluded.closed_at,
                web_url=excluded.web_url, user_notes_count=excluded.user_notes_count,
                fetched_at=excluded.fetched_at""",
                (
                    pid,
                    mr["iid"],
                    mr["id"],
                    mr.get("title", ""),
                    mr.get("state", ""),
                    author,
                    _ts(mr.get("created_at")),
                    _ts(mr.get("updated_at")),
                    _ts(mr.get("merged_at")),
                    _ts(mr.get("closed_at")),
                    mr.get("web_url", ""),
                    mr.get("user_notes_count"),
                    db.utcnow(),
                ),
            )
            w = db.get_work(conn, "mr", key)
            if w is None:
                db.set_work(conn, "mr", key, "pending", input_hash=h)
            elif w.input_hash != h:
                db.set_work(
                    conn, "mr", key, "stale" if w.status == "done" else "pending", input_hash=h
                )
        count += 1
    return count


def _position(note: JSONDict) -> tuple[Any, ...]:
    pos = note.get("position") or {}
    return (
        pos.get("new_path"),
        pos.get("old_path"),
        pos.get("new_line"),
        pos.get("old_line"),
        pos.get("head_sha"),
    )


def collect_mr(
    client: GitLabClient, conn: sqlite3.Connection, cfg: Config, pid: int, iid: int
) -> None:
    """Fetch discussions, approvals, versions with diffs and commits; write them in one transaction."""
    ref = f"{pid}:{iid}"
    gaps: list[tuple[str, str]] = []
    discussions = list(client.discussions(pid, iid))
    try:
        approvals = client.approvals(pid, iid)
    except NotAccessible:
        approvals, gaps = {}, [*gaps, ("approvals_unavailable", "")]
    versions: list[tuple[JSONDict, JSONDict | None]] = []
    try:
        for v in client.versions(pid, iid):
            try:
                versions.append((v, client.version(pid, iid, int(v["id"]))))
            except NotAccessible:
                versions.append((v, None))
                gaps.append(("version_diff_unavailable", str(v["id"])))
    except NotAccessible:
        gaps.append(("versions_unavailable", ""))
    try:
        commits = list(client.commits(pid, iid))
    except NotAccessible:
        commits = []
        gaps.append(("commits_unavailable", ""))
    with db.tx(conn):
        for table in (
            "notes",
            "discussions",
            "approvals",
            "mr_versions",
            "version_diffs",
            "mr_commits",
        ):
            col = "mr_iid"
            conn.execute(f"DELETE FROM {table} WHERE project_id=? AND {col}=?", (pid, iid))
        conn.execute("DELETE FROM gaps WHERE scope='mr' AND ref=?", (ref,))
        for d in discussions:
            conn.execute(
                "INSERT OR REPLACE INTO discussions(id, project_id, mr_iid, individual_note) VALUES (?, ?, ?, ?)",
                (d["id"], pid, iid, int(bool(d.get("individual_note")))),
            )
            for n in d.get("notes", []):
                author = upsert_user(conn, n.get("author"))
                resolver = upsert_user(conn, n.get("resolved_by"))
                conn.execute(
                    """INSERT OR REPLACE INTO notes(id, discussion_id, project_id, mr_iid, author_id, body,
                    created_at, updated_at, system, type, resolvable, resolved, resolved_by_id,
                    resolved_at, new_path, old_path, new_line, old_line, head_sha)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        n["id"],
                        d["id"],
                        pid,
                        iid,
                        author,
                        n.get("body") or "",
                        _ts(n.get("created_at")),
                        _ts(n.get("updated_at")),
                        int(bool(n.get("system"))),
                        n.get("type"),
                        int(bool(n.get("resolvable"))),
                        int(bool(n.get("resolved"))),
                        resolver,
                        _ts(n.get("resolved_at")),
                        *_position(n),
                    ),
                )
        for a in approvals.get("approved_by") or []:
            uid = upsert_user(conn, a.get("user"))
            if uid is not None:
                conn.execute("INSERT OR IGNORE INTO approvals VALUES (?, ?, ?)", (pid, iid, uid))
        for meta, detail in versions:
            complete = detail is not None
            for diff in (detail or {}).get("diffs") or []:
                text = diff.get("diff") or ""
                if (
                    diff.get("too_large")
                    or diff.get("collapsed")
                    or len(text.encode()) > cfg.max_diff_bytes
                ):
                    complete = False
                    gaps.append(("diff_too_large", f"{meta['id']}:{diff.get('new_path')}"))
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO version_diffs VALUES (?, ?, ?, ?, ?, ?)",
                    (pid, iid, meta["id"], diff.get("new_path") or "", diff.get("old_path"), text),
                )
            conn.execute(
                "INSERT OR REPLACE INTO mr_versions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    pid,
                    iid,
                    meta["id"],
                    meta.get("head_commit_sha"),
                    meta.get("base_commit_sha"),
                    _ts(meta.get("created_at")),
                    int(complete),
                ),
            )
        for c in commits:
            conn.execute(
                "INSERT OR REPLACE INTO mr_commits VALUES (?, ?, ?, ?, ?, ?)",
                (pid, iid, c["id"], c.get("author_name"), _ts(c.get("created_at")), c.get("title")),
            )
        for gap_kind, gap_detail in gaps:
            db.record_gap(conn, "mr", ref, gap_kind, gap_detail)
        db.set_work(conn, "mr", ref, "done")


def pending_mrs(conn: sqlite3.Connection) -> list[tuple[int, int]]:
    rows = conn.execute(
        """SELECT w.key FROM work w JOIN projects p ON p.id = CAST(substr(w.key, 1, instr(w.key, ':') - 1) AS INTEGER)
        WHERE w.kind='mr' AND p.selected=1 AND (w.status IN ('pending', 'stale')
        OR (w.status='failed' AND w.attempts < ?)) ORDER BY w.key""",
        (MAX_ATTEMPTS,),
    ).fetchall()
    return [(int(k.split(":")[0]), int(k.split(":")[1])) for (k,) in rows]


def run_collect(
    client: GitLabClient,
    conn: sqlite3.Connection,
    cfg: Config,
    now: datetime,
    progress: Progress = lambda _m: None,
    *,
    max_projects: int | None = None,
    max_mrs: int | None = None,
    stop_after: int | None = None,
) -> CollectStats:
    """Discover, list and collect. stop_after simulates an interruption (tests)."""
    try:
        selected = discover(client, conn, cfg, now, progress, max_projects)
        listed = 0
        for pid in selected:
            listed += list_project_mrs(client, conn, pid, max_mrs)
        todo = pending_mrs(conn)
        progress(f"collect: {len(todo)} MRs to fetch")
        done = failed = skipped = 0
        for n, (pid, iid) in enumerate(todo, 1):
            if stop_after is not None and n > stop_after:
                raise KeyboardInterrupt
            try:
                collect_mr(client, conn, cfg, pid, iid)
                done += 1
            except NotAccessible as exc:
                with db.tx(conn):
                    db.record_gap(conn, "mr", f"{pid}:{iid}", "mr_not_accessible", str(exc)[:200])
                    db.set_work(conn, "mr", f"{pid}:{iid}", "skipped", error=str(exc)[:200])
                skipped += 1
            except HttpError as exc:
                with db.tx(conn):
                    db.set_work(conn, "mr", f"{pid}:{iid}", "failed", error=str(exc)[:300])
                failed += 1
            if n % 25 == 0:
                progress(f"collect: {n}/{len(todo)}")
    except TransportError as exc:
        raise StopRun(f"GitLab unreachable, collection stopped: {exc}") from None
    with db.tx(conn):
        db.set_meta(conn, "snapshot_at", now.astimezone(UTC).isoformat(timespec="seconds"))
        db.set_meta(conn, "gitlab_requests", str(client.requests))
    progress(f"collect: {done} fetched, {failed} failed, {skipped} not accessible")
    return CollectStats(len(selected), listed, done, failed, skipped)


def collect_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Counts for the coverage section of the report."""

    def q(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0])

    return {
        "projects_visible": q("SELECT COUNT(*) FROM projects"),
        "projects_selected": q("SELECT COUNT(*) FROM projects WHERE selected=1"),
        "mrs": q("SELECT COUNT(*) FROM merge_requests"),
        "notes": q("SELECT COUNT(*) FROM notes"),
        "gaps": dict(conn.execute("SELECT kind, COUNT(*) FROM gaps GROUP BY kind").fetchall()),
        "work": db.work_summary(conn),
        "snapshot_at": db.get_meta(conn, "snapshot_at"),
        "window_start": db.get_meta(conn, "window_start"),
    }
