#!/usr/bin/env bash
# run-all.sh -- the rest of the 2026-09-21 round, unattended, in the only order
# that is valid. Launch it detached (setsid) and it will survive this session.
#
#   1. wait for the thinking-parity round to exit          (it is already running)
#   2. apply the deferred resume fix to GO_official_tb.sh  (unsafe while it runs)
#   3. summarise + compare the two arms
#   4. qwen3.6 at its VENDOR sampling setting, same subset  (plan.md §8.4b)
#   5. screen the candidates                                (plan.md §8.3)
#   6. Terminal-Bench for whatever the screen let through
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

say "5/7 screening the candidates (pull -> fit -> gates -> turn economy)"
./s9-candidates.sh --host "$HOST" 2>&1 | tail -40 | tee -a "$LOG"

say "6/7 Terminal-Bench for whatever was screened in"
SURVIVORS=$(python3 - <<'PY'
import csv, pathlib
p = pathlib.Path("results/candidates-2026-09-21.tsv")
if p.exists():
    with p.open() as f:
        print(" ".join(r["baked_tag"] for r in csv.DictReader(f, delimiter="\t")
                       if r.get("verdict") == "SCREENED-IN"))
PY
)
if [ -n "${SURVIVORS// }" ]; then
  say "    survivors: $SURVIVORS"
  ( cd "$TBO" && TB_THINKING=on TB_PHASE=1 ./GO_official_tb.sh $SURVIVORS ) 2>&1 | tail -20 | tee -a "$LOG"
  ( cd "$TBO" && TB_THINKING=on TB_PHASE=2 ./GO_official_tb.sh $SURVIVORS ) 2>&1 | tail -20 | tee -a "$LOG"
else
  say "    nothing was screened in -- no Terminal-Bench passes to run"
fi

say "7/7 final summary"
( cd "$TBO" && ./summarise.py && ./compare-arms.py ) 2>&1 | tee -a "$LOG"
say "RUN-ALL-DONE"
