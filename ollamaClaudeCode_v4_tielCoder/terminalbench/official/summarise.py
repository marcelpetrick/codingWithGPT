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

# Tasks that CANNOT be passed by following their own instruction. These are our
# problem, not the model's, and counting them is counting our defect as their
# failure -- the same reasoning that makes an infra failure VOID rather than a
# zero. Still run and still shown; simply not in the denominator.
# An "arm" is a configuration the whole field shared. It is parsed from the
# run-id because the run-id is the only thing the upstream harness carries into
# results.json, and because two arms merged into one rate is precisely the defect
# that voided round 1 (harness §8b): round 1 ran the subjects with reasoning off
# and the comparators with it on, and nothing in the output said so. Rows from
# round 1 are therefore labelled r1-mixed and are NEVER pooled with parity rows.
ARM_MARKERS = ("thinkon", "thinkoff")
LEGACY_ARM = "r1-mixed"


def split_arm(run_id):
    """run-id -> (model, arm). Unmarked ids are the 2026-09-18 mixed round."""
    base = run_id.rsplit("-n", 1)[0]
    for mark in ARM_MARKERS:
        if base.endswith("-" + mark):
            return base[: -(len(mark) + 1)], mark
    return base, LEGACY_ARM


DEFECTIVE = {
    "nginx-request-logging":
        "instruction says to configure /etc/nginx/conf.d/benchmark-site.conf; the "
        "tests read /etc/nginx/nginx.conf and require a log format named literally "
        "'detailed'. 0/12 in round 1, all on the same assertion, all with a correct "
        "config in the file the task named. 7 of 8 sub-tests passed every time.",
}


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
        model, arm = split_arm(run_id)
        for r in d.get("results", []):
            rows.append({
                "run_id": run_id,
                "model": model,
                "arm": arm,
                "task": r.get("task_id", "?"),
                "trial": r.get("trial_name", "?"),
                "resolved": bool(r.get("is_resolved")),
                "failure_mode": r.get("failure_mode", "unset"),
                # The upstream claude-code agent does not report token usage back
                # to the harness (agent-logs/ comes back empty, and both counters
                # are a literal 0 on every trial, including ones the model
                # demonstrably solved). Writing that 0 through would read as "used
                # no tokens" -- the exact silent-zero shape harness §0 exists to
                # catch -- so record it as "n/a" instead of a number.
                "in_tok": _tok(r.get("total_input_tokens")),
                "out_tok": _tok(r.get("total_output_tokens")),
                "agent_sec": _dur(r.get("agent_started_at"), r.get("agent_ended_at")),
            })

    tsv = out / "terminal-bench-official.tsv"
    cols = ["run_id", "model", "arm", "task", "trial", "resolved", "failure_mode",
            "in_tok", "out_tok", "agent_sec"]
    with tsv.open("w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]) for c in cols) + "\n")
    print(f"wrote {tsv}  ({len(rows)} trials)")

    # make-report.py reads every TSV from the REPO-level results/ directory, so
    # publish a copy there as well -- otherwise the official round is measured,
    # written and then silently missing from the report.
    repo_res = HERE.parent.parent / "results"
    if repo_res.is_dir():
        (repo_res / tsv.name).write_text(tsv.read_text())
        print(f"published  {repo_res / tsv.name}")

    # per-model roll-up, with infra failures held out of the denominator
    agg = defaultdict(lambda: {"soln": 0, "n": 0, "void": 0, "defect": 0, "sec": 0.0})
    for r in rows:
        a = agg[(r["arm"], r["model"])]
        if r["failure_mode"] in INFRA:
            a["void"] += 1
            continue
        if r["task"] in DEFECTIVE:
            a["defect"] += 1
            continue
        a["n"] += 1
        a["soln"] += int(r["resolved"])
        a["sec"] += r["agent_sec"]
    if not agg:
        print("no trials yet"); return
    if DEFECTIVE:
        print("\nheld out of the rate as DEFECTIVE (the task cannot be passed as written):")
        for t, why in DEFECTIVE.items():
            print(f"  {t} — {why}")
    ARM_NOTE = {
        LEGACY_ARM: "2026-09-18: thinking OFF on the Sharp-template models and ON for "
                    "every comparator. Model-vs-model VOID (harness §8b); kept for the "
                    "per-task and jitter findings, which compare a model to itself",
        "thinkon":  "thinking ON for every model -- the only symmetric setting this "
                    "harness can guarantee. This is the arm a ranking may be read from",
        "thinkoff": "thinking OFF, single-family arm only (Sharp template). Never a "
                    "cross-family comparison",
    }
    for arm in sorted({k[0] for k in agg}):
        print(f"\n== arm: {arm} ==\n   {ARM_NOTE.get(arm, '?')}")
        print(f"\n{'model':44} {'solved':>10} {'rate':>7} {'void':>5} {'defect':>7} {'median_s':>9}")
        sub = {k[1]: v for k, v in agg.items() if k[0] == arm}
        for m, a in sorted(sub.items(), key=lambda kv: -(kv[1]["soln"] / max(kv[1]["n"], 1))):
            rate = a["soln"] / a["n"] * 100 if a["n"] else 0.0
            avg = a["sec"] / a["n"] if a["n"] else 0.0
            warn = "  <-- VOID trials, investigate" if a["void"] else ""
            print(f"{m:44} {a['soln']:>4}/{a['n']:<5} {rate:>6.1f}% {a['void']:>5} "
                  f"{a['defect']:>7} {avg:>9.0f}{warn}")


def _tok(v):
    """0 from this agent means 'not reported', not 'none used'. Say so."""
    return v if v else "n/a"


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
