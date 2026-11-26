# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""More integration paths: live demo flag, concurrent stop."""

from dataclasses import replace
from pathlib import Path

import pytest

from mrreview import analyze, cli, collect, llm, normalize
from mrreview.demo import fake_ollama
from mrreview.demo.fixture import REFERENCE_NOW
from mrreview.http import UrllibTransport

from .conftest import Env


def test_demo_live_flag_uses_configured_ollama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with fake_ollama.serve(fake_ollama.FakeOllama()) as url:
        monkeypatch.setenv("MRREVIEW_OLLAMA_URL", url)
        monkeypatch.setenv("MRREVIEW_OLLAMA_MODEL", fake_ollama.STUB_MODEL)
        assert cli.main(["demo", "--live", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "dashboard.html").exists()


def test_concurrent_run_stops_when_server_dies(gl: Env, conn: object) -> None:
    import sqlite3

    assert isinstance(conn, sqlite3.Connection)
    cfg = replace(gl.cfg, ollama_model=fake_ollama.STUB_MODEL, ollama_concurrency=3)
    collect.run_collect(gl.client, conn, cfg, REFERENCE_NOW, max_projects=1)
    normalize.build_threads(conn)
    with fake_ollama.serve(fake_ollama.FakeOllama()) as url:
        info = llm.OllamaClient(url, UrllibTransport()).model_info(fake_ollama.STUB_MODEL)
    dead = llm.OllamaClient(url, UrllibTransport(), max_retries=0)
    dead.model_info = lambda _m: info  # type: ignore[method-assign]
    with pytest.raises(collect.StopRun):
        analyze.run_analyze(conn, cfg, dead)
    assert conn.execute("SELECT COUNT(*) FROM classifications WHERE status='ok'").fetchone()[0] == 0
