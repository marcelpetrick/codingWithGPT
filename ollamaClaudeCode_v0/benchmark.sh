#!/usr/bin/env bash
# Benchmark all Ollama models for coding tasks
# Usage: ./benchmark.sh [--timeout <seconds>]

SERVER="http://192.168.100.37:11434"
TIMEOUT=180
PROMPT="Write a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes. Include type hints and a brief docstring."

# Models to skip (vision/embedding — not relevant for Claude Code)
SKIP_PATTERN="embedding|vl:"

MODELS=$(curl -s "$SERVER/api/tags" | jq -r '.models[].name')
RESULTS=()

echo "=============================="
echo " Ollama Coding Benchmark"
echo " Server: $SERVER"
echo " Timeout per model: ${TIMEOUT}s"
echo " Prompt: (sieve of eratosthenes)"
echo "=============================="
echo ""

for MODEL in $MODELS; do
  if echo "$MODEL" | grep -qE "$SKIP_PATTERN"; then
    echo "[$MODEL] SKIP (vision/embedding)"
    continue
  fi

  echo -n "[$MODEL] Testing... "
  START=$(date +%s%3N)

  RESPONSE=$(curl -s --max-time "$TIMEOUT" \
    -X POST "$SERVER/api/generate" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"$MODEL\",
      \"prompt\": \"$PROMPT\",
      \"stream\": false,
      \"options\": {\"num_predict\": 300}
    }" 2>&1)

  EXIT=$?
  END=$(date +%s%3N)
  ELAPSED=$(( (END - START) ))

  if [ $EXIT -eq 28 ]; then
    echo "TIMEOUT (>${TIMEOUT}s)"
    RESULTS+=("TIMEOUT|$MODEL|>$((TIMEOUT * 1000))|")
    continue
  fi

  if [ $EXIT -ne 0 ]; then
    echo "ERROR (curl exit $EXIT)"
    RESULTS+=("ERROR|$MODEL|${ELAPSED}|curl exit $EXIT")
    continue
  fi

  EVAL_COUNT=$(echo "$RESPONSE" | jq -r '.eval_count // "?"')
  EVAL_DURATION_NS=$(echo "$RESPONSE" | jq -r '.eval_duration // 0')
  PROMPT_EVAL_NS=$(echo "$RESPONSE" | jq -r '.prompt_eval_duration // 0')
  TOTAL_DURATION_NS=$(echo "$RESPONSE" | jq -r '.total_duration // 0')

  # tokens/sec
  if [ "$EVAL_DURATION_NS" -gt 0 ] 2>/dev/null && [ "$EVAL_COUNT" != "?" ]; then
    TPS=$(echo "scale=1; $EVAL_COUNT * 1000000000 / $EVAL_DURATION_NS" | bc 2>/dev/null || echo "?")
  else
    TPS="?"
  fi

  TOTAL_SEC=$(echo "scale=2; $ELAPSED / 1000" | bc)
  SNIPPET=$(echo "$RESPONSE" | jq -r '.response // ""' | head -c 120 | tr '\n' ' ')

  echo "OK — ${TOTAL_SEC}s | ${EVAL_COUNT} tokens | ${TPS} tok/s"
  echo "    Preview: $SNIPPET..."
  echo ""

  RESULTS+=("OK|$MODEL|${ELAPSED}|${TPS}|${EVAL_COUNT}|${TOTAL_SEC}s")
done

echo ""
echo "=============================="
echo " Summary (sorted by speed)"
echo "=============================="
echo ""

# Sort OK results by elapsed time
printf '%s\n' "${RESULTS[@]}" | grep "^OK" | sort -t'|' -k3 -n | while IFS='|' read -r status model ms tps tokens elapsed; do
  printf "  %-30s  %s  %s tok/s  %s tokens\n" "$model" "$elapsed" "$tps" "$tokens"
done

echo ""
echo "--- Timed out / errored ---"
printf '%s\n' "${RESULTS[@]}" | grep -v "^OK" | while IFS='|' read -r status model rest; do
  printf "  %-30s  %s\n" "$model" "$status"
done
