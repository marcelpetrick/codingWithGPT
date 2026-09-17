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
# Copied from ../ollamaClaudeCode_v2/idle.sh. The only change is the OURS
# ownership regex below, extended with v3's tags. v2's copy is left untouched
# because it is the harness that produced v2's published verdict.
#
# Usage: ./idle.sh [--host H] [--port P] [--timeout S] [--wait S] [--force]
#
# Unloads only models this project owns. A foreign model is waited out, never
# evicted -- see the shared-server guard below.
set -uo pipefail

HOST="192.168.100.67"; PORT="11434"; TMO=180
WAIT=600   # how long to wait for a FOREIGN model to free itself before giving up
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --timeout) TMO="$2"; shift 2 ;;
    --wait)    WAIT="$2"; shift 2 ;;
    --force)   FORCE=1; shift ;;
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

# --- the shared-server guard -------------------------------------------------
# .67 belongs to a colleague (see ~/repos/ollamaFarm/AGENTS.md). Unloading is
# safe for models THIS harness put there and rude for anything else: on
# 2026-08-13 a benchmark was started while a colleague's claude-ol2 session held
# 32.54 GB with a 2h keep_alive, and an unguarded unload would have evicted them
# mid-session with no warning.
#
# So: only ever unload tags this project benchmarks or creates. Anything else
# means WAIT (default) -- polling read-only until it goes away on its own -- or
# bail out. --force is the explicit override for "I know that model is mine".
#
# KNOWN LIMITATION, stated rather than hidden: ownership is guessed from the tag
# name, and it cannot be done properly. The qwen3.6 variants this project also
# benchmarks (-mtp-q4_K_M-agentic, 27b-q8_0-agentic) are indistinguishable by
# name from qwen3.6:35b-a3b-q4_K_M-agentic, which is what a colleague's
# claude-ol2 session loads. Erring toward "foreign" means re-benchmarking those
# two needs either a free server or an explicit --force. That is the right way
# round: a needless wait costs minutes, evicting someone's session costs a
# 70-second reload plus their goodwill.
#
# Do NOT run this script while one of your own benchmarks is in flight -- it will
# unload the model being measured. That happened once on 2026-08-13, to this
# author, while "just checking the new guard works".
# v3 additions: the stage B tags this project pulled onto .67 on 2026-08-25
# (laguna-xs-2.1, north-mini-code-1.0, gemma4) and the stage A tags it will pull
# once .67 clears Ollama 0.32.12 (qwen3.8). Everything this project put there is
# ours to unload; everything else is still waited out rather than evicted.
#
# qwen3.6:* stays OUT of this list on purpose, even though v3 benchmarks the
# incumbent as its control. A colleague's claude-ol2 session loads
# qwen3.6:35b-a3b-q4_K_M-agentic, and the tag name cannot distinguish their
# session from our control run. Benchmarking the control therefore needs a free
# server or an explicit --force -- a needless wait costs minutes, evicting
# someone mid-session costs them a 70 s reload.
# v3 stage D additions (2026-08-27): nemotron-cascade-2 and granite4.2, pulled
# by this project on 2026-08-27. gemma4: already covered the 31b tag.
OURS='^(ornith:|muse-glimmer:|nemotron-3\.5-lightning:|nemotron-cascade-2:|granite4\.2:|kvprobe-|tune-|qwen3\.8:|laguna-xs-|north-mini-code-|gemma4:)'
foreign() { printf '%s\n' $R | grep -Ev "$OURS" || true; }

F=$(foreign)
if [ -n "$F" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "idle: someone else's model is resident -- waiting, NOT unloading:" >&2
  printf '  %s\n' $F >&2
  W=0
  while [ $W -lt "$WAIT" ]; do
    sleep 30; W=$((W+30))
    R=$(resident)
    [ -z "$R" ] && { echo "idle: server freed itself after ${W}s"; exit 0; }
    [ -z "$(foreign)" ] && break   # only our own models left; fall through to unload
  done
  if [ -n "$(foreign)" ]; then
    echo "idle: STILL busy after ${WAIT}s. Refusing to evict a foreign model." >&2
    echo "  re-run when it is free, or FORCE=1 if that model is yours." >&2
    exit 2
  fi
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
