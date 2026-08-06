#!/usr/bin/env bash
# run-matrix.sh — evaluate every candidate on .67, speed + agentic gates.
#
# Only ctx-baked variants are listed. A model with num_ctx unset is capped at
# 16384 tokens through /v1/messages and stops emitting tool calls past that
# (see ctx-cliff.sh), so testing the bare tag would measure a configuration
# nobody should actually run.
set -uo pipefail

HOST="${HOST:-192.168.100.67}"
DIR="$(dirname "$(readlink -f "$0")")"
LOG="$DIR/matrix.log"

MODELS=(
  "qwen3.6:35b-a3b-q4_K_M-ctx128k"      # MoE q4 24GB - primary candidate
  "qwen3.6:27b-q4_K_M-ctx128k"          # dense q4 17GB - quantisation axis
  "qwen3.6:27b-q8_0-ctx60k"             # dense q8 30GB - Alex's variant
  "qwen3.6:27b-mtp-q8_0-ctx60k"         # dense q8 + multi-token prediction
  "qwen3.6:27b-mtp-q8_0-ctx128k"        # same at 128k - expected to split, worth proving
  "qwen3.5:9b-ctx80k"                   # 9B baseline, comparable to .37
  "qwen3.6:35b-a3b-mtp-q4_K_M-ctx128k"  # MoE + MTP, if the pull finished
)

log() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

exists() {
  curl -s --max-time 10 "http://$HOST:11434/api/tags" \
    | jq -e --arg m "$1" '.models[]?|select(.name==$m)' >/dev/null 2>&1
}

worker() {
  log "=== matrix start on $HOST ==="
  for M in "${MODELS[@]}"; do
    if ! exists "$M"; then log "SKIP $M (not on server)"; continue; fi
    log "--- $M : speed + context ---"
    "$DIR/evaluate.sh" "$HOST" "$M" "$DIR/eval" >>"$LOG" 2>&1
    log "--- $M : agentic gates ---"
    "$DIR/agentic-test.sh" "$HOST" "$M" "$DIR/agentic" >>"$LOG" 2>&1
    log "--- $M done ---"
  done
  log "=== matrix finished ==="
  : > "$LOG.done"
}

if [ "${_DETACHED:-0}" = "1" ]; then
  worker
else
  export _DETACHED=1
  setsid nohup "$0" </dev/null >>"$LOG" 2>&1 &
  disown 2>/dev/null || true
  sleep 2
  echo "matrix detached — log: $LOG"
fi
