# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests: analysis against the fake Ollama over HTTP (REQ-LLM-*, REQ-DB-2, REQ-OUT-*)."""

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import replace

import pytest

from mrreview import analyze, collect, db, evaluate, llm, normalize
from mrreview.config import Config
from mrreview.demo.fake_ollama import STUB_MODEL, FakeOllama, serve
from mrreview.demo.fixture import REFERENCE_NOW
from mrreview.http import UrllibTransport

from .conftest import Env


@pytest.fixture
def ollama() -> Iterator[tuple[FakeOllama, llm.OllamaClient]]:
    fake = FakeOllama()
    with serve(fake) as url:
        yield fake, llm.OllamaClient(url, UrllibTransport(), max_retries=1, backoff_base=0, sleep=lambda _s: None)


@pytest.fixture
def collected(gl: Env, conn: sqlite3.Connection) -> Config:
    collect.run_collect(gl.client, conn, gl.cfg, REFERENCE_NOW, max_projects=1)
    normalize.build_threads(conn)
    return replace(gl.cfg, ollama_model=STUB_MODEL)


def test_analyze_and_reuse(conn: sqlite3.Connection, collected: Config,
                           ollama: tuple[FakeOllama, llm.OllamaClient]) -> None:
    fake, client = ollama
    n_sub = conn.execute("SELECT COUNT(*) FROM threads WHERE substantive=1").fetchone()[0]
    stats = analyze.run_analyze(conn, collected, client)
    assert stats.ok == n_sub
    assert fake.calls == n_sub
    row = conn.execute("SELECT * FROM classifications LIMIT 1").fetchone()
    assert row["model"] == STUB_MODEL
    assert row["model_digest"] == "f" * 64
    assert row["prompt_version"] == llm.PROMPT_VERSION
    assert db.get_meta(conn, "ollama_version") == "0.0.0-fake"
    again = analyze.run_analyze(conn, collected, client)
    assert again.todo == 0
    assert again.reused == n_sub
    assert fake.calls == n_sub


def test_request_shape_and_minimised_names(conn: sqlite3.Connection, collected: Config,
                                           ollama: tuple[FakeOllama, llm.OllamaClient]) -> None:
    fake, client = ollama
    analyze.run_analyze(conn, collected, client, limit=5)
    body = fake.bodies[0]
    assert body["format"] == llm.OUTPUT_SCHEMA
    assert body["stream"] is False
    assert body["think"] is False
    names = [r[0] for r in conn.execute("SELECT name FROM users WHERE kind='human'")]
    usernames = [r[0] for r in conn.execute("SELECT username FROM users WHERE kind='human'")]
    for b in fake.bodies:
        text = b["messages"][1]["content"]
        assert not any(n in text for n in names)
        assert not any("@" + u in text for u in usernames)
        assert "author_role" in text


def test_changed_thread_is_reclassified_only(conn: sqlite3.Connection, collected: Config,
                                             ollama: tuple[FakeOllama, llm.OllamaClient]) -> None:
    fake, client = ollama
    analyze.run_analyze(conn, collected, client)
    calls = fake.calls
    tid = conn.execute("SELECT id FROM threads WHERE substantive=1 LIMIT 1").fetchone()[0]
    with db.tx(conn):
        conn.execute("UPDATE notes SET body = body || ' (edited)' WHERE discussion_id=?", (tid,))
    normalize.build_threads(conn)
    stats = analyze.run_analyze(conn, collected, client)
    assert stats.todo == 1
    assert fake.calls == calls + 1


def test_malformed_output_is_kept_and_retried(conn: sqlite3.Connection, collected: Config,
                                              ollama: tuple[FakeOllama, llm.OllamaClient]) -> None:
    fake, client = ollama
    fake.faults = ["malformed", "bad_enum", "500", "500", "nomessage", "length"]
    stats = analyze.run_analyze(conn, collected, client, limit=6)
    # One request takes both 500s (max_retries=1), so six faults hit five threads.
    assert stats.ok == 1
    assert stats.invalid == 3
    assert stats.failed == 2
    bad = conn.execute("SELECT * FROM classifications WHERE status='invalid'").fetchall()
    assert all(b["error"] for b in bad)
    assert sum(1 for b in bad if b["raw_excerpt"]) == 2
    stats2 = analyze.run_analyze(conn, collected, client)
    assert stats2.todo >= 6
    assert conn.execute("SELECT COUNT(*) FROM classifications WHERE status!='ok'").fetchone()[0] == 0


def test_concurrency(conn: sqlite3.Connection, collected: Config,
                     ollama: tuple[FakeOllama, llm.OllamaClient]) -> None:
    _, client = ollama
    stats = analyze.run_analyze(conn, replace(collected, ollama_concurrency=4), client)
    assert stats.ok == stats.todo


def test_missing_model_and_unreachable(conn: sqlite3.Connection, collected: Config,
                                       ollama: tuple[FakeOllama, llm.OllamaClient]) -> None:
    _, client = ollama
    with pytest.raises(LookupError, match="not on the Ollama server"):
        analyze.run_analyze(conn, replace(collected, ollama_model="nope"), client)
    dead = llm.OllamaClient("http://127.0.0.1:9", UrllibTransport(), max_retries=0)
    with pytest.raises(collect.StopRun, match="unreachable"):
        analyze.run_analyze(conn, collected, dead)
    assert conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0] == 0


def test_server_dies_mid_run_stops_job(conn: sqlite3.Connection, collected: Config) -> None:
    fake = FakeOllama()
    with serve(fake) as url:
        client = llm.OllamaClient(url, UrllibTransport(), max_retries=0)
        info = client.model_info(STUB_MODEL)
    assert info.digest == "f" * 64
    dead_chat = llm.OllamaClient(url, UrllibTransport(), max_retries=0)
    dead_chat.model_info = lambda _m: info  # type: ignore[method-assign]
    with pytest.raises(collect.StopRun):
        analyze.run_analyze(conn, collected, dead_chat)
    assert conn.execute("SELECT COUNT(*) FROM classifications WHERE status='ok'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0] == 3


def test_evaluate_on_fixture_truth(gl: Env, conn: sqlite3.Connection, collected: Config,
                                   ollama: tuple[FakeOllama, llm.OllamaClient]) -> None:
    _, client = ollama
    analyze.run_analyze(conn, collected, client)
    counts = evaluate.run_evaluate(conn, collected)
    assert sum(counts.values()) == conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
    rows = conn.execute("SELECT f.*, t.id AS tid FROM findings f JOIN threads t ON t.id=f.thread_id").fetchall()
    by_key: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_key.setdefault(gl.fixture.truth[r["tid"]], []).append(r)
    for r in by_key.get("promise_no_fix", []):
        assert r["outcome"] == "open"
        assert r["verification"] == "textual_only"
    for r in by_key.get("silent_fix", []):
        assert r["outcome"] == "open"
        assert r["code_changed_after"] == 1
    for r in by_key.get("design_rebutted", []):
        assert r["outcome"] == "justified_no_change"
    direct = 0
    for r in rows:
        if gl.fixture.applied.get(r["tid"]) in ("direct", "silent"):
            assert r["code_changed_after"] == 1
            if r["outcome"] in evaluate.CHANGE_OUTCOMES:
                assert r["verification"] == "direct"
                direct += 1
    assert direct > 5
    for r in rows:
        tm = json.loads(r["timings"])
        assert set(tm) == {"first_response", "decision", "implementation", "resolution"}
        for v in tm.values():
            assert v.get("wall_h", 1) >= 0


def test_evaluate_needs_snapshot(conn: sqlite3.Connection) -> None:
    with pytest.raises(RuntimeError, match="snapshot"):
        evaluate.run_evaluate(conn, Config())
