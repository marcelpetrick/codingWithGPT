#!/usr/bin/env bash
# Follow-up to resume-ext-chain.sh (2026-10-05). Queues on the SAME lock, so it
# starts only after that chain has exited, and then:
#   1. re-runs, per model of the pair, the extended tasks whose every trial was
#      an infrastructure failure (write-compressor: image build hit a stale apt
#      layer, fixed by a --no-cache rebuild at 14:10), as a "-ext-repair" run
#   2. prints the extended verdict (summarise.py applies a repair only over
#      VOID-only tasks; ext-compare.py still refuses anything incomplete)
#   3. runs the Laguna XS 2.1 screen the stopped chain could not reach
# Any other kind of stop -- a task with mixed VOID/real trials, a missing pass,
# a busy box -- ends this script for a human to read. Idempotent: completed
# repair passes and a screened Laguna are skipped by the scripts it calls.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
TBO="$HERE/terminalbench/official"
LOG="results/s11-ext.log"
export TB_CC_VERSION="${TB_CC_VERSION:-2.1.283}"
PAIR=()
while IFS= read -r line; do PAIR+=("$line"); done < <(grep -vE '^\s*#|^\s*$' results/ext-models.txt)
say () { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*"; }
finish () {
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    say "REPAIR-CHAIN-DONE: repair, verdict and Laguna complete"
    timeout 5 notify-send "v4 repair chain complete" "Verdict in results/s11-ext.log, Laguna in results/s10-laguna-xs21.log." 2>/dev/null || true
  else
    say "REPAIR-CHAIN-STOPPED: exit $rc"
    timeout 5 notify-send "v4 repair chain stopped" "Check the repair chain log in results/ (exit $rc)." 2>/dev/null || true
  fi
}
trap finish EXIT

exec 9>/tmp/codingWithGPT-v4-ext-chain.lock
say "waiting for the extended chain to release its lock"
flock 9
say "lock acquired; pair: ${PAIR[*]}; Claude Code $TB_CC_VERSION"

# 1. which tasks need a repair, per model (VOID-only tasks); stop on mixed ones
repair_list () {  # <model tag> -> task names, one per line; exit 4 on a mixed task
  ( cd "$TBO" && python3 - "$1" <<'PY'
import json, sys
from pathlib import Path
from summarise import INFRA
slug = sys.argv[1].replace(":", "_").replace("/", "_").lower()
runs = sorted(p for p in Path("runs").glob(f"{slug}-thinkon-ext-n2-*") if (p / "results.json").exists())
if not runs:
    sys.exit(f"no extended pass for {slug}")
results = json.loads((runs[-1] / "results.json").read_text())["results"]
want = 2 * sum(1 for l in Path("subset-ext-scored.txt").read_text().splitlines()
               if l.strip() and not l.lstrip().startswith("#"))
if len(results) < want:
    sys.exit(f"{runs[-1].name}: {len(results)}/{want} trials -- the pass did not finish")
trials = {}
for r in results:
    trials.setdefault(r["task_id"], []).append(r.get("failure_mode", "unset") in INFRA)
mixed = [t for t, v in trials.items() if any(v) and not all(v)]
if mixed:
    print("mixed VOID/real trials, needs a human: " + ", ".join(mixed), file=sys.stderr)
    sys.exit(4)
print("\n".join(sorted(t for t, v in trials.items() if all(v))))
PY
  )
}

for M in "${PAIR[@]}"; do
  tasks="$(repair_list "$M")"
  [ -n "$tasks" ] || { say "repair: $M has no VOID-only task"; continue; }
  slug="$(echo "$M" | tr '/:' '__' | tr 'A-Z' 'a-z')"
  sub="subset-ext-repair-$slug.txt"
  { echo "# 2026-10-05 repair of VOID-only extended tasks for $M"; echo "$tasks"; } > "$TBO/$sub"
  say "repair: $M, n=2 on: $(echo "$tasks" | tr '\n' ' ')"
  ( cd "$TBO" && TB_SUBSET="$sub" TB_ARM_SUFFIX=-ext-repair TB_THINKING=on TB_PHASE=2 \
      ./GO_official_tb.sh "$M" ) 2>&1 | tail -12 | tee -a "$LOG"
done
python3 ./make-dashboard.py >/dev/null 2>&1

# 2. the verdict
say "3/3 comparison (after repair)" | tee -a "$LOG"
( cd "$TBO" && python3 summarise.py | grep -E "repair|IN FLIGHT|wrote" \
  && EXT_ONLY=1 python3 ext-compare.py "${PAIR[@]}" \
  && echo "-- pooled with the 8 parity tasks (information only: mixed client versions)" \
  && python3 ext-compare.py "${PAIR[@]}" | grep -v VERDICT ) 2>&1 | tee -a "$LOG"
say "S11-EXT-DONE (after repair)" | tee -a "$LOG"
python3 ./make-dashboard.py >/dev/null 2>&1

# 3. Laguna
say "starting Laguna"
./s10-one.sh laguna-xs21
