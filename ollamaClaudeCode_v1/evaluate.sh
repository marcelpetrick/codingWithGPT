#!/usr/bin/env bash
# evaluate.sh — full evaluation protocol for one model on one server.
#
# Speed alone does not decide usability for agentic coding, so this runs all
# four gates and writes one row per model:
#   1. speed, profiles S and L, thinking disabled
#   2. tool use via the Anthropic /v1/messages endpoint (the hard gate — a model
#      that cannot emit tool_use blocks is unusable in Claude Code regardless of
#      how fast it is)
#   3. resident VRAM and whether it spilled to CPU
#   4. context ceiling — largest num_ctx that still fits entirely in VRAM
#
# Usage: ./evaluate.sh <host> <model> [outdir]
set -uo pipefail

HOST="${1:?usage: evaluate.sh <host> <model> [outdir]}"
MODEL="${2:?usage: evaluate.sh <host> <model> [outdir]}"
OUT="${3:-$(dirname "$(readlink -f "$0")")/eval}"
BASE="http://${HOST}:11434"
mkdir -p "$OUT"
ROW="$OUT/rows.tsv"
SAFE=$(echo "$MODEL" | tr ':/' '__')

[ -f "$ROW" ] || printf 'model\tsize_gb\tvram_gb\tsplit\ttok_s_S\ttok_s_L\ttool_use\tmax_ctx_in_vram\tthink_default\tnotes\n' > "$ROW"

echo "############ $MODEL on $HOST ############"

unload() {
  for m in $(curl -s --max-time 10 "$BASE/api/ps" | jq -r '.models[]?.name'); do
    curl -s --max-time 30 -X POST "$BASE/api/generate" -H "Content-Type: application/json" \
      -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1
  done
  for _ in $(seq 1 30); do
    [ "$(curl -s --max-time 10 "$BASE/api/ps" | jq -r '.models|length')" = "0" ] && return 0
    sleep 2
  done
}

# ---- 1. speed, thinking disabled -------------------------------------------
echo "[1/4] speed (think off)"
unload
"$(dirname "$(readlink -f "$0")")/benchmark.sh" \
  --host "$HOST" --models "$MODEL" --profile "S L" --think-off \
  --cold-timeout 1200 --warm-timeout 900 --outdir "$OUT/bench-$SAFE" >"$OUT/bench-$SAFE.log" 2>&1
TSV=$(ls -t "$OUT/bench-$SAFE"/*.tsv 2>/dev/null | head -1)
TPS_S=$(awk -F'\t' '$1=="S"{print $4}' "$TSV" 2>/dev/null | head -1)
TPS_L=$(awk -F'\t' '$1=="L"{print $4}' "$TSV" 2>/dev/null | head -1)
VRAM=$(awk -F'\t' '$1=="L"{print $10}' "$TSV" 2>/dev/null | head -1)
SIZE=$(awk -F'\t' '$1=="L"{print $11}' "$TSV" 2>/dev/null | head -1)
echo "      S=${TPS_S:-?} L=${TPS_L:-?} tok/s  vram=${VRAM:-?}/${SIZE:-?} GB"

SPLIT="no"
if [ -n "${VRAM:-}" ] && [ -n "${SIZE:-}" ]; then
  [ "$(echo "$VRAM < $SIZE - 0.05" | bc 2>/dev/null)" = "1" ] && SPLIT="YES"
fi

# ---- 2. thinking behaviour with defaults -----------------------------------
echo "[2/4] thinking with defaults"
THINK=$(curl -s --max-time 900 -X POST "$BASE/api/generate" -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"Write a Python function for the Sieve of Eratosthenes with type hints.\",\"stream\":false,\"options\":{\"num_predict\":300}}" \
  | jq -r 'if (.thinking // "") == "" then "none" else "yes" end' 2>/dev/null)
echo "      thinking by default: ${THINK:-?}"

# ---- 3. tool use ------------------------------------------------------------
echo "[3/4] tool use"
TOOL=$(curl -s --max-time 900 -X POST "$BASE/v1/messages" \
  -H "Content-Type: application/json" -H "x-api-key: ollama" -H "anthropic-version: 2023-06-01" \
  -d "{\"model\":\"$MODEL\",\"max_tokens\":600,\"tools\":[{\"name\":\"write_file\",\"description\":\"Write content to a file\",\"input_schema\":{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\"},\"content\":{\"type\":\"string\"}},\"required\":[\"path\",\"content\"]}}],\"messages\":[{\"role\":\"user\",\"content\":\"Write hello world to /tmp/test.txt\"}]}" \
  | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('PARSE_FAIL'); raise SystemExit
if d.get('error'): print('API_ERROR'); raise SystemExit
sr=d.get('stop_reason')
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
if sr=='tool_use' and tu and tu[0].get('input',{}).get('path'): print('PASS')
elif tu: print('PARTIAL')
else: print('FAIL')
" 2>/dev/null)
echo "      tool use: ${TOOL:-?}"

# ---- 4. context ceiling -----------------------------------------------------
echo "[4/4] context ceiling"
MAXCTX="?"
for CTX in 32768 65536 131072 262144; do
  unload
  R=$(curl -s --max-time 1200 -X POST "$BASE/api/generate" -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1,\"num_ctx\":$CTX},\"think\":false}")
  [ -n "$(echo "$R" | jq -r '.error // empty')" ] && { echo "      ctx $CTX: error"; break; }
  read -r V S <<<"$(curl -s --max-time 10 "$BASE/api/ps" | jq -r '.models[0]? | "\(.size_vram/1e9) \(.size/1e9)"')"
  if [ -z "${V:-}" ]; then echo "      ctx $CTX: not resident"; break; fi
  if [ "$(echo "$V < $S - 0.05" | bc)" = "1" ]; then
    printf '      ctx %s: SPLIT (%.2f/%.2f GB) — ceiling is below this\n' "$CTX" "$V" "$S"
    break
  fi
  printf '      ctx %s: fully GPU (%.2f GB)\n' "$CTX" "$V"
  MAXCTX="$CTX"
done

unload
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$MODEL" "${SIZE:-}" "${VRAM:-}" "$SPLIT" "${TPS_S:-}" "${TPS_L:-}" \
  "${TOOL:-?}" "$MAXCTX" "${THINK:-?}" "" >> "$ROW"

echo "=> row appended to $ROW"
