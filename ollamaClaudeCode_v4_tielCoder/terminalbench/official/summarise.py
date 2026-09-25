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
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Failure modes that mean "the harness broke", not "the model failed the task".
INFRA = {"unknown_agent_error", "agent_installation_failed", "test_timeout",
         "unknown_error", "fatal_llm_parse_error",
         # 2026-09-25: the one parse_error trial is occamy csv-to-parquet n2 #2 --
         # "API Error: No internet route (ENETUNREACH)", then "uv: command not
         # found" in the tests. A network fault, not the model (review_20260925).
         "parse_error"}

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
# "thinkon-ext" (the 09-25 extended subset) must come first: it also ends in
# neither marker otherwise, and would be misread as the legacy mixed arm.
ARM_MARKERS = ("thinkon-ext", "thinkon", "thinkoff")
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
    "polyglot-c-py":
        "instruction asks for /app/main.c.py (run as `gcc main.c.py`); the tests "
        "and the reference solution use /app/main.py.c. All 27 parity trials "
        "failed with \"python3: can't open file '/app/main.py.c'\", and following "
        "the instruction literally cannot work (gcc hands a .py file to the linker: "
        "'file format not recognized'). Found 2026-09-25 (review_20260925).",
}


def expected_trials(run_dir, n_tasks):
    """tasks x attempts, parsed from the run-id -- the only completeness test.

    The upstream harness writes run-level results.json from the FIRST finished
    trial and appends to it, and tb.lock exists for the whole life of the run.
    So neither file says "this pass finished": a pass cut off after 3 of 20
    trials looks exactly like a complete one, and its rate reads as a model
    result. Counting the trial directories against tasks x attempts is what
    actually answers the question.
    """
    m = re.search(r"-n(\d+)-\d+$", run_dir.name)
    return n_tasks * int(m.group(1)) if m else None


def main():
    runs = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "runs"
    def count(name):
        f = HERE / name
        return len([l for l in f.read_text().splitlines()
                    if l.strip() and not l.lstrip().startswith("#")]) if f.exists() else 0
    # each arm has its own frozen task file, and a pass is complete only
    # against THAT file's task count
    n_tasks = count("subset.txt")
    n_tasks_ext = count("subset-ext-scored.txt")
    incomplete = []
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
        want = expected_trials(rj.parent, n_tasks_ext if "-thinkon-ext-" in run_id else n_tasks)
        have = len(list(rj.parent.glob("*/*/results.json")))
        if want and have < want:
            incomplete.append((run_id, have, want))
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
    if incomplete:
        print("\nIN FLIGHT or CUT SHORT -- not counted (a partial pass is not a rate):")
        for run_id, have, want in incomplete:
            print(f"  {run_id}  {have}/{want} trials")
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
        print(f"\n{'model':44} {'solved':>10} {'rate':>7} {'95% CI':>15} "
              f"{'void':>5} {'defect':>7} {'mean_s':>9}")   # a MEAN incl. timeouts, not a median (review_20260925 #7)
        sub = {k[1]: v for k, v in agg.items() if k[0] == arm}
        for m, a in sorted(sub.items(), key=lambda kv: -(kv[1]["soln"] / max(kv[1]["n"], 1))):
            rate = a["soln"] / a["n"] * 100 if a["n"] else 0.0
            avg = a["sec"] / a["n"] if a["n"] else 0.0
            lo, hi = wilson(a["soln"], a["n"])
            ci = f"[{lo:.0f}, {hi:.0f}]"
            warn = "  <-- VOID trials, investigate" if a["void"] else ""
            print(f"{m:44} {a['soln']:>4}/{a['n']:<5} {rate:>6.1f}% {ci:>15} "
                  f"{a['void']:>5} {a['defect']:>7} {avg:>9.0f}{warn}")
        print("\n   The interval is 95% Wilson. Two models whose intervals overlap "
              "are not ranked by\n   this round -- on a 9-task scored subset that "
              "is most of the field, which is the\n   point: the subset sizes the "
              "question it can answer.")


def wilson(k, n, z=1.96):
    """95% Wilson score interval for a resolved rate, in percentage points.

    Adopted 2026-09-21 from the r/LocalLLaMA tool-eval method (toTest.md §E),
    which published confidence intervals over 5 seeds where we were running n=1
    and n=3. The interval is the honest form of this round's most expensive
    lesson: on a 10-task subset, n=1 put Tiel at 40% and CyberTiel at 20% while
    n=3 put them at 37% and 27%. A rate printed without its width invites exactly
    the reading that a single lucky sample deserves -- north-mini's 50% read as a
    tie for the lead and settled at 41% once it was asked twice more.

    Wilson rather than normal-approximation because n here is 9-30 trials and the
    rates sit near 0.3-0.6, where the normal interval runs off the end of the
    scale and reports impossible bounds.
    """
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, (centre - half)) * 100, min(1.0, (centre + half)) * 100)


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
