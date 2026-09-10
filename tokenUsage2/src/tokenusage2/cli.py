# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Command line entry point: live dashboard, one frame, JSON, or the sources report."""

import argparse
import json
import os
import shutil
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tokenusage2.aggregate import GroupBy, Metric, Period, Snapshot, Tally
from tokenusage2.config import ConfigError, load_config
from tokenusage2.demo import DemoSource
from tokenusage2.live import LiveSource, Source
from tokenusage2.render import THEME_NAMES, View, mask, render
from tokenusage2.store import Store, StoreError
from tokenusage2.tui import bucket_count, data_span, run, status_text, take_snapshot
from tokenusage2.version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tokenusage2",
        description="Live token usage of Claude Code, Codex CLI and OpenCode across every "
        "local account, as daily, weekly and monthly views.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="print one frame and exit")
    mode.add_argument("--json", action="store_true", help="print a JSON snapshot and exit")
    mode.add_argument(
        "--doctor",
        action="store_true",
        help="show discovered homes, sources and reconciliation, then exit",
    )
    parser.add_argument(
        "--demo", action="store_true", help="use synthetic data (safe for screenshots)"
    )
    parser.add_argument("--period", choices=[p.value for p in Period], default="day")
    parser.add_argument(
        "--group",
        choices=[g.value for g in GroupBy],
        default="account",
        help="what colours the timeline",
    )
    parser.add_argument(
        "--breakdown",
        choices=[g.value for g in GroupBy],
        default="model",
        help="how the selected bucket is broken down",
    )
    parser.add_argument("--metric", choices=[m.value for m in Metric], default="total")
    parser.add_argument("--account", help="show only this account (label or id)")
    parser.add_argument(
        "--theme", choices=THEME_NAMES, help="colour theme (default: 'plain' when NO_COLOR is set)"
    )
    parser.add_argument("--interval", type=float, default=2.0, help="refresh seconds")
    parser.add_argument("--archive", type=Path, help="archive database path")
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="keep everything in memory (re-reads all logs every start)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="config file (default: $XDG_CONFIG_HOME/tokenusage2/config.toml)",
    )
    parser.add_argument("--home", type=Path, help="search agent homes under this directory")
    parser.add_argument("--tz", help="IANA time zone for day boundaries (default: system)")
    parser.add_argument("--width", type=int, help="frame width for --once")
    parser.add_argument("--height", type=int, help="frame height for --once")
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="colour for --once (auto: only on a terminal)",
    )
    parser.add_argument("--redact", action="store_true", help="mask e-mail addresses")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def resolve_tz(name: str | None, env: Mapping[str, str]) -> tzinfo:
    candidate = name or env.get("TZ", "").lstrip(":")
    if candidate:
        return ZoneInfo(candidate)
    try:
        with Path("/etc/localtime").open("rb") as handle:
            return ZoneInfo.from_file(handle, key="localtime")
    except OSError, ValueError:  # pragma: no cover - depends on the host
        return datetime.now().astimezone().tzinfo or ZoneInfo("UTC")


def default_archive(home: Path, env: Mapping[str, str]) -> Path:
    base = Path(env.get("XDG_DATA_HOME") or home / ".local" / "share")
    return base / "tokenusage2" / "archive.sqlite"


def _tally(tally: Tally) -> dict:
    return {**asdict(tally), "total": tally.total}


def _iso(ts: float | None, tz: tzinfo) -> str | None:
    return datetime.fromtimestamp(ts, tz).isoformat(timespec="seconds") if ts else None


def snapshot_json(snapshot: Snapshot, tz: tzinfo, redact: bool) -> dict:
    return {
        "generated_at": _iso(snapshot.now, tz),
        "period": str(snapshot.period),
        "group": str(snapshot.group),
        "metric": str(snapshot.metric),
        "totals": {
            name: _tally(getattr(snapshot, name)) for name in ("today", "week", "month", "all")
        },
        "rate_tokens_per_minute": round(snapshot.rate, 1),
        "accounts": [
            {
                "id": row.id,
                "label": row.label,
                "tool": str(row.tool),
                "identity": mask(row.identity) if redact else row.identity,
                "plan": row.plan,
                "running": row.running,
                "archived": row.archived,
                "last_request": _iso(row.last_ts, tz),
                **{name: _tally(getattr(row, name)) for name in ("today", "week", "month", "all")},
                "quotas": [
                    {
                        "window": q.window,
                        "used_percent": q.used,
                        "resets_at": _iso(q.resets_at, tz),
                        "observed_at": _iso(q.observed_at, tz),
                        "source": q.source,
                    }
                    for q in row.quotas
                ],
            }
            for row in snapshot.accounts
        ],
        "buckets": [
            {
                "start": bucket.start.isoformat(),
                "label": bucket.long,
                "total": _tally(bucket.total),
                "groups": {name: _tally(tally) for name, tally in bucket.groups.items()},
            }
            for bucket in snapshot.buckets
        ],
        "breakdown": {
            "bucket": snapshot.selected_bucket.long if snapshot.selected_bucket else None,
            "by": str(snapshot.detail),
            "rows": [
                {"name": row.name, "extra": row.extra, **_tally(row.tally)}
                for row in snapshot.breakdown
            ],
        },
    }


def _account_id(source: Source, wanted: str | None) -> str | None:
    if wanted is None:
        return None
    for account in source.accounts():
        if wanted in {account.id, account.label}:
            return account.id
    raise LookupError(wanted)


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    proc: Path = Path("/proc"),
    clock: Callable[[], float] = time.time,
) -> int:
    args = build_parser().parse_args(argv)
    env = dict(os.environ) if env is None else dict(env)
    home = args.home or Path(env.get("HOME") or Path.home())
    try:
        tz = resolve_tz(args.tz, env)
    except ZoneInfoNotFoundError, ValueError:
        print(f"tokenusage2: unknown time zone: {args.tz or env.get('TZ')}", file=sys.stderr)
        return 2
    if args.interval <= 0:
        print("tokenusage2: --interval must be positive", file=sys.stderr)
        return 2

    source: Source
    if args.demo:
        source = DemoSource(tz, clock)
    else:
        try:
            config = load_config(args.config, home, env)
            archive = None if args.no_archive else args.archive or default_archive(home, env)
            store = Store(archive)
        except (ConfigError, StoreError) as error:
            print(f"tokenusage2: {error}", file=sys.stderr)
            return 2
        source = LiveSource(store, home, env, config, tz, proc, clock)
    try:
        return _run(args, source, env, tz, clock)
    finally:
        source.close()


def _run(
    args: argparse.Namespace,
    source: Source,
    env: Mapping[str, str],
    tz: tzinfo,
    clock: Callable[[], float],
) -> int:
    try:
        account = _account_id(source, args.account)
    except LookupError:
        labels = ", ".join(a.label for a in source.accounts()) or "none"
        print(f"tokenusage2: unknown account {args.account!r} (known: {labels})", file=sys.stderr)
        return 2
    theme = args.theme or ("plain" if env.get("NO_COLOR") else "default")
    view = View(
        period=Period(args.period),
        group=GroupBy(args.group),
        metric=Metric(args.metric),
        detail=GroupBy(args.breakdown),
        theme=theme,
        redact=args.redact,
        interval=args.interval,
        account=account,
    )

    if args.doctor:
        source.scan()
        print("\n".join(source.sources()))
        return 0
    if args.json or args.once:
        report = source.scan()
        width, height = shutil.get_terminal_size((160, 48))
        width, height = args.width or width, args.height or height
        now = clock()
        count = bucket_count(
            view, width, height, len(source.accounts()), data_span(source, view, now, tz)
        )
        snapshot = take_snapshot(source, view, now=now, tz=tz, count=count)
        if args.json:
            print(json.dumps(snapshot_json(snapshot, tz, args.redact), indent=2))
            return 0
        colored = args.color == "always" or (args.color == "auto" and sys.stdout.isatty())
        if not colored:
            view.theme = "plain"
        lines = render(
            snapshot,
            view,
            width,
            height,
            tz=tz,
            status=status_text(report, source, view),
            mode=source.mode,
        )
        print("\n".join(lines))
        return 0
    if not (sys.stdout.isatty() and sys.stdin.isatty()):
        print(
            "tokenusage2: the live dashboard needs a terminal; use --once, --json or --doctor",
            file=sys.stderr,
        )
        return 2
    return run(source, view, tz, clock=clock)
