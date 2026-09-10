#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Profile tokenUsage2 against the real home directory.

Every stage the dashboard runs is timed first without instrumentation, for
honest wall-clock numbers, and then again under cProfile to show where the time
goes: cold indexing into an empty archive, a warm start from that archive, an
idle rescan, snapshot building for each period, frame rendering and the JSON
export. The archive lives in a temporary directory; nothing else is written.

Usage: scripts/profile_app.py [--repeat N] [--top N] [--width W --height H]
"""

import argparse
import cProfile
import io
import os
import pstats
import statistics
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokenusage2.aggregate import Period  # noqa: E402
from tokenusage2.cli import resolve_tz, snapshot_json  # noqa: E402
from tokenusage2.config import load_config  # noqa: E402
from tokenusage2.live import LiveSource  # noqa: E402
from tokenusage2.render import View, render  # noqa: E402
from tokenusage2.store import Store  # noqa: E402
from tokenusage2.tui import bucket_count, data_span, take_snapshot  # noqa: E402


def median_ms(action: Callable[[], object], repeat: int) -> float:
    samples = []
    for _ in range(repeat):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


def profiled(action: Callable[[], object], repeat: int, top: int) -> str:
    profile = cProfile.Profile()
    profile.enable()
    for _ in range(repeat):
        action()
    profile.disable()
    buffer = io.StringIO()
    stats = pstats.Stats(profile, stream=buffer).strip_dirs().sort_stats("tottime")
    stats.print_stats(top)
    lines = buffer.getvalue().splitlines()
    start = next((i for i, line in enumerate(lines) if "ncalls" in line), 0)
    return "\n".join(line for line in lines[start:] if line.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=5, help="runs per warm stage")
    parser.add_argument("--top", type=int, default=12, help="functions listed per stage")
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--height", type=int, default=48)
    args = parser.parse_args()

    env = dict(os.environ)
    home = Path.home()
    tz = resolve_tz(None, env)
    config = load_config(None, home, env)
    rows: list[tuple[str, float, str]] = []
    profiles: dict[str, str] = {}

    with tempfile.TemporaryDirectory() as scratch:

        def cold_source(name: str) -> LiveSource:
            return LiveSource(Store(Path(scratch) / f"{name}.sqlite"), home, env, config, tz)

        started = time.perf_counter()
        source = cold_source("timed")
        report = source.scan()
        rows.append(
            (
                "cold index (discover + scan)",
                (time.perf_counter() - started) * 1000,
                f"{report.files_read} files · {report.bytes_read / 2**20:,.0f} MiB · "
                f"{report.events_changed:,} events",
            )
        )
        source.close()
        profiles["cold index"] = profiled(lambda: cold_source("profiled").scan(), 1, args.top)

        archive = Path(scratch) / "timed.sqlite"

        def warm_start() -> LiveSource:
            return LiveSource(Store(archive), home, env, config, tz)

        rows.append(
            (
                "warm start (load archive)",
                median_ms(warm_start, args.repeat),
                f"{len(warm_start().events()):,} events",
            )
        )
        profiles["warm start"] = profiled(warm_start, args.repeat, args.top)

        source = warm_start()
        source.scan()
        rows.append(
            (
                "idle rescan",
                median_ms(source.scan, args.repeat),
                f"{source.ingestor.last_report.files_seen} files stat'ed",
            )
        )
        profiles["idle rescan"] = profiled(source.scan, args.repeat, args.top)

        now = time.time()
        for period in Period:
            view = View(period=period)
            count = bucket_count(
                view,
                args.width,
                args.height,
                len(source.accounts()),
                data_span(source, view, now, tz),
            )

            def snapshot(view: View = view, count: int = count) -> object:
                return take_snapshot(source, view, now=now, tz=tz, count=count)

            rows.append(
                (f"snapshot · {period}", median_ms(snapshot, args.repeat), f"{count} buckets")
            )
            if period is Period.DAY:
                profiles["snapshot · day"] = profiled(snapshot, args.repeat, args.top)

        view = View()
        count = bucket_count(
            view, args.width, args.height, len(source.accounts()), data_span(source, view, now, tz)
        )
        frame = take_snapshot(source, view, now=now, tz=tz, count=count)

        def draw() -> object:
            return render(frame, view, args.width, args.height, tz=tz)

        rows.append((f"render {args.width}x{args.height}", median_ms(draw, args.repeat), ""))
        profiles["render"] = profiled(draw, args.repeat, args.top)
        rows.append(
            ("json export", median_ms(lambda: snapshot_json(frame, tz, True), args.repeat), "")
        )
        source.close()

    print(f"{'stage':<32}{'median ms':>12}  notes")
    for stage, milliseconds, note in rows:
        print(f"{stage:<32}{milliseconds:>12,.1f}  {note}")
    for stage, text in profiles.items():
        print(f"\n== cProfile · {stage} (sorted by own time) ==\n{text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
