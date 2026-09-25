#!/usr/bin/env bash
# s12-rebaseline.sh -- the two method fixes review_20260925.md made mandatory
# before the KAT verdict can stand.
#
#  A. SAME-VERSION RE-BASELINE. The reference ledger sessions ran on Claude Code
#     2.1.274 (09-17), every candidate on 2.1.282 (09-25); the speed axis the pick
#     rests on was confounded with the client. Every contender now runs the ledger
#     fixture x5, back to back, on ONE Claude Code version, thinking on.
#  B. TOOL-GATE CONSISTENCY. T5 (nested schema) x8 for every screened model, and a
#     re-gate of Laguna XS 2.1 under the current setup (its cut rested on v3 data).
#
# Rule, fixed here before any re-baseline result exists (it replaces the unquantified
# "clearly faster" of 09-24):
#   quality passes   median held-out 18/18 AND no run below 16/18
#   clearly faster   median wall >= 25% lower AND the 5-run ranges do not overlap
#   G2 passes        >= 9/10, and T5 >= 7/8 when re-run (one miss in 8 is sampling noise)
#
# Arm label rb0925 -> rows go to results/cc-session-rb0925.tsv, transcripts to
# results/cc/<tag>-hard-thinkon-rb0925-rN.jsonl; nothing mixes into the screen data.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
HOST="192.168.100.67"; BASE="http://$HOST:11434"
LOG="$HERE/results/s12-rebaseline.log"
say () { printf '\n\033[1m[%s] %s\033[0m\n' "$(date +%H:%M)" "$*" | tee -a "$LOG"; }
MODELS=(
  kat-coder-v2.5:q5km-ctx256k-agentic
  tiel-coder:35b-q5-ctx256k-agentic
  gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic
  qwen3.6:35b-a3b-q4_K_M-agentic
  qwen3.6:35b-a3b-q4_K_M-agentic-t06
  byteshape-qwen3.6-35b:q4ks-ctx256k-agentic
)
GATED=(kat-coder-v2.5:q5km-ctx256k-agentic tiel-coder:35b-q5-ctx256k-agentic
       occamy-1.0:q5km-ctx256k-agentic ornith-1.5-35b:q5km-ctx256k-agentic
       byteshape-qwen3.6-35b:q4ks-ctx256k-agentic)

say "waiting for the box"
while pgrep -f '^bash \./(GO_official_tb|s9-candidates|s10-one|run-all|refine-ab|s11-ext)\.sh' >/dev/null 2>&1; do sleep 60; done
curl -s -m 10 "$BASE/api/version" >/dev/null || { say "server unreachable -- stopping"; exit 3; }
say "Claude Code $(claude --version 2>/dev/null | head -1) -- the one version for every session below"

done_runs () {  # <tag> -> number of rb0925 transcripts that ended in a result event
  local sl; sl="$(echo "$1" | tr '/:' '__')"
  grep -l '"type":"result"' results/cc/"$sl"-hard-thinkon-rb0925-r[0-9]*.jsonl 2>/dev/null | wc -l
}

say "A. same-version re-baseline, ledger x5 each"
for M in "${MODELS[@]}"; do
  if [ "$(done_runs "$M")" -ge 5 ]; then say "  $M: already 5 runs -- skipping"; continue; fi
  say "  $M"
  CC_ARM=rb0925 ./cc-session.sh --host "$HOST" --fixture hard --runs 5 --thinking on "$M" 2>&1 \
    | grep -E 'PASS|FAIL' | tee -a "$LOG"
  curl -s "$BASE/api/generate" -d "{\"model\":\"$M\",\"keep_alive\":0}" >/dev/null
done

say "B1. T5 nested-schema gate x8"
python3 ./gate-rerun.py --host "$BASE" --n 8 --gate T5 "${GATED[@]}" 2>&1 | tail -12 | tee -a "$LOG"

say "B2. Laguna XS 2.1 re-gate, current setup, Poolside's sampler"
LAG=laguna-xs-2.1:q4km-ctx256k-agentic
curl -s -m 600 "$BASE/api/create" -d "{\"model\":\"$LAG\",\"from\":\"laguna-xs-2.1:q4_K_M\",\"parameters\":{\"num_ctx\":262144,\"presence_penalty\":0,\"temperature\":1.0,\"top_k\":20,\"top_p\":1.0},\"stream\":false}" | tail -c 200 | tee -a "$LOG"
./agentic-test.sh "$HOST" "$LAG" 2>&1 | tail -12 | tee -a "$LOG"
curl -s "$BASE/api/generate" -d "{\"model\":\"$LAG\",\"keep_alive\":0}" >/dev/null

say "C. comparison against the rule"
python3 - <<'PY' | tee -a "$LOG"
import csv, statistics
from collections import defaultdict
rows = defaultdict(list)
with open("results/cc-session-rb0925.tsv") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        if r["fixture"] == "hard" and r["thinking"] == "on":
            rows[r["model"]].append(r)
print(f"{'model':<46} {'n':>2} {'median s':>9} {'range':>11} {'held-out per run':<22}")
for m, rs in rows.items():
    rs = rs[-5:]
    w = [float(r["wall_s"]) for r in rs if r["wall_s"].replace('.', '', 1).isdigit()]
    h = [int(r["hidden"].split("/")[0]) for r in rs if "/" in r["hidden"]]
    q = "PASS" if h and statistics.median(h) == 18 and min(h) >= 16 else "fail"
    print(f"{m:<46} {len(rs):>2} {statistics.median(w) if w else 0:>9.0f} "
          f"{(f'{min(w):.0f}-{max(w):.0f}' if w else '-'):>11} {','.join(map(str, h)):<22} quality {q}")
PY
say "S12-REBASELINE-DONE"
