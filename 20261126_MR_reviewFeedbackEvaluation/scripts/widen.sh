#!/usr/bin/env bash
# widen.sh: widen the analysed scope step by step, with Ollama work in chunks of one hour.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/widen.sh                 run all steps from the first unfinished one
#         touch out/widen.STOP             stop after the current chunk (remove the file to resume)
# Needs:  MRREVIEW_GITLAB_URL, MRREVIEW_GITLAB_TOKEN (or GITLAB_TOKEN), MRREVIEW_FOCUS_USER.
# Steps:  1 focus projects only · 2 top 50 active projects · 3 top 100 · 4 all active projects.
#         The focus user's projects rank first in every step.
# Chunk:  check that no other model is loaded on the shared Ollama box, then
#         `mrreview run <step> --max-minutes 60` (exit 0 = step done, exit 3 = more work: same step again).
# Every chunk is idempotent: collection, evidence and classification resume where they stopped.
# A failed chunk (any other exit code) stops the chain and is logged; it never deletes data.
set -uo pipefail
cd "$(dirname "$0")/.."

DB=${DB:-out/real/mrreview.sqlite3}
OUT=${OUT:-out/real/dashboard.html}
LOG=${LOG:-out/widen.log}
CHUNK_MINUTES=${CHUNK_MINUTES:-60}
FOCUS=${MRREVIEW_FOCUS_USER:?set MRREVIEW_FOCUS_USER}
OLLAMA=${MRREVIEW_OLLAMA_URL:-http://192.168.100.67:11434}
MODEL=${MRREVIEW_OLLAMA_MODEL:-qwen3.6:35b-a3b-q4_K_M-agentic}
export MRREVIEW_GITLAB_TOKEN=${MRREVIEW_GITLAB_TOKEN:-${GITLAB_TOKEN:-}}
STEPS=(
  "--focus-user $FOCUS --focus-only"
  "--focus-user $FOCUS --max-projects 50"
  "--focus-user $FOCUS --max-projects 100"
  "--focus-user $FOCUS"
)
mkdir -p "$(dirname "$LOG")"

log() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

box_free() {  # true when the shared box has no model loaded, or only ours
  local loaded
  loaded=$(curl --noproxy '*' -fsS -m 10 "$OLLAMA/api/ps" | python3 -c \
    'import json,sys; print(" ".join(m["name"] for m in json.load(sys.stdin)["models"]))') || return 1
  [ -z "$loaded" ] || [ "$loaded" = "$MODEL" ]
}

step=${START_STEP:-1}
while [ "$step" -le "${#STEPS[@]}" ]; do
  args=${STEPS[$((step - 1))]}
  if [ -e out/widen.STOP ]; then log "stop file found; stopping before step $step"; exit 0; fi
  if ! box_free; then log "Ollama box busy or unreachable; waiting 10 minutes"; sleep 600; continue; fi
  log "step $step chunk start: $args"
  # shellcheck disable=SC2086
  uv run mrreview --db "$DB" run $args --max-minutes "$CHUNK_MINUTES" --out "$OUT" >>"$LOG" 2>&1
  rc=$?
  case $rc in
    0) log "step $step done"; step=$((step + 1)) ;;
    3) log "step $step: chunk done, more work remains" ;;
    *) log "step $step failed with exit code $rc; chain stopped"; exit "$rc" ;;
  esac
done
log "all steps done"
