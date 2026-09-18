#!/usr/bin/env bash
# GO_official_tb.sh -- the single "go" for the OFFICIAL Terminal-Bench round.
#
#   ./GO_official_tb.sh            # the planned 4-hour window (see OFFICIAL_TB_PLAN.md)
#   ./GO_official_tb.sh <tag> ...  # override the model field
#
# Unlike the sibling terminalbench/ suite (our own C tasks), this drives the
# UPSTREAM terminal-bench harness on the upstream terminal-bench-core dataset,
# so the numbers are comparable to the public leaderboard. The only local piece
# is the agent adapter (ollama_claude_code_agent.py), which points Claude Code at
# .67 -- the stock claude-code agent has no ANTHROPIC_BASE_URL and would silently
# hit api.anthropic.com and report 0%.
#
# Plan (chosen 2026-09-18): "Tiel deep, n=2".
# Thinking is ON by default and that is deliberate: <|think_off|> is a
# Sharp-template token, so asking for "off" in a mixed field silences Tiel and
# CyberTiel while every comparator keeps reasoning. That asymmetry invalidated the
# 2026-09-18 round's model comparison. TB_THINKING=off is only legitimate when the
# field is Tiel/CyberTiel alone; the adapter now refuses it otherwise.
#   phase 1: all 4 models x the frozen 10-task subset x n=1   (~1.3 h)
#   phase 2: the same 4 x the subset x n=2                    (~2.7 h)
# Every model runs the IDENTICAL subset (subset.txt). One model resident at a
# time; the box is shared, so it yields, never evicts.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"

HOST="${OLLAMA_HOST_URL:-http://192.168.100.67:11434}"
VENV="${TB_VENV:-$HERE/tb-venv}"                 # created by setup.sh
DATASET="terminal-bench-core==0.1.1"
AGENT="terminalbench.official.ollama_claude_code_agent:OllamaClaudeCodeAgent"
OUT="$HERE/runs"
CONCURRENCY="${TB_CONCURRENCY:-1}"               # one model on the box -> serial
export PYTHONPATH="$HERE/../..:${PYTHONPATH:-}"  # so the import path resolves

TB="$VENV/bin/tb"
[ -x "$TB" ] || { echo "harness not installed -- run ./setup.sh first"; exit 4; }

# THE STANDING FIELD, fixed 2026-09-18 (BENCHMARK_HARNESS.md §9a). A new contender
# is measured against these four and nothing else; each holds a different axis, and
# a candidate takes a slot only by beating that slot's holder on its own axis:
#   qwen3.6     the default          (capability + reproducibility)
#   north-mini  the speed ceiling    (owes an n=2 pass)
#   gemma4      the footprint floor  (and the vision slot)
#   tiel-coder  context safety       (the only one that refuses an over-long prompt)
# Retired, do NOT re-add: cyber-tiel, ornith, the shipped Tiel tag,
# nemotron-3.5-lightning, nemotron-cascade-2, qwen3.8. Pass tags as arguments to
# run a candidate; the four below stay as its comparison set.
FIELD_ALL=(
  "qwen3.6:35b-a3b-q4_K_M-agentic"
  "north-mini-code-1.0:q4_K_M-ctx256k-agentic"
  "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic"
  "tiel-coder:35b-q5-ctx256k-agentic"
)
# n>=2 for anything a recommendation rests on: v4's n=1 pass put Tiel at 40% and
# CyberTiel at 20%; n=3 put them at 37% and 27%. Both single samples were wrong.
FIELD_N2=("${FIELD_ALL[@]}")
if [ "$#" -gt 0 ]; then FIELD_ALL=("$@"); FIELD_N2=("$@"); fi

mapfile -t TASKS < <(grep -vE '^\s*#|^\s*$' subset.txt)
TARGS=(); for t in "${TASKS[@]}"; do TARGS+=(-t "$t"); done
echo "subset (${#TASKS[@]} tasks): ${TASKS[*]}"

echo "=== preflight ==="
curl -s -m10 "$HOST/api/version" >/dev/null || { echo "server not answering -- check USB ethernet"; exit 2; }
docker compose version >/dev/null 2>&1 || { echo "docker compose plugin missing"; exit 5; }

# Warn (do not fail) if any tag is absent from the box -- a 404 would corrupt turns.
present="$(curl -s "$HOST/api/tags")"
for m in "${FIELD_ALL[@]}"; do
  echo "$present" | grep -q "\"$m\"" || echo "  WARN: $m not on the server -- create it first (see toTest.md Stage 1)"
done

# NOTE (2026-09-18, found mid-round): the run-id must be LOWERCASE. terminal-bench
# derives the `docker compose -p <project>` name from it, and compose rejects any
# project name containing uppercase:
#   invalid project name "...q4_K_M...": must consist only of lowercase
#   alphanumeric characters, hyphens, and underscores
# Tags carrying a quant suffix like q4_K_M therefore failed *every* task in ~0.4s
# with a tidy "Accuracy: 0.00%" -- qwen3.6, north-mini and gemma4 were all hit,
# while tiel/cyber-tiel (q5) and ornith (no quant in the tag) ran fine. The model
# tag passed to -m is untouched; only the run-id is folded to lowercase.
run_one () {  # <runs> <model...>
  local runs="$1"; shift
  for m in "$@"; do
    echo "=== $m  (n=$runs, thinking ${TB_THINKING:-on}) ==="
    "$TB" run -d "$DATASET" "${TARGS[@]}" \
      --agent-import-path "$AGENT" -m "$m" \
      -k thinking="${TB_THINKING:-on}" \
      --n-attempts "$runs" \
      --n-concurrent "$CONCURRENCY" \
      --output-path "$OUT" \
      --run-id "$(echo "$m" | tr '/:' '__' | tr 'A-Z' 'a-z')-n$runs-$(date +%H%M%S)" \
      2>&1 | tail -40
    # be a good neighbour: unload this model before the next one loads
    curl -s "$HOST/api/generate" -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1 || true
  done
}

# TB_PHASE=1 | 2 | both (default). Lets a round that was stopped mid-way resume
# without re-running passes that are already valid.
PHASE="${TB_PHASE:-both}"

if [ "$PHASE" = "1" ] || [ "$PHASE" = "both" ]; then
  echo "=== PHASE 1: ${#FIELD_ALL[@]} models x ${#TASKS[@]} tasks x n=1 ==="
  run_one 1 "${FIELD_ALL[@]}"
fi

if [ "$PHASE" = "2" ] || [ "$PHASE" = "both" ]; then
  echo "=== PHASE 2: the standing field x ${#TASKS[@]} tasks x n=2 ==="
  run_one 2 "${FIELD_N2[@]}"
fi

echo "=== results are under $OUT ; summarise with ./summarise.py ==="
python3 "$HERE/summarise.py" "$OUT" || true
echo "GO-OFFICIAL-TB-DONE"
