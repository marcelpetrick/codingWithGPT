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

# Stage A of plan.md: the Qwen3.8 rungs. Unblocked 2026-08-27 — .67 moved from
# Ollama 0.32.9 to 0.32.15, so the registry's HTTP 412 gate ("requires":"0.32.12")
# is cleared and these manifests resolve.
#
# The Stage B list this file carried on 2026-08-25 (laguna-xs-2.1,
# north-mini-code-1.0, gemma4:26b-a4b-it) is gone from MODELS but not from the
# record: its pulls are in pull-queue.log above this run's entries.
#
# A1 and A2 share one weight blob (sha256:f5f1dd8920d4, 15.656 GiB) and differ
# only in the params layer — A2 adds "draft_num_predict":4. So A2 costs one
# small layer, not a second 16 GB download, and re-testing v2's MTP finding is
# effectively free.
MODELS=(
  "qwen3.8:27b-q4_K_M"            # A1 — dense 27B, 256K, vision. The model the
                                  # project was commissioned to benchmark.
  "qwen3.8:27b-mtp-q4_K_M"        # A2 — same weights + MTP head. v2 measured MTP
                                  # as a net loss (129.2 -> 100.6 tok/s at the
                                  # shipped draft_num_predict 4); re-test is free.
  # A3 "qwen3.8:27b-q8_0" is deliberately NOT queued. plan.md §2 gates it on
  # "runs only if A1 earns it", and pulling 27 GB onto a shared, df-less box
  # would also have a large disk write in flight underneath A1's own benchmark.
  # It gets pulled by hand if and only if A1's numbers justify a quality rung.
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
