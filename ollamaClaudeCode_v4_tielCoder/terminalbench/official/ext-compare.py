#!/usr/bin/env python3
"""Compare the selected pair on extended Terminal-Bench correctness.

EXT_ONLY=1 is the decision arm: every scored extended task must have exactly
two valid trials per model. The mixed-client parity arm is information only.
Reads results/terminal-bench-official.tsv as written by summarise.py.

Applies the decision rule fixed in s11-ext.sh before any extended result:
non-overlapping pooled intervals, else a paired sign test over tasks at p < 0.05,
else a tie on correctness (and the 09-24 rule stands).
"""
import csv
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

from summarise import DEFECTIVE, INFRA, wilson

HERE = Path(__file__).resolve().parent
# the pair, as Ollama tags on the command line (s11-ext.sh passes them); default KAT vs Tiel
_TAGS = sys.argv[1:3] or ["kat-coder-v2.5:q5km-ctx256k-agentic", "tiel-coder:35b-q5-ctx256k-agentic"]
MODELS = {t.replace(":", "_").replace("/", "_").lower(): t.split(":")[0] for t in _TAGS}
# EXT_ONLY=1: the decision set -- the extended tasks only, where both models ran one
# pinned Claude Code version. Amended 2026-09-27 BEFORE any extended result existed:
# the parity rows mix client versions (2.1.278 vs 2.1.282), so pooling them in would
# carry the confound into the verdict. Without EXT_ONLY the pooled figure is printed
# for information.
ARMS = ("thinkon-ext",) if os.environ.get("EXT_ONLY") else ("thinkon", "thinkon-ext")


def main():
    tsv = HERE / "results" / "terminal-bench-official.tsv"
    per = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # model -> task -> [solved, live]
    infra = []
    with tsv.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["model"] not in MODELS or r["arm"] not in ARMS:
                continue
            if r["failure_mode"] in INFRA:
                infra.append(f'{r["model"]}/{r["task"]}: {r["failure_mode"]}')
                continue
            if r["task"] in DEFECTIVE:
                continue
            c = per[r["model"]][r["task"]]
            c[1] += 1
            c[0] += r["resolved"] == "True"

    a, b = list(MODELS)
    if os.environ.get("EXT_ONLY"):
        expected = {
            line.strip() for line in (HERE / "subset-ext-scored.txt").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        errors = []
        if not expected:
            errors.append("the scored extended task list is empty")
        if infra:
            errors.append("infrastructure failures: " + ", ".join(infra))
        for model in (a, b):
            missing = expected - per[model].keys()
            extra = per[model].keys() - expected
            wrong_n = {task: trials[1] for task, trials in per[model].items()
                       if task in expected and trials[1] != 2}
            if missing:
                errors.append(f"{model} missing: {', '.join(sorted(missing))}")
            if extra:
                errors.append(f"{model} unexpected: {', '.join(sorted(extra))}")
            if wrong_n:
                errors.append(f"{model} trial counts: {wrong_n}")
        if errors:
            raise SystemExit("extended comparison invalid; " + "; ".join(errors))

    common = sorted(set(per[a]) & set(per[b]))
    print(f"tasks run by both: {len(common)}")
    for m in (a, b):
        k = sum(per[m][t][0] for t in common)
        n = sum(per[m][t][1] for t in common)
        lo, hi = wilson(k, n)
        print(f"  {MODELS[m]:<11} {k:>3}/{n:<3} = {100 * k / n if n else 0:5.1f}%  95% CI [{lo:.0f}, {hi:.0f}]")

    wins_a = wins_b = 0
    for t in common:
        ra = per[a][t][0] / per[a][t][1]
        rb = per[b][t][0] / per[b][t][1]
        wins_a += ra > rb
        wins_b += rb > ra
    n_dec = wins_a + wins_b
    # exact two-sided sign test on the tasks where the two differ
    p = min(1.0, 2 * sum(math.comb(n_dec, i) for i in range(0, min(wins_a, wins_b) + 1)) / 2 ** n_dec) if n_dec else 1.0
    print(f"  paired over tasks: {MODELS[a]} better on {wins_a}, {MODELS[b]} better on {wins_b}, "
          f"equal on {len(common) - n_dec}; sign test p = {p:.3f}")

    ka, na = sum(per[a][t][0] for t in common), sum(per[a][t][1] for t in common)
    kb, nb = sum(per[b][t][0] for t in common), sum(per[b][t][1] for t in common)
    (la, ha), (lb, hb) = wilson(ka, na), wilson(kb, nb)
    if ha < lb or hb < la:
        w = MODELS[a] if la > hb else MODELS[b]
        print(f"VERDICT: {w} wins on correctness -- pooled intervals do not overlap")
    elif p < 0.05:
        w = MODELS[a] if wins_a > wins_b else MODELS[b]
        print(f"VERDICT: {w} wins on correctness -- paired sign test p = {p:.3f}")
    else:
        print("VERDICT: tie on correctness -- the rule falls back to quality and speed (s12)")


if __name__ == "__main__":
    main()
