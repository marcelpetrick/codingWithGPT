#!/usr/bin/env bash
# v6-runnerup.sh -- add the runner-up, occamy-1.0, to arm pi1118, so the champion (KAT, already in the
# arm) and the runner-up are measured under the same server state as pi. Waits for v6-q8.sh to end.
# Same harness and restart logic as v6-run.sh. Idempotent. Deletes nothing.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; V4="$HERE/../ollamaClaudeCode_v4_tielCoder"
ARM=pi1118; LOG="$V4/results/s15-$ARM.log"
export ARM RUNS=3 MODELS_OVERRIDE="occamy-1.0:q5km-ctx256k-agentic"
cd "$V4"
until grep -qE 'V6-Q8-END|STOPPED' results/s15-pi1118q8.log 2>/dev/null; do sleep 60; done
for pass in 1 2 3 4; do
  ./s15-refresh.sh; rc=$?
  last="$(grep -E 'STOPPED:|S15-REFRESH-DONE' "$LOG" | tail -1)"
  case "$last" in
    *S15-REFRESH-DONE*) break ;;
    *"STOPPED: time budget"*) continue ;;
    *) echo "[v6-runnerup] stop, exit $rc: $last" >>"$LOG"; break ;;
  esac
done
python3 ./refresh-compare.py --arm "$ARM" >/dev/null 2>&1
cp "$V4/results/refresh-$ARM.md" "$HERE/results/" 2>/dev/null
echo "[v6-runnerup] V6-RUNNERUP-END" >>"$LOG"
timeout 5 notify-send "v6 runner-up ended" "results/refresh-$ARM.md" 2>/dev/null || true
