#!/usr/bin/env bash
# pull-detached.sh — pull a model onto a remote Ollama server and keep going
# after the launching terminal (or Claude Code) exits.
#
# Why this exists: Ollama's /api/pull downloads only while an HTTP client stays
# attached. Measured on 2026-08-04 — with no client connected the transfer
# advanced 126 MB in 45 s versus the ~990 MB a full-rate transfer would give.
# The download is therefore driven by the client, not by the server.
#
# Two things make it survivable:
#   - setsid detaches into a new session, so terminal/agent teardown cannot
#     signal it
#   - blobs are resumable, so a retry loop picks up where a dropped connection
#     left off instead of restarting
#
# Usage:
#   ./pull-detached.sh 192.168.100.67 qwen3.6:35b-a3b-q4_K_M
#   tail -f pull-<model>.log
set -uo pipefail

HOST="${1:?usage: pull-detached.sh <host> <model>}"
MODEL="${2:?usage: pull-detached.sh <host> <model>}"
BASE="http://${HOST}:11434"
LOG="$(dirname "$(readlink -f "$0")")/pull-$(echo "$MODEL" | tr ':/' '__').log"

log() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

worker() {
  log "START pull $MODEL from $BASE"
  local attempt=0
  while true; do
    # already there?
    if curl -s --max-time 10 "$BASE/api/tags" \
        | jq -e --arg m "$MODEL" '.models[]?|select(.name==$m)' >/dev/null 2>&1; then
      log "DONE — $MODEL present on $HOST"
      # leave a marker the caller can test for
      : > "${LOG}.done"
      return 0
    fi

    attempt=$((attempt+1))
    log "attempt #$attempt — attaching to /api/pull"

    # No --max-time: we want this connection to live as long as it can.
    # Progress lines are sampled (every ~500th) to keep the log small.
    curl -sN -X POST "$BASE/api/pull" \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"$MODEL\",\"stream\":true}" 2>>"$LOG" \
    | tr '\r' '\n' \
    | awk -v lf="$LOG" '
        function stamp() { cmd = "date +\"%F %T\""; cmd | getline ts; close(cmd); return ts }
        /completed/ {
          n++
          if (n % 500 == 0) {
            match($0, /"completed":[0-9]+/); c = substr($0, RSTART+12, RLENGTH-12)
            match($0, /"total":[0-9]+/);     t = substr($0, RSTART+8,  RLENGTH-8)
            if (t > 0) {
              printf "%s  %.1f%%  %.2f/%.2f GB\n", stamp(), c*100/t, c/1e9, t/1e9 >> lf
              fflush(lf)
            }
          }
          next
        }
        /"status"/ { printf "%s  %s\n", stamp(), $0 >> lf; fflush(lf) }
      '

    log "connection ended — retrying in 10s (blobs resume, no data lost)"
    sleep 10
  done
}

# Detach: new session so terminal/agent teardown cannot reach us. Inhibit only
# *idle* suspend — a lid close will still suspend the machine unless the user's
# power settings say otherwise.
if [ "${_DETACHED:-0}" = "1" ]; then
  worker
else
  export _DETACHED=1
  if command -v systemd-inhibit >/dev/null 2>&1; then
    setsid nohup systemd-inhibit --what=idle:sleep --why="ollama pull $MODEL" \
      "$0" "$HOST" "$MODEL" </dev/null >>"$LOG" 2>&1 &
  else
    setsid nohup "$0" "$HOST" "$MODEL" </dev/null >>"$LOG" 2>&1 &
  fi
  disown 2>/dev/null || true
  sleep 2
  echo "detached. pid group $!"
  echo "log: $LOG"
fi
