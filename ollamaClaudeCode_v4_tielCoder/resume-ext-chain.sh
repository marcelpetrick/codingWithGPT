#!/usr/bin/env bash
# Wait for a quiet shared box, then run the extended comparison and Laguna once.
# Launch detached under systemd-inhibit; the lock prevents duplicate chains.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
exec 9>/tmp/codingWithGPT-v4-ext-chain.lock
flock -n 9 || { echo "another extended chain holds the lock"; exit 0; }

BASE="http://192.168.100.67:11434"
INTERVAL="${CHAIN_WAIT_INTERVAL:-60}"
QUIET_POLLS="${CHAIN_QUIET_POLLS:-5}"
MAX_POLLS="${CHAIN_MAX_POLLS:-720}"
# Pin both Terminal-Bench stages to the version chosen before the extended
# comparison. The host CLI may update while this detached chain waits.
export TB_CC_VERSION="${TB_CC_VERSION:-2.1.283}"
say () { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*"; }
finish () {
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    say "CHAIN-DONE: extended comparison and Laguna complete"
    timeout 5 notify-send "v4 benchmark chain complete" "Extended comparison and Laguna finished." 2>/dev/null || true
  else
    say "CHAIN-STOPPED: exit $rc; inspect results/s11-ext.log and results/s10-laguna-xs21.log"
    timeout 5 notify-send "v4 benchmark chain stopped" "Check results/chain-0928.log (exit $rc)." 2>/dev/null || true
  fi
}
trap finish EXIT

say "waiting for the box to be empty for $QUIET_POLLS checks ($INTERVAL seconds apart); Claude Code $TB_CC_VERSION"
quiet=0
for (( poll=1; poll<=MAX_POLLS; poll++ )); do
  resident=$(curl --noproxy '*' -fsS -m 10 "$BASE/api/ps" | python3 -c '
import json, sys
print(" ".join(m["name"] for m in json.load(sys.stdin)["models"]))') || {
    say "server unreadable; stopping without starting a run"
    exit 3
  }
  if [ -z "$resident" ]; then
    quiet=$((quiet + 1))
    if [ "$quiet" -ge "$QUIET_POLLS" ]; then
      say "box has stayed empty; starting the extended comparison"
      ./s11-ext.sh
      say "extended comparison complete; starting Laguna"
      ./s10-one.sh laguna-xs21
      exit 0
    fi
  else
    [ "$quiet" -eq 0 ] || say "quiet window reset: $resident"
    quiet=0
    [ "$poll" -eq 1 ] && say "resident: $resident"
  fi
  sleep "$INTERVAL"
done
say "box stayed occupied for $MAX_POLLS checks; stopping without starting a run"
exit 3
