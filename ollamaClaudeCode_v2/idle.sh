#!/usr/bin/env bash
# idle.sh — assert the server has nothing resident, and wait until it does.
#
# Why this is a separate, mandatory step rather than a flag on the benchmarks:
# .67 is a shared box with ~40 GB. Two 20-25 GB models cannot both be resident,
# so if a benchmark starts while the previous model is still held by keep_alive,
# one of three things happens and all of them silently corrupt the result:
#
#   1. the incoming model is evicted-and-reloaded mid-run, and load_duration
#      leaks into the timings;
#   2. the incoming model is partially offloaded to system RAM, which
#      review2.md measured at 5.3x slower for a 12.5% spill -- it would look
#      like a bad model rather than a busy server;
#   3. the *other* model gets evicted, which is rude on a shared machine.
#
# Ollama frees a model when it is asked with keep_alive 0. That is a request,
# not a command, so this polls /api/ps until it is actually empty instead of
# sleeping a guessed interval.
#
# Usage: ./idle.sh [--host H] [--port P] [--timeout S]
set -uo pipefail

HOST="192.168.100.67"; PORT="11434"; TMO=180
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --timeout) TMO="$2"; shift 2 ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done
API="http://${HOST}:${PORT}"

resident() {
  curl -s -m 10 "$API/api/ps" | python3 -c '
import sys,json
try: ms=json.load(sys.stdin).get("models",[])
except Exception: raise SystemExit
for m in ms: print(m["name"])' 2>/dev/null
}

R=$(resident)
if [ -z "$R" ]; then
  echo "idle: nothing resident on $HOST"
  exit 0
fi

echo "idle: unloading ->"
printf '  %s\n' $R
for M in $R; do
  # keep_alive 0 asks Ollama to drop it as soon as the request returns.
  curl -s -m 30 -X POST "$API/api/generate" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$M\",\"keep_alive\":0}" >/dev/null
done

W=0
while [ $W -lt "$TMO" ]; do
  R=$(resident)
  [ -z "$R" ] && { echo "idle: server is now empty (${W}s)"; exit 0; }
  sleep 5; W=$((W+5))
done

echo "idle: TIMEOUT after ${TMO}s, still resident:" >&2
printf '  %s\n' $R >&2
exit 1
