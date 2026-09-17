#!/usr/bin/env bash
# head2head.sh — run the same battery against several models, one at a time.
#
# The one rule this script exists to enforce: **the server is idle before every
# measurement.** .67 holds ~35.5 GB and these models are 17-34 GB, so two of
# them cannot co-reside. A benchmark that starts while the previous model is
# still held by keep_alive measures eviction, reload and spill rather than the
# model -- and v1 put the cost of a 12.5% spill at 5.3x, more than the gap
# between any two models here. So ./idle.sh runs between every stage and the
# run aborts if the server will not empty.
#
# Order matters too: throughput first on a cold server, then the capability
# gates. Throughput is the fragile measurement; gates are pass/fail.
#
# v4 changes against v3's copy:
#   * idle.sh gets --mine "$M": the model a stage just loaded is ours to unload,
#     which lets the qwen3.6 control run without --force or a 600 s wait
#   * gates use v4's agentic-test.sh (unloads only the tested model)
#   * GATE_RUNS repeats the T1-T7 battery; each run keeps its own TSV
#   * needle depths per model via NEEDLE_DEPTHS (words); empty skips the stage
#   * vision stage for models whose /api/show lists "vision"
#
# Usage: GATE_RUNS=1 NEEDLE_DEPTHS="80000" ./head2head.sh [--host H] <model>...
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
GATE_RUNS="${GATE_RUNS:-1}"
NEEDLE_DEPTHS="${NEEDLE_DEPTHS-2700 10700 40000 80000}"

D="$(dirname "$(readlink -f "$0")")"
OUT="$D/results"; mkdir -p "$OUT"
API="http://${HOST}:${PORT}"

for M in "$@"; do
  gate() {
    "$D/idle.sh" --host "$HOST" --port "$PORT" --mine "$M" || {
      echo "ABORT: server would not go idle; refusing to benchmark into a busy box" >&2
      exit 1; }
  }
  printf '\n\033[1m########## %s ##########\033[0m\n' "$M"
  curl -s "$API/api/version"; echo

  gate
  printf '\n\033[1m-- throughput --\033[0m\n'
  "$D/tokrate.sh" --host "$HOST" --port "$PORT" "$M"

  gate
  printf '\n\033[1m-- residency / KV --\033[0m\n'
  curl -s -m 900 -X POST "$API/api/chat" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"120s\"}" >/dev/null
  curl -s "$API/api/ps" | python3 -c '
import sys,json
for m in json.load(sys.stdin).get("models",[]):
    t=m.get("size",0); v=m.get("size_vram",0); c=m.get("context_length","?")
    print("   %-50s total %6.2f GB  vram %6.2f GB  %3.0f%% GPU  ctx=%s"%(
          m["name"],t/1e9,v/1e9,100*v/t if t else 0,c))' | tee -a "$OUT/residency.log"

  for R in $(seq 1 "$GATE_RUNS"); do
    gate
    printf '\n\033[1m-- agentic gates T1-T7, run %s/%s --\033[0m\n' "$R" "$GATE_RUNS"
    GDIR="$OUT/agentic"; [ "$GATE_RUNS" -gt 1 ] && GDIR="$OUT/agentic/run$R"
    "$D/agentic-test.sh" "$HOST" "$M" "$GDIR"
  done

  if [ -n "$NEEDLE_DEPTHS" ]; then
    gate
    printf '\n\033[1m-- needle retrieval --\033[0m\n'
    "$D/needle-v2.sh" --host "$HOST" --port "$PORT" --model "$M" --num-predict 2048 --depths "$NEEDLE_DEPTHS"
  fi

  if curl -s "$API/api/show" -d "{\"model\":\"$M\"}" | python3 -c 'import sys,json;sys.exit(0 if "vision" in json.load(sys.stdin).get("capabilities",[]) else 1)'; then
    gate
    printf '\n\033[1m-- vision, at the baked window --\033[0m\n'
    python3 "$D/vision-bench.py" --host "$API" "$M"
  fi
  gate
done

echo
echo "done; server left idle"
