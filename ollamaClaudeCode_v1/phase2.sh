#!/usr/bin/env bash
# phase2.sh — everything that must run after run-matrix.sh finishes.
#
# Waits for the matrix to complete (it owns both GPUs; running concurrently would
# corrupt the speed numbers), then:
#
#   1. re-runs the T6 needle gates for the two models whose first-pass T6 data is
#      void (the "ThThTh" haystack bug, see review2.md)
#   2. benchmarks qwen3.6:35b-a3b-q4_K_M-ctx256k -- the config actually recommended
#      for deployment, since the MoE was measured holding 262144 fully in VRAM.
#      Measured rather than inferred from the 128k row.
#   3. benchmarks qwen3.5:9b-ctx80k and -ctx96k on the OLD server .37 with the same
#      corrected harness, so the cross-server comparison covers the agentic gates
#      and not just throughput. .37 runs Ollama 0.30.6 vs 0.32.5 on .67, which also
#      tests whether the num_ctx/2 overflow behaviour is general or version-specific.
#
# Results for .37 go to eval37/ and agentic37/ -- rows.tsv carries no host column,
# so mixing the two hosts in one file would silently confuse the report.
set -uo pipefail

DIR="$(dirname "$(readlink -f "$0")")"
LOG="$DIR/phase2.log"
NEW=192.168.100.67
OLD=192.168.100.37

log() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

worker() {
  log "=== phase2 waiting for matrix ==="
  while [ ! -f "$DIR/matrix.log.done" ]; do sleep 30; done
  log "=== matrix done, phase2 starting ==="

  # --- 1. repair the void needle rows -------------------------------------
  for M in "qwen3.6:35b-a3b-q4_K_M-ctx128k" "qwen3.6:27b-q4_K_M-ctx128k"; do
    log "--- needle retest: $M ---"
    "$DIR/needle-retest.sh" "$NEW" "$M" >>"$LOG" 2>&1
  done

  # --- 2. the recommended deployment config, measured ----------------------
  M="qwen3.6:35b-a3b-q4_K_M-ctx256k"
  log "--- $M : speed + context ---"
  "$DIR/evaluate.sh" "$NEW" "$M" "$DIR/eval" >>"$LOG" 2>&1
  log "--- $M : agentic gates ---"
  "$DIR/agentic-test.sh" "$NEW" "$M" "$DIR/agentic" >>"$LOG" 2>&1
  log "--- $M done ---"

  # --- 3. the old server, same harness ------------------------------------
  for M in "qwen3.5:9b-ctx80k" "qwen3.5:9b-ctx96k"; do
    log "--- OLD $OLD $M : speed + context ---"
    "$DIR/evaluate.sh" "$OLD" "$M" "$DIR/eval37" >>"$LOG" 2>&1
    log "--- OLD $OLD $M : agentic gates ---"
    "$DIR/agentic-test.sh" "$OLD" "$M" "$DIR/agentic37" >>"$LOG" 2>&1
    log "--- OLD $OLD $M done ---"
  done

  log "=== phase2 finished ==="
  : > "$LOG.done"
}

if [ "${_DETACHED:-0}" = "1" ]; then
  worker
else
  export _DETACHED=1
  setsid nohup "$0" </dev/null >>"$LOG" 2>&1 &
  disown 2>/dev/null || true
  sleep 2
  echo "phase2 detached (waits for matrix) — log: $LOG"
fi
