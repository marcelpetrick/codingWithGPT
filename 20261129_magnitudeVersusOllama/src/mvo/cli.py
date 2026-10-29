# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line: ``mvo run``, ``mvo gate``, ``mvo report``, ``mvo --version``.

Exit codes: 0 done, 1 some rows failed or bad input, 2 the run stopped (engine unreachable or warm-up failed).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

from mvo.client import Engine, EngineError, EngineUnreachable
from mvo.report import write_reports
from mvo.runner import EXCLUSIONS, Arm, load_exclusions, run_arm
from mvo.sysinfo import git_commit, run_text
from mvo.version import __version__


def parse_cells(text: str) -> list[tuple[str, int]]:
    """Parse 'A:4096,B:1024' into [('A', 4096), ('B', 1024)]."""
    cells = []
    for part in text.split(","):
        workload, _, ctx = part.strip().partition(":")
        if workload not in ("A", "B", "C", "V") or not ctx.isdigit():
            raise ValueError(f"bad cell: {part!r} (use WORKLOAD:CTX, e.g. A:4096)")
        cells.append((workload, int(ctx)))
    return cells


def engine_version(spec: dict[str, Any]) -> str:
    """Ask the engine for its version (URL returning {"version": ...}, or a command)."""
    if "version_url" in spec:
        try:
            with urllib.request.urlopen(spec["version_url"], timeout=10) as response:
                return str(json.loads(response.read())["version"])
        except (OSError, ValueError, KeyError) as error:
            raise EngineUnreachable(f"version check failed: {error}") from error
    out = run_text(spec.get("version_cmd", []))
    if not out:
        raise EngineUnreachable(f"version command failed: {spec.get('version_cmd')}")
    return out.splitlines()[0].strip()


def load_arm(root: Path, label: str, site: str) -> tuple[Arm, dict[str, Any]]:
    """Read one arm from arms.json."""
    doc = json.loads((root / "arms.json").read_text(encoding="utf-8"))
    for spec in doc["arms"]:
        if spec["label"] == label:
            engine = Engine(
                name=spec["engine"],
                protocol=spec["protocol"],
                base_url=spec["base_url"],
                model=spec["model"],
                api_key=spec.get("api_key", ""),
                extra=spec.get("extra", {}),
            )
            arm = Arm(label, engine, engine_version(spec), spec["drafter"], spec["quant"], site)
            return arm, spec
    raise ValueError(f"unknown arm: {label}")


def exclude_rows(results_dir: Path, site: str, arm: str, prompt_id: str, reason: str) -> int:
    """Append an exclusion entry for every current good row of (site, arm, prompt_id)."""
    name = f"{site}_{arm}.jsonl"
    path = results_dir / name
    if not path.exists():
        print(f"error: no result file {path}", file=sys.stderr)
        return 1
    excluded = load_exclusions(results_dir)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    hits = [
        r for r in rows if r["prompt_id"] == prompt_id and r.get("ok") and (name, r["key"], r["time"]) not in excluded
    ]
    if not hits:
        print(f"error: no good rows of {prompt_id} in {path}", file=sys.stderr)
        return 1
    with (results_dir / EXCLUSIONS).open("a", encoding="utf-8") as handle:
        for r in hits:
            handle.write(json.dumps({"file": name, "key": r["key"], "time": r["time"], "reason": reason}) + "\n")
    print(f"excluded {len(hits)} rows of {prompt_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(prog="mvo", description=__doc__)
    parser.add_argument("--version", action="version", version=f"mvo {__version__}")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project folder (default: .)")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="measure one arm")
    run.add_argument("--arm", required=True)
    run.add_argument("--cells", required=True, help="e.g. A:4096,A:16384,B:1024,B:8192,C:4096,V:4096")
    run.add_argument("--reps", type=int, default=5)
    run.add_argument("--site", default="laptop")

    gate = sub.add_parser("gate", help="record a load / refuse result")
    for name in ("site", "engine", "model", "status", "detail"):
        gate.add_argument(f"--{name}", required=True)

    exclude = sub.add_parser("exclude", help="exclude the current good rows of one prompt, with a reason")
    exclude.add_argument("--site", required=True)
    exclude.add_argument("--arm", required=True)
    exclude.add_argument("--prompt-id", required=True)
    exclude.add_argument("--reason", required=True)

    sub.add_parser("report", help="write report.md and dashboard.html")

    args = parser.parse_args(argv)
    root: Path = args.root
    if args.command == "report":
        md, page = write_reports(root)
        print(f"wrote {md} and {page}")
        return 0
    if args.command == "exclude":
        return exclude_rows(root / "results", args.site, args.arm, args.prompt_id, args.reason)
    if args.command == "gate":
        row = {k: getattr(args, k) for k in ("site", "engine", "model", "status", "detail")}
        row["time"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
        (root / "results").mkdir(exist_ok=True)
        with (root / "results" / "gate.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return 0
    try:
        cells = parse_cells(args.cells)
        arm, _ = load_arm(root, args.arm, args.site)
        out = root / "results" / f"{args.site}_{args.arm}.jsonl"
        failed = run_arm(arm, cells, args.reps, out, commit=git_commit())
    except EngineUnreachable as error:
        print(f"STOP: engine unreachable: {error}", file=sys.stderr)
        return 2
    except EngineError as error:
        print(f"STOP: warm-up failed (model did not load or answer): {error}", file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"done, {failed} failed rows")
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
