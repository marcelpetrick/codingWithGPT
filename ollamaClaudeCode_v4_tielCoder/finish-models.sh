#!/usr/bin/env bash
# finish-models.sh -- owner's instruction 2026-10-07: no re-runs and no re-baseline,
# finish the models first so the round has a pick. One sequential chain:
#   1. KAT-Coder extended pass, n=2, fresh and wholly on Ollama 0.35.1. qwen3.6's
#      complete 0.33.3 pass (093350) is reused, not re-run: GO_official_tb.sh skips it.
#   2. INFORMATION-only comparison (EXT_INFO=1): the pair now spans two runtimes,
#      so it prints no VERDICT; tasks VOID for either model are dropped for both.
#   3. Laguna XS 2.1 screen (+ Terminal-Bench if screened in), on 0.35.1.
# The dashboard is regenerated after every stage. Idempotent: a complete pass or
# screen is skipped on a re-run. Launch detached under systemd-inhibit.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
TBO="$HERE/terminalbench/official"
BASE="http://192.168.100.67:11434"
LOG="results/s11-ext.log"
KAT="kat-coder-v2.5:q5km-ctx256k-agentic"
export TB_CC_VERSION="${TB_CC_VERSION:-2.1.283}"
PAIR=()
while IFS= read -r line; do PAIR+=("$line"); done < <(grep -vE '^\s*#|^\s*$' results/ext-models.txt)
say () { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*"; }
finish () {
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    say "FINISH-MODELS-DONE: KAT extended pass, information comparison and Laguna complete"
    timeout 5 notify-send "v4 finish-models complete" "Comparison in results/s11-ext.log, Laguna in results/s10-laguna-xs21.log." 2>/dev/null || true
  else
    say "FINISH-MODELS-STOPPED: exit $rc"
    timeout 5 notify-send "v4 finish-models stopped" "Check results/finish-models-*.log (exit $rc)." 2>/dev/null || true
  fi
}
trap finish EXIT
trap 'exit 143' TERM INT HUP   # a signal is a stop, never a success

exec 9>/tmp/codingWithGPT-v4-ext-chain.lock
flock -n 9 || { say "another v4 chain holds the lock"; exit 3; }

ver="$(curl --noproxy '*' -fsS -m 10 "$BASE/api/version")" || { say "server unreadable; stopping"; exit 3; }
resident=$(curl --noproxy '*' -fsS -m 10 "$BASE/api/ps" | python3 -c '
import json, sys
print(" ".join(m["name"] for m in json.load(sys.stdin)["models"]))') || { say "cannot read /api/ps; stopping"; exit 3; }
[ -z "$resident" ] || { say "box occupied by $resident; stopping without unloading it"; exit 3; }
say "server $ver, box empty; pair: ${PAIR[*]}; Claude Code $TB_CC_VERSION"

# 1. KAT extended pass (T5 already 8/8 in s12; the oracle subset already exists)
say "1/3 extended pass: $KAT, n=2, on $ver" | tee -a "$LOG"
( cd "$TBO" && TB_SUBSET=subset-ext-scored.txt TB_ARM_SUFFIX=-ext TB_THINKING=on TB_PHASE=2 \
    ./GO_official_tb.sh "$KAT" ) 2>&1 | tail -12 | tee -a "$LOG"
python3 ./make-dashboard.py >/dev/null 2>&1

# 2. information-only comparison; it must find both passes complete
say "2/3 comparison (INFORMATION ONLY: qwen3.6 on 0.33.3, KAT on $ver)" | tee -a "$LOG"
( cd "$TBO" && python3 summarise.py | grep -E "IN FLIGHT|trials\)|  kat|  qwen" ; \
  EXT_ONLY=1 EXT_INFO=1 python3 ext-compare.py "${PAIR[@]}" ) 2>&1 | tee -a "$LOG"
python3 ./make-dashboard.py >/dev/null 2>&1

# 3. Laguna
say "3/3 Laguna XS 2.1 on $ver"
./s10-one.sh laguna-xs21
python3 ./make-dashboard.py >/dev/null 2>&1
