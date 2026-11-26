# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line interface. Run `mrreview --help`."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from mrreview import __version__, analyze, collect, db, evaluate, llm, normalize, quality, report
from mrreview.config import Config, ConfigError, load_config
from mrreview.demo import fake_gitlab, fake_ollama
from mrreview.demo.fixture import REFERENCE_NOW, build_fixture
from mrreview.gitlab import GitLabClient
from mrreview.http import UrllibTransport


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, file=sys.stderr, flush=True)


def _gitlab(cfg: Config) -> GitLabClient:
    if not cfg.gitlab_url or not cfg.gitlab_token:
        raise ConfigError("set MRREVIEW_GITLAB_URL and MRREVIEW_GITLAB_TOKEN (read_api scope)")
    return GitLabClient(
        cfg.gitlab_url,
        cfg.gitlab_token,
        UrllibTransport(),
        per_page=cfg.per_page,
        timeout=cfg.http_timeout_s,
        max_retries=cfg.max_retries,
        backoff_base=cfg.backoff_base_s,
    )


def _ollama(cfg: Config) -> llm.OllamaClient:
    return llm.OllamaClient(cfg.ollama_url, UrllibTransport(), timeout=cfg.ollama_timeout_s)


def _stages(
    conn: sqlite3.Connection,
    cfg: Config,
    args: argparse.Namespace,
    gl: GitLabClient,
    ol: llm.OllamaClient,
    out: Path,
    *,
    demo: bool = False,
    now: datetime | None = None,
) -> None:
    collect.run_collect(
        gl,
        conn,
        cfg,
        now or datetime.now(UTC),
        _log,
        max_projects=getattr(args, "max_projects", None),
        max_mrs=getattr(args, "max_mrs", None),
    )
    _log(f"normalize: {normalize.build_threads(conn)}")
    analyze.run_analyze(conn, cfg, ol, _log, limit=getattr(args, "limit", None))
    _log(f"evaluate: {evaluate.run_evaluate(conn, cfg)}")
    _log(f"report: {report.write_report(conn, cfg, out, demo=demo)}")


def cmd_demo(args: argparse.Namespace, cfg: Config) -> int:
    """Run the whole pipeline on the synthetic fixture."""
    out = Path(args.out)
    cfg = replace(cfg, db_path=out / "demo.sqlite3")
    conn = db.connect(cfg.db_path)
    fake = fake_gitlab.FakeGitLab(
        build_fixture(seed=args.seed), token="demo-token"  # noqa: S106 - fake server token
    )
    with fake_gitlab.serve(fake) as url:
        gl = GitLabClient(url, "demo-token", UrllibTransport())
        if args.live:
            _stages(
                conn,
                cfg,
                args,
                gl,
                _ollama(cfg),
                out / "dashboard.html",
                demo=True,
                now=REFERENCE_NOW,
            )
        else:
            stub = fake_ollama.FakeOllama()
            with fake_ollama.serve(stub) as ourl:
                cfg = replace(cfg, ollama_model=fake_ollama.STUB_MODEL, ollama_url=ourl)
                ol = llm.OllamaClient(ourl, UrllibTransport())
                _stages(
                    conn, cfg, args, gl, ol, out / "dashboard.html", demo=True, now=REFERENCE_NOW
                )
    conn.close()
    return 0


def cmd_smoke(args: argparse.Namespace, cfg: Config) -> int:
    """Bounded live run against the real GitLab and Ollama (REQ-OPS-1)."""
    if not args.authorized:
        print(
            "refused: a live run reads real review data. Confirm the authorization of VISION.md "
            "section 8, then pass --authorized.",
            file=sys.stderr,
        )
        return 2
    out = Path(args.out)
    cfg = replace(cfg, db_path=out / "smoke.sqlite3")
    conn = db.connect(cfg.db_path)
    _stages(conn, cfg, args, _gitlab(cfg), _ollama(cfg), out / "smoke_dashboard.html")
    print(json.dumps(db.work_summary(conn)))
    conn.close()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mrreview", description=__doc__)
    p.add_argument("--version", action="version", version=f"mrreview {__version__}")
    p.add_argument("--config", type=Path, help="TOML configuration file")
    p.add_argument("--db", type=Path, help="SQLite database path (overrides the configuration)")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="discover projects and collect MR history")
    c.add_argument("--max-projects", type=int)
    c.add_argument("--max-mrs", type=int, help="most recent MRs per project (bounded sample)")
    a = sub.add_parser("analyze", help="classify substantive threads with Ollama")
    a.add_argument("--limit", type=int)
    sub.add_parser("evaluate", help="verify outcomes and compute timings")
    r = sub.add_parser("report", help="write the HTML dashboard")
    r.add_argument("--out", type=Path, default=Path("out/dashboard.html"))
    r.add_argument("--demo", action="store_true", help="label the report as synthetic demo data")
    run = sub.add_parser("run", help="all stages: collect, normalize, analyze, evaluate, report")
    run.add_argument("--out", type=Path, default=Path("out/dashboard.html"))
    run.add_argument("--max-projects", type=int)
    run.add_argument("--max-mrs", type=int)
    run.add_argument("--limit", type=int)
    sub.add_parser("status", help="show work state and coverage")
    d = sub.add_parser("demo", help="run everything on synthetic data")
    d.add_argument("--out", default="out/demo")
    d.add_argument("--seed", type=int, default=7)
    d.add_argument("--live", action="store_true", help="use the real Ollama instead of the stub")
    sm = sub.add_parser("smoke", help="bounded live run against real GitLab and Ollama")
    sm.add_argument("--authorized", action="store_true")
    sm.add_argument("--out", default="out/smoke")
    sm.add_argument("--max-projects", type=int, default=2)
    sm.add_argument("--max-mrs", type=int, default=5)
    sm.add_argument("--limit", type=int, default=20)
    sa = sub.add_parser("sample", help="write a stratified sample for manual annotation")
    sa.add_argument("--n", type=int, default=40)
    sa.add_argument("--out", type=Path, default=Path("out/annotation_sample.csv"))
    ag = sub.add_parser("agreement", help="model vs human agreement of an annotated sample")
    ag.add_argument("file", type=Path)
    args = p.parse_args(argv)
    try:
        cfg = load_config(args.config, os.environ)
        if args.db:
            cfg = replace(cfg, db_path=args.db)
        if args.cmd == "demo":
            return cmd_demo(args, cfg)
        if args.cmd == "smoke":
            return cmd_smoke(args, cfg)
        if args.cmd == "agreement":
            print(json.dumps(quality.agreement(args.file), indent=2))
            return 0
        conn = db.connect(cfg.db_path)
        if args.cmd == "collect":
            collect.run_collect(
                _gitlab(cfg),
                conn,
                cfg,
                datetime.now(UTC),
                _log,
                max_projects=args.max_projects,
                max_mrs=args.max_mrs,
            )
            _log(f"normalize: {normalize.build_threads(conn)}")
        elif args.cmd == "analyze":
            analyze.run_analyze(conn, cfg, _ollama(cfg), _log, limit=args.limit)
        elif args.cmd == "evaluate":
            _log(f"evaluate: {evaluate.run_evaluate(conn, cfg)}")
        elif args.cmd == "report":
            _log(f"report: {report.write_report(conn, cfg, args.out, demo=args.demo)}")
        elif args.cmd == "run":
            _stages(conn, cfg, args, _gitlab(cfg), _ollama(cfg), args.out)
        elif args.cmd == "status":
            print(json.dumps(collect.collect_summary(conn), indent=2, default=str))
        elif args.cmd == "sample":
            print(f"wrote {quality.write_sample(conn, args.out, args.n)} rows to {args.out}")
        conn.close()
    except (ConfigError, collect.StopRun, LookupError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
