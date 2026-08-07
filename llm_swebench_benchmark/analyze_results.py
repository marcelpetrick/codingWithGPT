#!/usr/bin/env python3
"""
Summarise a SWE-bench evaluation run, and diff it against a previous run.

Reports the two numbers that matter separately:
  * apply rate     -- how many patches reached the test stage at all
                      (an evaluation-pipeline property)
  * resolution rate -- how many applied patches actually fixed the issue
                      (the model's property)

Conflating the two is what produced the misleading 20.7% headline in the
first run: it was computed over the biased subset that happened to apply.
"""

import argparse
import glob
import json
import os
from collections import Counter


def load_run(run_dir: str) -> dict:
    """instance_id -> report dict for every report.json under a run directory."""
    out = {}
    for path in glob.glob(os.path.join(run_dir, "*/*/report.json")):
        try:
            data = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue
        for iid, inner in data.items():
            out[iid] = inner
    return out


def summarise(reports: dict, total_dataset: int) -> dict:
    applied = sum(1 for r in reports.values() if r.get("patch_successfully_applied"))
    resolved = sum(1 for r in reports.values() if r.get("resolved"))
    return {
        "evaluated": len(reports),
        "applied": applied,
        "resolved": resolved,
        # Denominator is the whole dataset: the honest figure, not the
        # subset that happened to survive the pipeline.
        "resolution_rate_full": resolved / total_dataset * 100 if total_dataset else 0.0,
        "resolution_rate_applied": resolved / applied * 100 if applied else 0.0,
        "apply_rate": applied / len(reports) * 100 if reports else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="logs/run_evaluation/<run_id>")
    ap.add_argument("--baseline", help="previous run dir to compare against")
    ap.add_argument("--dataset-size", type=int, default=300)
    ap.add_argument("--json-out", help="write machine-readable summary here")
    args = ap.parse_args()

    cur = load_run(args.run)
    if not cur:
        raise SystemExit(f"no report.json found under {args.run}")
    s = summarise(cur, args.dataset_size)

    print(f"run: {args.run}")
    print(f"  dataset instances      : {args.dataset_size}")
    print(f"  reached test stage     : {s['evaluated']}")
    print(f"  patch applied          : {s['applied']} ({s['apply_rate']:.1f}% of evaluated)")
    print(f"  resolved               : {s['resolved']}")
    print(f"  RESOLUTION (full set)  : {s['resolved']}/{args.dataset_size} = {s['resolution_rate_full']:.1f}%")
    print(f"  resolution (of applied): {s['resolution_rate_applied']:.1f}%")

    if args.baseline:
        base = load_run(args.baseline)
        if base:
            b = summarise(base, args.dataset_size)
            print(f"\nbaseline: {args.baseline}")
            print(f"  reached test stage     : {b['evaluated']}")
            print(f"  resolved               : {b['resolved']}")
            print(f"  RESOLUTION (full set)  : {b['resolved']}/{args.dataset_size} = {b['resolution_rate_full']:.1f}%")

            print("\ndelta")
            print(f"  reached test stage : {b['evaluated']:>4d} -> {s['evaluated']:>4d}  ({s['evaluated']-b['evaluated']:+d})")
            print(f"  resolved           : {b['resolved']:>4d} -> {s['resolved']:>4d}  ({s['resolved']-b['resolved']:+d})")
            print(f"  resolution (full)  : {b['resolution_rate_full']:.1f}% -> {s['resolution_rate_full']:.1f}%")

            newly = sorted(i for i, r in cur.items()
                           if r.get("resolved") and not base.get(i, {}).get("resolved"))
            regressed = sorted(i for i, r in base.items()
                               if r.get("resolved") and not cur.get(i, {}).get("resolved"))
            print(f"\n  newly resolved ({len(newly)}):")
            for i in newly:
                print(f"    + {i}")
            if regressed:
                print(f"\n  REGRESSED ({len(regressed)}):")
                for i in regressed:
                    print(f"    - {i}")
            else:
                print("\n  regressions: none")

    by_repo = Counter()
    tot_repo = Counter()
    for iid, r in cur.items():
        repo = iid.rsplit("-", 1)[0]
        tot_repo[repo] += 1
        if r.get("resolved"):
            by_repo[repo] += 1
    print("\nresolved by repo (evaluated instances):")
    for repo in sorted(tot_repo):
        print(f"  {by_repo[repo]:>3d}/{tot_repo[repo]:<3d}  {repo}")

    if args.json_out:
        json.dump(s, open(args.json_out, "w"), indent=2)
        print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()
