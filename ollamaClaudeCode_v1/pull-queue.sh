#!/usr/bin/env bash
# pull-queue.sh — pull several models onto a remote Ollama server, one at a
# time, surviving terminal/agent teardown.
#
# Sequential on purpose: parallel pulls split the same link and make disk
# exhaustion harder to attribute if it happens.
#
# See pull-detached.sh for why a client must stay attached (measured: the
# server does not progress on its own).
set -uo pipefail

HOST="${HOST:-192.168.100.67}"
BASE="http://${HOST}:11434"
DIR="$(dirname "$(readlink -f "$0")")"
LOG="$DIR/pull-queue.log"

MODELS=(
  "qwen3.6:35b-a3b-q4_K_M"       # MoE, primary recommendation
  "qwen3.6:27b-q4_K_M"           # dense q4, isolates quantisation vs the q8 we have
  "qwen3.6:35b-a3b-mtp-q4_K_M"   # MoE + multi-token prediction
)

log() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }

have() {
  curl -s --max-time 10 "$BASE/api/tags" \
    | jq -e --arg m "$1" '.models[]?|select(.name==$m)' >/dev/null 2>&1
}

worker() {
  log "=== queue start on $HOST: ${MODELS[*]} ==="
  for M in "${MODELS[@]}"; do
    if have "$M"; then log "SKIP $M (already present)"; continue; fi
    log "--- pulling $M ---"
    local tries=0
    while ! have "$M"; do
      tries=$((tries+1))
      [ "$tries" -gt 40 ] && { log "GIVE UP on $M after $tries attempts"; break; }
      log "$M attempt #$tries"
      curl -sN -X POST "$BASE/api/pull" -H "Content-Type: application/json" \
        -d "{\"model\":\"$M\",\"stream\":true}" 2>>"$LOG" \
      | tr '\r' '\n' \
      | awk -v lf="$LOG" -v m="$M" '
          function stamp() { cmd="date +\"%F %T\""; cmd|getline ts; close(cmd); return ts }
          /"error"/ { printf "%s  %s ERROR %s\n", stamp(), m, $0 >> lf; fflush(lf); next }
          /completed/ {
            n++
            if (n % 800 == 0) {
              match($0,/"completed":[0-9]+/); c=substr($0,RSTART+12,RLENGTH-12)
              match($0,/"total":[0-9]+/);     t=substr($0,RSTART+8,RLENGTH-8)
              if (t>0) {
                printf "%s  %s %.1f%%  %.2f/%.2f GB\n", stamp(), m, c*100/t, c/1e9, t/1e9 >> lf
                fflush(lf)
              }
            }
            next
          }
          /"status"/ { printf "%s  %s %s\n", stamp(), m, $0 >> lf; fflush(lf) }
        '
      have "$M" && break
      log "$M connection dropped — resuming in 10s"
      sleep 10
    done
    have "$M" && log "OK $M present"
  done
  log "=== queue finished ==="
  : > "$LOG.done"
}

if [ "${_DETACHED:-0}" = "1" ]; then
  worker
else
  export _DETACHED=1
  if command -v systemd-inhibit >/dev/null 2>&1; then
    setsid nohup systemd-inhibit --what=idle:sleep --why="ollama pull queue" \
      "$0" </dev/null >>"$LOG" 2>&1 &
  else
    setsid nohup "$0" </dev/null >>"$LOG" 2>&1 &
  fi
  disown 2>/dev/null || true
  sleep 2
  echo "queue detached — log: $LOG"
fi
