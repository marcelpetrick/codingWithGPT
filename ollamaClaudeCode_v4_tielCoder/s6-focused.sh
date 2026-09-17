#!/usr/bin/env bash
# s6-focused.sh — the remaining work, narrowed.
#
# Cut from further benchmarking (their data stays in the report, labelled):
#   nemotron-cascade-2  rejected twice on the same defect. v3: 7/10 gates, 84 turns,
#                       256 s. v4: 8/10 gates, 0/3 sessions, hidden 0/18, 3/18, 3/18,
#                       419 s median, 41 Bash calls and nine blind Writes in one run.
#   qwen3.8:27b dense   30.3 tok/s, 787 s median on the hard fixture -- 4x the field.
#                       v3 measured and rejected it; v4 reproduced that.
# Re-running either would spend an hour to re-confirm a settled answer.
#
# What is left, and only this:
#   1. CyberTiel's two missing probes (cache, overflow)
#   2. sandboxed sessions -- Tiel (host parity) and CyberTiel, the two models the
#      round is actually about, plus a thinking-off arm for CyberTiel because the
#      thinking-off result on Tiel was the largest operational finding of S3
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"; cd "$D"
T2="tiel-coder:35b-q5-ctx256k-agentic"
CT="cyber-tiel:35b-q5-ctx256k-agentic"

echo "### 1. CyberTiel: the two probes the S5 run did not include"
./idle.sh --mine "$CT" || true
python3 ./cache-probe.py "$CT" || true
./idle.sh --mine "$CT" || true
python3 ./overflow-probe.py "$CT" || true
./idle.sh --mine "$CT" || true

echo "### 2. Sandboxed sessions — Tiel (parity) and CyberTiel"
for R in 1 2 3; do
  for M in "$T2" "$CT"; do
    ./idle.sh --mine "$M" || true
    ./cc-session-sandboxed.sh --fixture easy --runs 1 --first-run "$R" --timeout 900 "$M" || true
    ./cc-session-sandboxed.sh --fixture hard --runs 1 --first-run "$R" --timeout 1200 "$M" || true
  done
  # CyberTiel with thinking off: Tiel's think-off arm halved its hard session, and
  # CyberTiel carries the same Sharp template, so the switch should transfer.
  ./idle.sh --mine "$CT" || true
  ./cc-session-sandboxed.sh --fixture hard --runs 1 --first-run "$R" --timeout 1200 --thinking off "$CT" || true
done
./idle.sh --mine "$CT" --mine "$T2" || true
echo S6-DONE
