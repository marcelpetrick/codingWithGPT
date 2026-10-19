#!/usr/bin/env bash
# s14-field.sh -- the whole field on the current state (Ollama 0.35.1, Claude Code 2.1.303), 2026-10-19.
# Extends s13 (qwen3.6, KAT) to every model still on the box, same arm, same rule; adds the T5 gate x8.
#
# Claude Code moved 2.1.282 -> 2.1.303 since the 09-25 re-baseline and the server
# moved 0.33.3 -> 0.35.1, so the reference numbers are stale for any new candidate.
# Re-measure the default and its tie on ONE client version, before any candidate runs.
#
# Rule (unchanged from s12, fixed before these runs):
#   quality passes   median held-out 18/18 AND no run below 16/18
#   clearly faster   median wall >= 25% lower AND the 5-run ranges do not overlap
#
# Arm label rb1019 -> results/cc-session-rb1019.tsv; nothing mixes into earlier arms.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
HOST="192.168.100.67"; BASE="http://$HOST:11434"
LOG="$HERE/results/s14-field.log"
say () { printf '\n\033[1m[%s] %s\033[0m\n' "$(date +%H:%M)" "$*" | tee -a "$LOG"; }
MODELS=(
  tiel-coder:35b-q5-ctx256k-agentic
  laguna-xs-2.1:q4km-ctx256k-agentic
  gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic
  byteshape-qwen3.6-35b:q4ks-ctx256k-agentic
  occamy-1.0:q5km-ctx256k-agentic
  ornith-1.5-35b:q5km-ctx256k-agentic
)
GATED=(qwen3.6:35b-a3b-q4_K_M-agentic kat-coder-v2.5:q5km-ctx256k-agentic "${MODELS[@]}")

say "waiting for the box"
while pgrep -f '^bash \./(GO_official_tb|s9-candidates|s10-one|run-all|refine-ab|s11-ext|s12-rebaseline|s13-rebaseline|finish-models)\.sh' >/dev/null 2>&1; do sleep 60; done
curl -s -m 10 "$BASE/api/version" >/dev/null || { say "server unreachable -- stopping"; exit 3; }
say "Claude Code $(claude --version 2>/dev/null | head -1) -- the one version for every session below"

done_runs () {  # <tag> -> number of rb1019 transcripts that ended in a result event
  local sl; sl="$(echo "$1" | tr '/:' '__')"
  grep -l '"type":"result"' results/cc/"$sl"-hard-thinkon-rb1019-r[0-9]*.jsonl 2>/dev/null | wc -l
}

say "A. same-version re-baseline, ledger x5 each"
for M in "${MODELS[@]}"; do
  if [ "$(done_runs "$M")" -ge 5 ]; then say "  $M: already 5 runs -- skipping"; continue; fi
  say "  $M"
  CC_ARM=rb1019 ./cc-session.sh --host "$HOST" --fixture hard --runs 5 --thinking on "$M" 2>&1 \
    | grep -E 'PASS|FAIL' | tee -a "$LOG"
  curl -s "$BASE/api/generate" -d "{\"model\":\"$M\",\"keep_alive\":0}" >/dev/null
done

say "B. T5 nested-schema gate x8, every model"
python3 ./gate-rerun.py --host "$BASE" --n 8 --gate T5 "${GATED[@]}" 2>&1 | tail -14 | tee -a "$LOG"

say "C. comparison against the rule"
python3 - <<'PY' | tee -a "$LOG"
import csv, statistics
from collections import defaultdict
rows = defaultdict(list)
with open("results/cc-session-rb1019.tsv") as f:
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
say "S14-FIELD-DONE"
