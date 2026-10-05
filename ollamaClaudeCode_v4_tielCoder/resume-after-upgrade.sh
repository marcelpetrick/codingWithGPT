#!/usr/bin/env bash
# After the owner upgraded .67 to Ollama 0.35.1 during KAT's extended pass
# (2026-10-05 ~16:45), the owner chose: let KAT finish, label it mixed, no
# re-run. This replaces resume-repair-chain.sh, whose 0.33.3 repair of
# qwen3.6's VOID write-compressor can no longer be done under the same runtime.
# Queues on the extended chain's lock, then:
#   1. INFORMATION-only comparison (EXT_INFO=1: a task VOID for either model is
#      dropped for both; MIXED_RUNTIME runs never print a VERDICT)
#   2. dashboard
#   3. the Laguna XS 2.1 screen, on 0.35.1 (recorded in the log)
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
TBO="$HERE/terminalbench/official"
LOG="results/s11-ext.log"
export TB_CC_VERSION="${TB_CC_VERSION:-2.1.283}"
PAIR=()
while IFS= read -r line; do PAIR+=("$line"); done < <(grep -vE '^\s*#|^\s*$' results/ext-models.txt)
say () { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*"; }
finish () {
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    say "AFTER-UPGRADE-DONE: information comparison and Laguna complete"
    timeout 5 notify-send "v4 chain complete" "Comparison in results/s11-ext.log, Laguna in results/s10-laguna-xs21.log." 2>/dev/null || true
  else
    say "AFTER-UPGRADE-STOPPED: exit $rc"
    timeout 5 notify-send "v4 chain stopped" "Check the after-upgrade log in results/ (exit $rc)." 2>/dev/null || true
  fi
}
trap finish EXIT
trap 'exit 143' TERM INT HUP   # a signal is a stop, never a success

exec 9>/tmp/codingWithGPT-v4-ext-chain.lock
say "waiting for the extended chain to release its lock"
flock 9
ver="$(curl --noproxy '*' -fsS -m 10 http://192.168.100.67:11434/api/version)" || { say "server unreadable; stopping"; exit 3; }
say "lock acquired; pair: ${PAIR[*]}; server $ver; Claude Code $TB_CC_VERSION"

# 1. information-only comparison; it must find KAT's pass complete
say "3/3 comparison (INFORMATION ONLY: mixed runtime, VOID tasks dropped for both)" | tee -a "$LOG"
( cd "$TBO" && python3 summarise.py | grep -E "IN FLIGHT|trials\)|  kat|  qwen" ; \
  EXT_ONLY=1 EXT_INFO=1 python3 ext-compare.py "${PAIR[@]}" ) 2>&1 | tee -a "$LOG"
say "S11-EXT-DONE (information only)" | tee -a "$LOG"
python3 ./make-dashboard.py >/dev/null 2>&1

# 2. Laguna, on the upgraded runtime
say "starting Laguna on $ver"
./s10-one.sh laguna-xs21
python3 ./make-dashboard.py >/dev/null 2>&1
