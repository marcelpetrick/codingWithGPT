#!/usr/bin/env bash
# s7-extra-gates.sh — the four agentic gates T1-T7 never covered (gate-extra.py),
# across the focused field. Waits for S6 so the two stages never share the box.
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"; cd "$D"
while ! grep -q "S6-DONE" results/s6.log 2>/dev/null; do sleep 20; done
echo "S6 finished; starting the extra gates"
./idle.sh || true
# The focused set: the two subjects, plus the comparators that are still in play.
# cascade-2 and qwen3.8 are cut (plan.md 4c) and are not re-run here either.
for M in "tiel-coder:35b-q5-ctx256k-agentic" \
         "cyber-tiel:35b-q5-ctx256k-agentic" \
         "ornith:35b-ctx256k-agentic" \
         "north-mini-code-1.0:q4_K_M-ctx256k-agentic" \
         "qwen3.6:35b-a3b-q4_K_M-agentic" \
         "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic" \
         "nemotron-3.5-lightning:30b-ctx256k-agentic"; do
  ./idle.sh --mine "$M" || true
  python3 ./gate-extra.py --n 3 "$M" || true
done
./idle.sh || true
echo S7-DONE
