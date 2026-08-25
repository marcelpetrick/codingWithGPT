#!/usr/bin/env bash
# head2head.sh — run the same battery against several models, one at a time.
#
# The one rule this script exists to enforce: **the server is idle before every
# measurement.** .67 holds ~40 GB and these models are 17-25 GB, so two of them
# cannot co-reside. A benchmark that starts while the previous model is still
# held by keep_alive measures eviction, reload and spill rather than the model
# -- and review2.md put the cost of a 12.5% spill at 5.3x, which is more than
# the difference between any two models here. So ./idle.sh runs between every
# stage and the run aborts if the server will not empty.
#
# Order matters too: throughput first on a cold server, then the capability
# gates. Throughput is the fragile measurement; gates are pass/fail and do not
# care about a few tok/s.
#
# Usage: ./head2head.sh [--host H] <model> [<model>...]
set -uo pipefail

HOST="192.168.100.67"; PORT="11434"
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    *) break ;;
  esac
done
[ $# -ge 1 ] || { echo "usage: head2head.sh [--host H] <model>..." >&2; exit 2; }

D="$(dirname "$(readlink -f "$0")")"
V1="$D/../ollamaClaudeCode_v1"
OUT="$D/results"; mkdir -p "$OUT"

gate() {
  "$D/idle.sh" --host "$HOST" --port "$PORT" || {
    echo "ABORT: server would not go idle; refusing to benchmark into a busy box" >&2
    exit 1; }
}

for M in "$@"; do
  printf '\n\033[1m########## %s ##########\033[0m\n' "$M"

  gate
  printf '\n\033[1m-- throughput --\033[0m\n'
  "$D/tokrate.sh" --host "$HOST" --port "$PORT" "$M"

  gate
  printf '\n\033[1m-- residency / KV --\033[0m\n'
  curl -s -m 900 -X POST "http://${HOST}:${PORT}/api/chat" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"120s\"}" >/dev/null
  curl -s "http://${HOST}:${PORT}/api/ps" | python3 -c '
import sys,json
for m in json.load(sys.stdin).get("models",[]):
    t=m.get("size",0); v=m.get("size_vram",0); c=m.get("context_length","?")
    print("   %-44s total %6.2f GB  vram %6.2f GB  %3.0f%% GPU  ctx=%s"%(
          m["name"],t/1e9,v/1e9,100*v/t if t else 0,c))'

  gate
  printf '\n\033[1m-- agentic gates T1-T5 --\033[0m\n'
  "$V1/agentic-test.sh" "$HOST" "$M" "$OUT/agentic" 2>&1 | sed -n '/T1/,/T6/p'

  gate
  printf '\n\033[1m-- needle retrieval --\033[0m\n'
  "$D/needle-v2.sh" --host "$HOST" --port "$PORT" --model "$M"
done

gate
echo
echo "done; server left idle"
