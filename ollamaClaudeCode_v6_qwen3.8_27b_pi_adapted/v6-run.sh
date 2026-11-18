#!/usr/bin/env bash
# v6-run.sh -- measure the pi adapter with the round 11-02 harness, unchanged, in arm pi1118.
# Arms: pi, its own base (same requantization), and KAT (the current default) as the bar.
# s15-refresh.sh stops at its time budget; this re-runs it until it reports DONE (idempotent,
# it skips every valid run). Any other stop ends this script. Deletes nothing.
# Usage: setsid nohup systemd-inhibit --what=sleep:idle ./v6-run.sh >/dev/null 2>&1 & disown
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
V4="$HERE/../ollamaClaudeCode_v4_tielCoder"
ARM=pi1118; LOG="$V4/results/s15-$ARM.log"
export ARM RUNS=3 MODELS_OVERRIDE="qwen3.8-pi:27b-q4km-ctx200k-nothink qwen3.8-base:27b-q4km-ctx200k-nothink kat-coder-v2.5:q5km-ctx256k-agentic"
cd "$V4"
for pass in 1 2 3 4 5 6; do
  ./s15-refresh.sh
  rc=$?
  last="$(grep -E 'STOPPED:|S15-REFRESH-DONE' "$LOG" | tail -1)"
  case "$last" in
    *S15-REFRESH-DONE*) break ;;
    *"STOPPED: time budget"*) continue ;;
    *) echo "[v6-run] stop, exit $rc: $last" >>"$LOG"; break ;;
  esac
done
python3 ./refresh-compare.py --arm "$ARM" >/dev/null 2>&1
cp "$V4/results/refresh-$ARM.md" "$HERE/results/" 2>/dev/null
echo "[v6-run] V6-RUN-END" >>"$LOG"
timeout 5 notify-send "v6 run ended" "results/refresh-$ARM.md" 2>/dev/null || true
