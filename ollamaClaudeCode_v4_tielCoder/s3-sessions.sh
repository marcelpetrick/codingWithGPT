#!/usr/bin/env bash
# s3-sessions.sh — stage S3 of plan.md: every model, both fixtures, n runs.
#
# Round-robin rather than model-by-model: run 1 of every model happens before
# run 2 of any model. .67 is shared, so conditions drift over a two-hour stage
# (a colleague's session, thermal state); taking all three runs of one model in
# a block would hand that drift to a single model as if it were its speed.
#
# The server is emptied before each model's block of sessions, and the model
# that just ran is passed to idle.sh as --mine, so the qwen3.6 control can be
# unloaded without evicting anyone else.
#
# Usage: RUNS=3 ./s3-sessions.sh            (models are the v4 field, below)
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"
RUNS="${RUNS:-3}"

T1="Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest"
MODELS=(
  "$T1"
  "tiel-coder:35b-q5-ctx256k-agentic"
  "north-mini-code-1.0:q4_K_M-ctx256k-agentic"
  "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic"
  "ornith:35b-ctx256k-agentic"
  "qwen3.6:35b-a3b-q4_K_M-agentic"
  "nemotron-3.5-lightning:30b-ctx256k-agentic"
  "nemotron-cascade-2:30b-ctx256k-agentic"
  "qwen3.8:27b-q4_K_M-ctx128k-agentic"
)
[ -n "${ONLY_MODELS:-}" ] && IFS='|' read -r -a MODELS <<< "$ONLY_MODELS"

PREV=""
for R in $(seq 1 "$RUNS"); do
  for M in "${MODELS[@]}"; do
    "$D/idle.sh" --mine "$M" ${PREV:+--mine "$PREV"} || { echo "ABORT: server busy" >&2; exit 1; }
    "$D/cc-session.sh" --fixture easy --runs 1 --first-run "$R" --timeout 900 "$M"
    "$D/cc-session.sh" --fixture hard --runs 1 --first-run "$R" --timeout 1200 "$M"
    # Thinking off only where the template implements <|think_off|>, i.e. Tiel. The
    # shipped tag stands for both Tiel tags (same template). Any other model would
    # silently run with thinking on under an "off" label.
    if [ "$M" = "$T1" ]; then
      "$D/cc-session.sh" --fixture easy --runs 1 --first-run "$R" --timeout 900 --thinking off "$M"
      "$D/cc-session.sh" --fixture hard --runs 1 --first-run "$R" --timeout 1200 --thinking off "$M"
    fi
    PREV="$M"
  done
done
"$D/idle.sh" ${PREV:+--mine "$PREV"}
echo S3-DONE
