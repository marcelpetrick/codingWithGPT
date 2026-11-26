# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests: collector against the fake GitLab over HTTP (REQ-COL-*, REQ-DB-2)."""

import sqlite3

import pytest

from mrreview import collect, db, normalize
from mrreview.demo.fixture import REFERENCE_NOW
from mrreview.gitlab import GitLabClient, NotAccessible
from mrreview.http import HttpError, UrllibTransport

from .conftest import Env


def test_discover_selects_and_skips(gl: Env, conn: sqlite3.Connection) -> None:
    selected = collect.discover(gl.client, conn, gl.cfg, REFERENCE_NOW)
    assert set(selected) == {11, 12, 13, 14}
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM projects")}
    assert len(rows) == 6
    assert rows[15]["selected"] == 0
    assert rows[15]["skip_reason"].startswith("no MR activity since")
    assert rows[16]["skip_reason"].startswith("no MR activity")
    assert rows[11]["web_url"].endswith("firmware/display-controller")
    assert rows[11]["path"] == "firmware/display-controller"


def test_discover_bounded_sample(gl: Env, conn: sqlite3.Connection) -> None:
    selected = collect.discover(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1)
    assert len(selected) == 1
    reasons = [r[0] for r in conn.execute("SELECT skip_reason FROM projects WHERE selected=0")]
    assert "outside the bounded sample" in reasons


def test_collect_full_history(gl: Env, conn: sqlite3.Connection) -> None:
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    expected = sum(len(gl.fixture.mrs[p]) for p in (11, 12, 13, 14))
    assert stats.mrs_collected == expected
    assert conn.execute("SELECT COUNT(*) FROM merge_requests").fetchone()[0] == expected
    n_notes = sum(
        len(d["notes"]) for k, ds in gl.fixture.discussions.items() if k[0] != 15 for d in ds
    )
    assert conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == n_notes
    assert conn.execute("SELECT COUNT(*) FROM mr_versions").fetchone()[0] > expected
    assert conn.execute("SELECT COUNT(*) FROM version_diffs").fetchone()[0] > 0
    assert conn.execute("SELECT COUNT(*) FROM mr_commits").fetchone()[0] > 0
    states = {r[0] for r in conn.execute("SELECT DISTINCT state FROM merge_requests")}
    assert {"merged", "opened"} <= states
    assert db.get_meta(conn, "snapshot_at") == REFERENCE_NOW.isoformat()
    assert set(gl.fake.methods) == {"GET"}


def test_rerun_no_duplicates_and_no_refetch(gl: Env, conn: sqlite3.Connection) -> None:
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    before = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("notes", "approvals", "mr_versions", "users", "merge_requests")
    }
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    assert stats.mrs_collected == 0
    after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in before}
    assert before == after


def test_changed_mr_is_refetched(gl: Env, conn: sqlite3.Connection) -> None:
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    mr = gl.fixture.mrs[11][0]
    mr["updated_at"] = "2026-11-20T11:00:00Z"
    mr["user_notes_count"] = int(mr["user_notes_count"]) + 1
    assert db.get_work(conn, "mr", f"11:{mr['iid']}").status == "done"  # type: ignore[union-attr]
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    assert stats.mrs_collected == 1


def test_resume_after_interruption(gl: Env, conn: sqlite3.Connection) -> None:
    with pytest.raises(KeyboardInterrupt):
        collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, stop_after=10)
    assert db.work_summary(conn)["mr"]["done"] == 10
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    total = sum(len(gl.fixture.mrs[p]) for p in (11, 12, 13, 14))
    assert stats.mrs_collected == total - 10
    assert db.work_summary(conn)["mr"] == {"done": total}


def test_retry_on_rate_limit_and_server_error(gl: Env, conn: sqlite3.Connection) -> None:
    gl.fake.faults = {r"/discussions$": [429, 502], r"/approvals$": [503]}
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1, max_mrs=3)
    assert stats.mrs_collected == 3
    assert stats.mrs_failed == 0


def test_persistent_failure_is_recorded_then_retried(gl: Env, conn: sqlite3.Connection) -> None:
    gl.fake.faults = {r"/merge_requests/\d+/commits$": [500] * 4}
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1, max_mrs=2)
    assert stats.mrs_failed == 1
    failed = conn.execute("SELECT * FROM work WHERE status='failed'").fetchall()
    assert len(failed) == 1
    assert "HTTP 500" in failed[0]["last_error"]
    assert "tok-123" not in failed[0]["last_error"]
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1, max_mrs=2)
    assert stats.mrs_collected == 1


def test_gaps_recorded(gl: Env, conn: sqlite3.Connection) -> None:
    key = next(iter(gl.fixture.approvals))
    del gl.fixture.approvals[key]
    del gl.fixture.commits[key]
    vid = gl.fixture.versions[key][0]["id"]
    del gl.fixture.version_detail[(*key, vid)]
    other = list(gl.fixture.versions)[1]
    del gl.fixture.versions[other]
    big = list(gl.fixture.version_detail)[5]
    gl.fixture.version_detail[big]["diffs"][0]["too_large"] = True
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    kinds = {r[0] for r in conn.execute("SELECT kind FROM gaps")}
    assert {
        "approvals_unavailable",
        "commits_unavailable",
        "version_diff_unavailable",
        "versions_unavailable",
        "diff_too_large",
    } <= kinds
    assert (
        conn.execute("SELECT COUNT(*) FROM mr_versions WHERE diffs_complete=0").fetchone()[0] >= 2
    )


def test_inaccessible_mr_and_project(gl: Env, conn: sqlite3.Connection) -> None:
    key = next(iter(gl.fixture.discussions))
    del gl.fixture.discussions[key]
    gl.fixture.projects.append(
        {
            "id": 77,
            "name": "secret",
            "path_with_namespace": "x/secret",
            "web_url": "http://x",
            "last_activity_at": None,
            "archived": False,
        }
    )
    stats = collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    assert stats.mrs_skipped == 1
    reason = conn.execute("SELECT skip_reason FROM projects WHERE id=77").fetchone()[0]
    assert reason == "merge requests not accessible"
    assert (
        conn.execute("SELECT COUNT(*) FROM gaps WHERE kind='mr_not_accessible'").fetchone()[0] == 1
    )


def test_unreachable_server_stops_the_job(conn: sqlite3.Connection) -> None:
    from mrreview.config import Config

    client = GitLabClient(
        "http://127.0.0.1:9",
        "t",
        UrllibTransport(),
        max_retries=1,
        backoff_base=0,
        sleep=lambda _s: None,
    )
    with pytest.raises(collect.StopRun, match="unreachable"):
        collect.run_collect(client, conn, Config(), REFERENCE_NOW)
    assert conn.execute("SELECT COUNT(*) FROM merge_requests").fetchone()[0] == 0


def test_wrong_token_is_a_final_error(gl: Env) -> None:
    client = GitLabClient(gl.url, "wrong", UrllibTransport(), max_retries=0)
    with pytest.raises(HttpError, match="401"):
        list(client.projects(membership=True, archived=True))
    client_ok = GitLabClient(gl.url, "tok-123", UrllibTransport())
    with pytest.raises(NotAccessible):
        client_ok.get_json("/nope")
    assert repr(client_ok) == f"GitLabClient('{gl.url}/api/v4')"


def test_client_is_read_only(gl: Env) -> None:
    public = [m for m in dir(GitLabClient) if not m.startswith("_")]
    assert set(public) <= {
        "get_json",
        "paginate",
        "projects",
        "merge_requests",
        "discussions",
        "approvals",
        "versions",
        "version",
        "commits",
        "requests",
    }
    status, _, _ = gl.fake.handle("POST", "/api/v4/projects", {"private-token": "tok-123"})
    assert status == 405


def test_token_never_logged(gl: Env, conn: sqlite3.Connection) -> None:
    messages: list[str] = []
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, messages.append, max_projects=1)
    assert messages
    assert all("tok-123" not in m for m in messages)
    dump = "\n".join(conn.iterdump())
    assert "tok-123" not in dump


def test_threads_from_collected_data(gl: Env, conn: sqlite3.Connection) -> None:
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW)
    counts = normalize.build_threads(conn)
    truth = gl.fixture.truth
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM threads")}
    for did, row in rows.items():
        key = truth.get(did)
        if key == "lgtm":
            assert row["reason"] == "routine_only"
        elif key == "bot":
            assert row["reason"] == "bot_initiated"
        elif key == "author_self_note":
            assert row["reason"] == "author_self_note"
        elif key in ("unanswered", "silent_fix", "injection"):
            assert row["reason"] == "substantive"
            assert row["has_reply"] == 0
    assert counts["substantive"] > 200
    assert not any(r["id"].startswith("sys") for r in rows.values())
    again = normalize.build_threads(conn)
    assert again == counts
