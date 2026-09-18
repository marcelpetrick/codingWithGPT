#!/usr/bin/env python3
"""summarise.py -- fold every upstream terminal-bench run into one TSV + a table.

Reads runs/*/results.json (the harness's own output format, unmodified) and
writes results/terminal-bench-official.tsv for the report generator.

The column that matters as much as the score is **failure_mode**. The upstream
harness reports an infrastructure failure -- a container that would not build, an
agent that could not be installed, a timeout -- as an unresolved trial, which is
indistinguishable from "the model tried and got it wrong" if you only read
`accuracy`. We saw exactly that today: a missing docker-compose plugin produced a
clean "Accuracy: 0.00%". So we break the number out by failure mode and treat any
non-model failure as VOID, not as a zero (harness §0).

Usage: summarise.py [runs_dir]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Failure modes that mean "the harness broke", not "the model failed the task".
INFRA = {"unknown_agent_error", "agent_installation_failed", "test_timeout",
         "unknown_error", "fatal_llm_parse_error"}


def main():
    runs = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "runs"
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    rows = []
    for rj in sorted(runs.glob("*/results.json")):
        run_id = rj.parent.name
        if run_id.startswith("selfcheck") or run_id.startswith("smoke"):
            continue
        try:
            d = json.loads(rj.read_text())
        except ValueError:
            print(f"  ! unreadable: {rj}")
            continue
        for r in d.get("results", []):
            rows.append({
                "run_id": run_id,
                "model": run_id.rsplit("-n", 1)[0],
                "task": r.get("task_id", "?"),
                "trial": r.get("trial_name", "?"),
                "resolved": bool(r.get("is_resolved")),
                "failure_mode": r.get("failure_mode", "unset"),
                "in_tok": r.get("total_input_tokens") or 0,
                "out_tok": r.get("total_output_tokens") or 0,
                "agent_sec": _dur(r.get("agent_started_at"), r.get("agent_ended_at")),
            })

    tsv = out / "terminal-bench-official.tsv"
    cols = ["run_id", "model", "task", "trial", "resolved", "failure_mode",
            "in_tok", "out_tok", "agent_sec"]
    with tsv.open("w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")
    print(f"wrote {tsv}  ({len(rows)} trials)")

    # per-model roll-up, with infra failures held out of the denominator
    agg = defaultdict(lambda: {"soln": 0, "n": 0, "void": 0, "sec": 0.0})
    for r in rows:
        a = agg[r["model"]]
        if r["failure_mode"] in INFRA:
            a["void"] += 1
            continue
        a["n"] += 1
        a["soln"] += int(r["resolved"])
        a["sec"] += r["agent_sec"]
    if not agg:
        print("no trials yet"); return
    print(f"\n{'model':44} {'solved':>10} {'rate':>7} {'void':>5} {'median_s':>9}")
    for m, a in sorted(agg.items(), key=lambda kv: -(kv[1]["soln"] / max(kv[1]["n"], 1))):
        rate = a["soln"] / a["n"] * 100 if a["n"] else 0.0
        avg = a["sec"] / a["n"] if a["n"] else 0.0
        warn = "  <-- VOID trials, investigate" if a["void"] else ""
        print(f"{m:44} {a['soln']:>4}/{a['n']:<5} {rate:>6.1f}% {a['void']:>5} {avg:>9.0f}{warn}")


def _dur(a, b):
    if not a or not b:
        return 0.0
    from datetime import datetime
    try:
        return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()
    except ValueError:
        return 0.0


if __name__ == "__main__":
    main()
