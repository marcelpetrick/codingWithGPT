#!/usr/bin/env python3
"""compare-arms.py -- what changed when reasoning came back on.

The 2026-09-18 round ran the Sharp-template models with reasoning off and every
comparator with it on, then read the gap as capability (harness §8b). The re-run
fixes the asymmetry; this script is what reads the two arms against each other,
and it exists so the comparison is computed rather than eyeballed.

It reports three things, in the order they should be trusted:

  1. REASONING ACTUALLY EMITTED, counted from the transcripts. Never from the
     config -- a model that ignores a flag fails silently, which is the whole
     lesson. A parity arm where some model still shows 0 blocks is not a parity
     arm, and the script says so before it prints a single rate.
  2. Per-model rate per arm, each with its 95% Wilson interval, and whether the
     two arms are separated at all for that model.
  3. The per-task grid, because a rate that did not move can still hide tasks
     that flipped in both directions.

Usage: ./compare-arms.py [--runs DIR] [--base r1-mixed] [--arm thinkon]
"""
import argparse
import csv
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from summarise import DEFECTIVE, INFRA, wilson  # noqa: E402

THINK_MARKER = '"type":"thinking"'


def reasoning_by_model(runs: Path, arm_suffix: str):
    """Count reasoning blocks per model from the agent transcripts themselves."""
    agg = defaultdict(lambda: {"blocks": 0, "trials": 0, "silent": 0})
    for log in runs.glob(f"*{arm_suffix}*/*/*/sessions/agent.log"):
        if log.parts[len(runs.parts)].startswith(("smoke", "selfcheck", "void-")):
            continue
        model = log.parts[len(runs.parts)].rsplit("-n", 1)[0]
        n = len(re.findall(re.escape(THINK_MARKER), log.read_text(errors="replace")))
        a = agg[model]
        a["blocks"] += n
        a["trials"] += 1
        a["silent"] += (n == 0)
    return agg


def rows_by_arm(tsv: Path):
    by_arm = defaultdict(list)
    with tsv.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            by_arm[r.get("arm", "r1-mixed")].append(r)
    return by_arm


def rate(rows):
    live = [r for r in rows
            if r["failure_mode"] not in INFRA and r["task"] not in DEFECTIVE]
    if not live:
        return None
    k = sum(r["resolved"] == "True" for r in live)
    return k, len(live), wilson(k, len(live))


def strip_arm(model):
    for mark in ("-thinkon", "-thinkoff"):
        if model.endswith(mark):
            return model[: -len(mark)]
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(HERE / "runs"))
    ap.add_argument("--base", default="r1-mixed")
    ap.add_argument("--arm", default="thinkon")
    a = ap.parse_args()
    runs = Path(a.runs)
    by_arm = rows_by_arm(HERE / "results" / "terminal-bench-official.tsv")

    print(f"\n=== 1. reasoning actually emitted, arm '{a.arm}' "
          f"(counted in the transcripts, not the config) ===\n")
    think = reasoning_by_model(runs, a.arm)
    if not think:
        print("   no transcripts for this arm yet")
    bad = []
    for m, t in sorted(think.items()):
        flag = ""
        if t["blocks"] == 0:
            flag = "   <-- SILENT: this model did not reason. The arm is NOT parity."
            bad.append(m)
        print(f"   {strip_arm(m):50} {t['trials']:3d} trials {t['blocks']:5d} blocks"
              f"  ({t['silent']} silent){flag}")
    if bad:
        print("\n   !! Do not read a ranking off this arm until that is explained.\n")

    print(f"\n=== 2. rate per arm, with 95% Wilson intervals ===\n")
    models = sorted({strip_arm(r["model"]) for r in by_arm.get(a.arm, [])})
    if not models:
        print("   the parity arm has no rows yet\n")
        return
    print(f"   {'model':44} {'base':>18} {'parity':>18}   verdict")
    for m in models:
        base = rate([r for r in by_arm.get(a.base, []) if strip_arm(r["model"]) == m])
        new = rate([r for r in by_arm.get(a.arm, []) if strip_arm(r["model"]) == m])
        if not new:
            continue
        bs = (f"{base[0]}/{base[1]} [{base[2][0]:.0f},{base[2][1]:.0f}]"
              if base else "not run")
        ns = f"{new[0]}/{new[1]} [{new[2][0]:.0f},{new[2][1]:.0f}]"
        if base:
            # "moved" only if the intervals do not overlap: anything else is the
            # same measurement twice, and this round exists because a point
            # estimate was read as a change once already.
            sep = base[2][1] < new[2][0] or new[2][1] < base[2][0]
            verdict = ("MOVED" if sep else "not separated")
        else:
            verdict = "no base"
        print(f"   {m:44} {bs:>18} {ns:>18}   {verdict}")

    print(f"\n=== 3. per-task, parity arm (solved/live) ===\n")
    grid = defaultdict(dict)
    tasks = []
    for r in by_arm.get(a.arm, []):
        m = strip_arm(r["model"])
        grid[m].setdefault(r["task"], []).append(r)
        if r["task"] not in tasks:
            tasks.append(r["task"])
    for m in models:
        cells = []
        for t in tasks:
            rows = grid[m].get(t, [])
            if not rows:
                cells.append(f"{t}:-")
                continue
            if t in DEFECTIVE:
                cells.append(f"{t}:DEFECT")
                continue
            live = [r for r in rows if r["failure_mode"] not in INFRA]
            ok = sum(r["resolved"] == "True" for r in live)
            mark = "SOLVED" if ok == len(live) else ("failed" if ok == 0 else "FLIPS")
            cells.append(f"{t}:{ok}/{len(live)} {mark}")
        print(f"   {m}")
        for c in cells:
            print(f"      {c}")
    print()


if __name__ == "__main__":
    main()
