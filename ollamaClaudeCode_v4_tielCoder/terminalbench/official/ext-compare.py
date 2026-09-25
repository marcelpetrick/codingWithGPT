#!/usr/bin/env python3
"""ext-compare.py -- KAT-Coder vs Tiel-Coder on correctness, over every task both
have run at thinking parity: the 9 scored parity tasks (n=3) plus the scored
extended tasks (n=2, arm thinkon-ext). Reads results/terminal-bench-official.tsv
as written by summarise.py, so it inherits its rules: complete passes only,
defective tasks out, infrastructure failures void.

Applies the decision rule fixed in s11-ext.sh before any extended result:
non-overlapping pooled intervals, else a paired sign test over tasks at p < 0.05,
else a tie on correctness (and the 09-24 rule stands).
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

from summarise import DEFECTIVE, INFRA, wilson

HERE = Path(__file__).resolve().parent
MODELS = {"kat-coder-v2.5_q5km-ctx256k-agentic": "KAT-Coder",
          "tiel-coder_35b-q5-ctx256k-agentic": "Tiel-Coder"}
ARMS = ("thinkon", "thinkon-ext")


def main():
    tsv = HERE / "results" / "terminal-bench-official.tsv"
    per = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # model -> task -> [solved, live]
    with tsv.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["model"] not in MODELS or r["arm"] not in ARMS:
                continue
            if r["task"] in DEFECTIVE or r["failure_mode"] in INFRA:
                continue
            c = per[r["model"]][r["task"]]
            c[1] += 1
            c[0] += r["resolved"] == "True"

    a, b = list(MODELS)
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
        print("VERDICT: tie on correctness -- the 09-24 rule stands, speed decides (KAT-Coder)")


if __name__ == "__main__":
    main()
