#!/usr/bin/env bash
# s8-dualuse.sh — the base-vs-abliterated discriminator (dualuse-probe.py).
# Waits for the extra gates (S7) so the box is never shared. API-only, no code
# is executed. See BENCHMARK_HARNESS.md 6a for the task list and scope.
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"; cd "$D"
while ! grep -q "S7-DONE" results/s7.log 2>/dev/null; do sleep 20; done
echo "S7 finished; starting the dual-use discriminator"
for M in "tiel-coder:35b-q5-ctx256k-agentic" \
         "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest" \
         "cyber-tiel:35b-q5-ctx256k-agentic"; do
  ./idle.sh --mine "$M" || true
  python3 ./dualuse-probe.py "$M" || true
done
./idle.sh || true
echo S8-DONE
