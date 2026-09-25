#!/usr/bin/env bash
# s11-ext.sh -- the extended Terminal-Bench round, KAT-Coder vs Tiel-Coder on
# correctness (owner's question 2026-09-25: "it has not passed all tests
# reliably?"). The 9-task subset is +-17 points and separates nobody.
#
#   1. ORACLE on the 30 tasks of terminalbench/official/subset-ext.txt: a task
#      whose own reference solution fails is defective and is dropped BEFORE any
#      model runs (the nginx lesson) -> subset-ext-scored.txt
#   2. KAT, then Tiel: every scored task x n=2, thinking on (arm thinkon-ext)
#   3. ext-compare.py: pooled rate (9 parity tasks x3 + ext tasks x2) and a
#      paired per-task sign test
#
# Decision rule, fixed here before any extended result exists:
#   - pooled 95% intervals do not overlap          -> the higher one wins on correctness
#   - else paired sign test over tasks, p < 0.05   -> the task-wise winner wins on correctness
#   - else a tie on correctness                    -> the 09-24 rule stands (speed decides: KAT)
#
# Idempotent: the oracle list is reused if present, and complete passes are
# skipped by GO_official_tb.sh. Waits for the box like the other drivers.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
TBO="$HERE/terminalbench/official"
LOG="$HERE/results/s11-ext.log"
BASE="http://192.168.100.67:11434"
# The two models compared. Default KAT vs Tiel; if the s12 re-baseline changes who the
# two most promising are, write them (two tags, one per line, best first) to
# results/ext-models.txt BEFORE this runs -- the comparison and its rule are unchanged.
if [ -s results/ext-models.txt ]; then mapfile -t PAIR < <(grep -vE '^\s*#|^\s*$' results/ext-models.txt | head -2)
else PAIR=(kat-coder-v2.5:q5km-ctx256k-agentic tiel-coder:35b-q5-ctx256k-agentic); fi
say () { printf '\n\033[1m[%s] %s\033[0m\n' "$(date +%H:%M)" "$*" | tee -a "$LOG"; }

say "waiting for the box"
while pgrep -f '^bash \./(GO_official_tb|s9-candidates|s10-one|run-all|refine-ab)\.sh' >/dev/null 2>&1; do sleep 60; done
curl -s -m 10 "$BASE/api/version" >/dev/null || { say "server unreachable -- stopping"; exit 3; }

# T5 x8 for any model of the pair that s12 did not re-gate (qwen3.6 was not in its list)
for M in "${PAIR[@]}"; do
  grep -q "^$M	T5	" results/gate-rerun.tsv 2>/dev/null || python3 ./gate-rerun.py --host "$BASE" --n 8 --gate T5 "$M" 2>&1 | tail -2 | tee -a "$LOG"
done

cd "$TBO"
if [ ! -s subset-ext-scored.txt ]; then
  say "1/3 oracle on the 30 extended tasks"
  mapfile -t EXT < <(grep -vE '^\s*#|^\s*$' subset-ext.txt)
  TARGS=(); for t in "${EXT[@]}"; do TARGS+=(-t "$t"); done
  OID="selfcheck-oracle-ext-$(date +%H%M%S)"
  export PYTHONPATH="$TBO/../..:${PYTHONPATH:-}"
  "${TB_VENV:-$TBO/tb-venv}/bin/tb" run -d "terminal-bench-core==0.1.1" "${TARGS[@]}" \
      -a oracle --n-concurrent 2 --output-path runs --run-id "$OID" 2>&1 | tail -15 | tee -a "$LOG"
  python3 - "runs/$OID" <<'PY' | tee -a "$LOG"
import glob, json, sys
from pathlib import Path
res = {}
for f in glob.glob(f"{sys.argv[1]}/*/*/results.json"):
    d = json.load(open(f))
    res[d.get("task_id") or Path(f).parts[-3]] = bool(d.get("is_resolved"))
tasks = [l.strip() for l in open("subset-ext.txt") if l.strip() and not l.lstrip().startswith("#")]
ok = [t for t in tasks if res.get(t)]
bad = [t for t in tasks if not res.get(t)]
hdr = ("# Scored extended subset: the tasks of subset-ext.txt whose ORACLE (reference\n"
       f"# solution) passed, run {sys.argv[1]}. Dropped as defective ({len(bad)}): "
       + (", ".join(bad) or "none") + "\n")
open("subset-ext-scored.txt", "w").write(hdr + "\n".join(ok) + "\n")
print(f"oracle: {len(ok)} of {len(tasks)} tasks pass; dropped: {', '.join(bad) or 'none'}")
PY
fi
cd "$HERE"

for M in "${PAIR[@]}"; do
  say "2/3 extended round: $M, n=2"
  ( cd "$TBO" && TB_SUBSET=subset-ext-scored.txt TB_ARM_SUFFIX=-ext TB_THINKING=on TB_PHASE=2 \
      ./GO_official_tb.sh "$M" ) 2>&1 | tail -12 | tee -a "$LOG"
  python3 ./make-dashboard.py >/dev/null 2>&1
done

say "3/3 comparison"
( cd "$TBO" && python3 summarise.py >/dev/null && python3 ext-compare.py "${PAIR[@]}" ) 2>&1 | tee -a "$LOG"
say "S11-EXT-DONE"
