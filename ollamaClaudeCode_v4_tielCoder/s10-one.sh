#!/usr/bin/env bash
# s10-one.sh -- one candidate, end to end: screen, then Terminal-Bench if it
# was screened in. The ranked order and the reason for it live in
# ROUND_2026-09-24.md; this script only does one entry of that list, so the
# round document can be updated and committed between candidates.
#
#   ./s10-one.sh <name>        # <name> as in s9-candidates.sh CANDIDATES
#
# Waits for anything else on the box to finish first (one model at a time),
# and is idempotent through the two scripts it calls: a screened candidate is
# not screened again, a complete Terminal-Bench pass is not re-run.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
NAME="${1:?usage: s10-one.sh <candidate name>}"
HOST="192.168.100.67"
TSV="$HERE/results/candidates-2026-09-21.tsv"
TBO="$HERE/terminalbench/official"
LOG="$HERE/results/s10-$NAME.log"
say () { printf '\n\033[1m[%s] %s\033[0m\n' "$(date +%H:%M)" "$*" | tee -a "$LOG"; }

say "waiting for the box: no other Terminal-Bench pass, screen or run-all step"
# Anchored on the interpreter: an unanchored -f pattern also matched a wrapper
# whose command line merely MENTIONED the script, and deadlocked the chain
# for 70 min on 2026-09-24 (ROUND_2026-09-24.md).
BUSY='^bash \./(GO_official_tb|s9-candidates)\.sh'
while pgrep -f "$BUSY" >/dev/null 2>&1 \
   || { pgrep -f '^bash \./run-all\.sh' >/dev/null 2>&1 && ! grep -q '5/7' results/run-all.log; }; do
  sleep 60
done

say "screen: $NAME"
./s9-candidates.sh --host "$HOST" --only "$NAME" 2>&1 | tail -30 | tee -a "$LOG"

VERDICT=$(awk -F'\t' -v n="$NAME" '$2==n {v=$17; t=$5} END {print v"|"t}' "$TSV")
TAG="${VERDICT#*|}"; VERDICT="${VERDICT%%|*}"
say "verdict: ${VERDICT:-none}  tag: ${TAG:--}"

if [ "$VERDICT" = "SCREENED-IN" ]; then
  say "Terminal-Bench n=1 then n=2 for $TAG"
  ( cd "$TBO" && TB_THINKING=on TB_PHASE=1 ./GO_official_tb.sh "$TAG" ) 2>&1 | tail -20 | tee -a "$LOG"
  ( cd "$TBO" && TB_THINKING=on TB_PHASE=2 ./GO_official_tb.sh "$TAG" ) 2>&1 | tail -20 | tee -a "$LOG"
  ( cd "$TBO" && ./summarise.py ) 2>&1 | tee -a "$LOG"
fi
say "S10-DONE $NAME $VERDICT"
