#!/usr/bin/env bash
# GO_terminalbench.sh — the single "go" command.
#
# Tomorrow: ./GO_terminalbench.sh          (uses the default model set below)
#      or:  ./GO_terminalbench.sh <model> [<model>...]   to override.
#
# Runs the whole Terminal-Bench-style C/CMake suite (terminalbench/tasks) against
# each model, one model at a time, thinking OFF (v4: 2.3x, no correctness loss),
# then regenerates the report. Everything is validated and committed the night
# before; this just executes. It leaves the shared box idle at the end.
set -uo pipefail
D="$(dirname "$(readlink -f "$0")")"; cd "$D"

# Default field: the subject models plus the comparators still in play. cascade-2
# and qwen3.8 stay cut (plan.md 4c). Edit this line to change the set.
# The standing field, fixed 2026-09-18 (BENCHMARK_HARNESS.md §9a). cyber-tiel,
# ornith, the shipped Tiel tag, nemotron-3.5-lightning, cascade-2 and qwen3.8 are
# retired from testing -- their numbers stay in the tables, they are not re-run.
DEFAULT=(
  "qwen3.6:35b-a3b-q4_K_M-agentic"
  "north-mini-code-1.0:q4_K_M-ctx256k-agentic"
  "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic"
  "tiel-coder:35b-q5-ctx256k-agentic"
)
MODELS=("$@"); [ ${#MODELS[@]} -eq 0 ] && MODELS=("${DEFAULT[@]}")

echo "=== preflight ==="
curl -s -m10 http://192.168.100.67:11434/api/version >/dev/null || { echo "server not answering — check USB ethernet"; exit 2; }
docker image inspect v4-tb-sandbox:latest >/dev/null 2>&1 || \
  docker build -q -t v4-tb-sandbox:latest -f terminalbench/Dockerfile.tb terminalbench/ >/dev/null
echo "=== fixture self-check (seed fails / solution passes) ==="
terminalbench/tb-validate.sh || { echo "FIXTURES INVALID — aborting"; exit 3; }

echo "=== running the suite, thinking OFF, n=2 ==="
terminalbench/tb-run.sh --runs 2 --thinking off "${MODELS[@]}"

# a thinking-ON arm for Tiel only, to keep the v4 comparison alive
echo "=== thinking-ON arm (Tiel) ==="
terminalbench/tb-run.sh --runs 1 --thinking on \
  "tiel-coder:35b-q5-ctx256k-agentic" || true

echo "=== regenerate report ==="
python3 make-report.py --pdf || true
echo "GO-TERMINALBENCH-DONE"
