#!/usr/bin/env bash
# pull-queue.sh — pull several models onto a remote Ollama server, one at a
# time, surviving terminal/agent teardown.
#
# Copied from ../ollamaClaudeCode_v1/pull-queue.sh; only the model list differs.
# The v1 script is left untouched because its log is the provenance of v1's
# measurements.
#
# Sequential on purpose: parallel pulls split the same link and make disk
# exhaustion harder to attribute if it happens. .67 exposes no free-disk field
# and we have no shell on it, so a full disk shows up first as a failed write —
# one pull at a time keeps that attributable to one model.
#
# See ../ollamaClaudeCode_v1/pull-detached.sh for why a client must stay
# attached (measured 2026-08-04: with no client connected the transfer advanced
# 126 MB in 45 s against the ~990 MB a full-rate transfer would give — the
# server does not progress on its own).
set -uo pipefail

HOST="${HOST:-192.168.100.67}"
BASE="http://${HOST}:11434"
DIR="$(dirname "$(readlink -f "$0")")"
LOG="$DIR/pull-queue.log"

# Stage B of plan.md: the three new MoEs that clear .67's Ollama 0.32.9 today.
# Stage A (qwen3.8:*) is deliberately absent — every qwen3.8 manifest requires
# 0.32.12 and the registry answers 412, so queueing it here would only produce
# an error loop. It gets added once .67 is upgraded.
MODELS=(
  "laguna-xs-2.1:q4_K_M"          # 33B MoE, 3B active — the only new model shaped
                                  # like the incumbent, so the only plausible
                                  # challenger on tok/s
  "north-mini-code-1.0:q4_K_M"    # Cohere 30B MoE, 3B active, trained for agentic
                                  # SWE, advertises a 488K window
  "gemma4:26b-a4b-it-q4_K_M"      # 4B active, vision + audio, a different vendor's
                                  # tool-calling template
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
