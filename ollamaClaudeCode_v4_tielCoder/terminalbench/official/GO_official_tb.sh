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
#   phase 1: all 6 models x the frozen 10-task subset x n=1   (~2.0 h)
#   phase 2: Tiel + CyberTiel + control x the subset x n=2    (~1.5 h)
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

# Subject models first (they get n=2 in phase 2), then the comparators.
FIELD_ALL=(
  "tiel-coder:35b-q5-ctx256k-agentic"
  "cyber-tiel:35b-q5-ctx256k-agentic"
  "qwen3.6:35b-a3b-q4_K_M-agentic"
  "north-mini-code-1.0:q4_K_M-ctx256k-agentic"
  "ornith:35b-ctx256k-agentic"
  "gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic"
)
FIELD_N2=(
  "tiel-coder:35b-q5-ctx256k-agentic"
  "cyber-tiel:35b-q5-ctx256k-agentic"
  "qwen3.6:35b-a3b-q4_K_M-agentic"
)
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

run_one () {  # <runs> <model...>
  local runs="$1"; shift
  for m in "$@"; do
    echo "=== $m  (n=$runs, thinking off) ==="
    "$TB" run -d "$DATASET" "${TARGS[@]}" \
      --agent-import-path "$AGENT" -m "$m" \
      -k thinking=off \
      --n-attempts "$runs" \
      --n-concurrent "$CONCURRENCY" \
      --output-path "$OUT" \
      --run-id "$(echo "$m" | tr '/:' '__')-n$runs-$(date +%H%M%S)" \
      2>&1 | tail -40
    # be a good neighbour: unload this model before the next one loads
    curl -s "$HOST/api/generate" -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1 || true
  done
}

echo "=== PHASE 1: all ${#FIELD_ALL[@]} models x ${#TASKS[@]} tasks x n=1 ==="
run_one 1 "${FIELD_ALL[@]}"

echo "=== PHASE 2: subject trio x ${#TASKS[@]} tasks x n=2 ==="
run_one 2 "${FIELD_N2[@]}"

echo "=== results are under $OUT ; summarise with ./summarise.py ==="
python3 "$HERE/summarise.py" "$OUT" || true
echo "GO-OFFICIAL-TB-DONE"
