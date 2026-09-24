#!/usr/bin/env bash
# run-all.sh -- the rest of the 2026-09-21 round, unattended, in the only order
# that is valid. Launch it detached (setsid) and it will survive this session.
#
#   1. wait for the thinking-parity round to exit          (it is already running)
#   2. apply the deferred resume fix to GO_official_tb.sh  (unsafe while it runs)
#   3. summarise + compare the two arms
#   4. qwen3.6 at its VENDOR sampling setting, same subset  (plan.md §8.4b)
#   5-6. candidates: ranked, then one at a time via s10-one.sh (not here)
#   7. summarise again
#
# One box, one model at a time, .67 only. `.37` is out of scope for this project
# by the owner's instruction -- it was used once, for an API-semantics probe that
# needed a server the round was not using, and its probe tags were deleted.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
TBO="$HERE/terminalbench/official"
LOG="$HERE/results/run-all.log"
HOST="192.168.100.67"; BASE="http://$HOST:11434"
say () { printf '\n\033[1m[%s] %s\033[0m\n' "$(date +%H:%M)" "$*" | tee -a "$LOG"; }

say "1/7 waiting for the parity round to exit"
while pgrep -f 'GO_official_tb\.sh' >/dev/null 2>&1; do sleep 60; done
say "    parity round has exited"

say "2/7 applying the deferred resume fix"
python3 "$TBO/apply-resume-fix.py" 2>&1 | tee -a "$LOG"

say "3/7 summarising the parity arm"
( cd "$TBO" && ./summarise.py && ./compare-arms.py ) 2>&1 | tee -a "$LOG"

# ---------------------------------------------------------------------------
# 4. The control at its vendor setting. Qwen's card asks for temperature 0.6,
# top_p 0.95, top_k 20, min_p 0, presence_penalty 0 for thinking-mode precise
# coding; our tag has been running temperature 0 (greedy) for four rounds, and
# Claude Code sends no temperature of its own, so that baked value is what every
# trial used. New tag, old one kept: the pair is the measurement.
# ---------------------------------------------------------------------------
T06="qwen3.6:35b-a3b-q4_K_M-agentic-t06"
say "4/7 baking $T06 and running it on the frozen subset"
curl -s -m120 "$BASE/api/create" -d "{\"model\":\"$T06\",\"from\":\"qwen3.6:35b-a3b-q4_K_M-agentic\",\"parameters\":{\"num_ctx\":262144,\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20,\"min_p\":0,\"presence_penalty\":0,\"repeat_penalty\":1.0},\"stream\":false}" >/dev/null
curl -s -m60 "$BASE/api/show" -d "{\"model\":\"$T06\"}" | python3 -c "import sys,json;print('   baked:', (json.load(sys.stdin).get('parameters') or '?').replace(chr(10),' | '))" | tee -a "$LOG"
( cd "$TBO" && TB_THINKING=on TB_PHASE=1 ./GO_official_tb.sh "$T06" ) 2>&1 | tail -20 | tee -a "$LOG"
( cd "$TBO" && TB_THINKING=on TB_PHASE=2 ./GO_official_tb.sh "$T06" ) 2>&1 | tail -20 | tee -a "$LOG"

# ---------------------------------------------------------------------------
# 5-6. Candidates are NOT screened as a batch any more (changed 2026-09-24).
# They are web-vetted and ranked first, then run ONE AT A TIME with
# ./s10-one.sh <name>, best first, and the round document is updated and
# committed after each -- so a result lands in the docs before the next model
# is even pulled, and a candidate the evidence already rules out is never run.
# ---------------------------------------------------------------------------
say "5/7 candidates are driven one at a time by s10-one.sh (ranked order, ROUND_2026-09-24.md)"
say "6/7 (see 5/7)"

say "7/7 final summary"
( cd "$TBO" && ./summarise.py && ./compare-arms.py ) 2>&1 | tee -a "$LOG"
say "RUN-ALL-DONE"
