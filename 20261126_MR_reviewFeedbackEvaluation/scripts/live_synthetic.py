# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Classify the synthetic fixture with the real Ollama server (live LLM smoke, D-007).

Usage: uv run python scripts/live_synthetic.py <db_path> [limit]
Only synthetic data is sent. The run is idempotent: a rerun reuses valid results.
"""

import os
import sys
from pathlib import Path

from mrreview import analyze, collect, db, evaluate, llm, normalize
from mrreview.config import load_config
from mrreview.demo.fake_gitlab import FakeGitLab, serve
from mrreview.demo.fixture import REFERENCE_NOW, build_fixture
from mrreview.gitlab import GitLabClient
from mrreview.http import UrllibTransport


def main() -> int:
    path = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    cfg = load_config(None, os.environ)
    conn = db.connect(path)
    fake = FakeGitLab(build_fixture(), token="demo")
    with serve(fake) as url:
        client = GitLabClient(url, "demo", UrllibTransport())
        collect.run_collect(client, conn, cfg, REFERENCE_NOW, print)
    print(normalize.build_threads(conn))
    oc = llm.OllamaClient(cfg.ollama_url, UrllibTransport(), timeout=cfg.ollama_timeout_s)
    stats = analyze.run_analyze(conn, cfg, oc, lambda m: print(m, flush=True), limit=limit)
    print(stats)
    print(evaluate.run_evaluate(conn, cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
