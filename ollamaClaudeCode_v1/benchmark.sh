#!/usr/bin/env bash
# Ollama benchmark harness v1
#
# Differences vs v0/benchmark.sh:
#   - host is a parameter, not hardcoded
#   - two prompt profiles (S = short/coding, L = long/prose) so results are
#     comparable both to v0 run 1-5 (S) and to Alex's numbers (L)
#   - forces an unload between models (keep_alive:0) to avoid the model-swap
#     deadlock that killed v0 run 3
#   - tiered timeouts: long on first (cold) touch, short once warm
#   - thinking tokens counted separately from answer tokens
#   - TSV output so runs can be diffed instead of eyeballed
#
# Usage:
#   ./benchmark.sh --host 192.168.100.37
#   ./benchmark.sh --host 192.168.100.67 --models qwen3.6:27b-q8_0
#   ./benchmark.sh --host 192.168.100.37 --profile S --skip-cold-timeout 900
#
set -uo pipefail

HOST="192.168.100.37"
PORT="11434"
PROFILES="S L"
MODELS_ARG=""
COLD_TIMEOUT=600          # first touch of a model: cold load from disk
WARM_TIMEOUT=300          # subsequent calls: model already resident
THINK_MODE="default"      # default | off  (off sends "think": false)
OUTDIR=""
SKIP_PATTERN="embedding|-vl:|flux"

# Profile S: identical to v0/benchmark.sh — keeps continuity with runs 1-5
PROMPT_S="Write a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes. Include type hints and a brief docstring."
NUM_PREDICT_S=300

# Profile L: Alex's prompt. Uncapped in spirit; 4096 is a runaway guard only.
PROMPT_L="Write exactly 1000 tokens about GPUs."
NUM_PREDICT_L=4096

while [ $# -gt 0 ]; do
  case "$1" in
    --host)     HOST="$2"; shift 2 ;;
    --port)     PORT="$2"; shift 2 ;;
    --models)   MODELS_ARG="$2"; shift 2 ;;
    --profile)  PROFILES="$2"; shift 2 ;;
    --cold-timeout) COLD_TIMEOUT="$2"; shift 2 ;;
    --warm-timeout) WARM_TIMEOUT="$2"; shift 2 ;;
    --think-off) THINK_MODE="off"; shift ;;
    --outdir)   OUTDIR="$2"; shift 2 ;;
    -h|--help)  sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

SERVER="http://${HOST}:${PORT}"
STAMP=$(date +%Y%m%d-%H%M%S)
[ -n "$OUTDIR" ] || OUTDIR="$(dirname "$0")/results"
mkdir -p "$OUTDIR"
TSV="${OUTDIR}/${HOST}-${STAMP}.tsv"

VERSION=$(curl -s --max-time 5 "$SERVER/api/version" | jq -r '.version // "unreachable"')
if [ "$VERSION" = "unreachable" ]; then
  echo "ERROR: $SERVER not reachable" >&2
  exit 1
fi

if [ -n "$MODELS_ARG" ]; then
  MODELS=$(echo "$MODELS_ARG" | tr ',' ' ')
else
  MODELS=$(curl -s --max-time 15 "$SERVER/api/tags" | jq -r '.models[].name' | sort)
fi

printf 'profile\tmodel\tstatus\ttok_s\teval_count\tthink_count\tload_s\tprompt_eval_s\ttotal_s\tvram_gb\tsize_gb\n' > "$TSV"

echo "=============================================="
echo " Ollama benchmark v1"
echo " Server:   $SERVER  (ollama $VERSION)"
echo " Profiles: $PROFILES"
echo " Timeouts: cold ${COLD_TIMEOUT}s / warm ${WARM_TIMEOUT}s"
echo " Thinking: $THINK_MODE"
echo " Output:   $TSV"
echo "=============================================="
echo ""

# Force the server to drop whatever is resident, then wait for VRAM to free.
# v0 run 3 lost an entire run because a stuck model-swap queued every later
# request behind it. Unloading between models is the mitigation.
unload_all() {
  local loaded
  loaded=$(curl -s --max-time 10 "$SERVER/api/ps" | jq -r '.models[]?.name')
  for m in $loaded; do
    curl -s --max-time 30 -X POST "$SERVER/api/generate" \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1
  done
  for _ in $(seq 1 30); do
    local n
    n=$(curl -s --max-time 10 "$SERVER/api/ps" | jq -r '.models | length' 2>/dev/null || echo 1)
    [ "$n" = "0" ] && return 0
    sleep 2
  done
  echo "    WARN: VRAM did not free within 60s — server may be wedged" >&2
  return 1
}

run_one() {
  local model="$1" profile="$2" prompt="$3" numpred="$4" timeout="$5"
  local think_field=""
  [ "$THINK_MODE" = "off" ] && think_field=', "think": false'

  local body
  body=$(jq -nc --arg m "$model" --arg p "$prompt" --argjson n "$numpred" \
    '{model:$m, prompt:$p, stream:false, options:{num_predict:$n}}')
  [ "$THINK_MODE" = "off" ] && body=$(echo "$body" | jq -c '. + {think:false}')

  local start end elapsed resp exit_code
  start=$(date +%s%3N)
  resp=$(curl -s --max-time "$timeout" -X POST "$SERVER/api/generate" \
    -H "Content-Type: application/json" -d "$body" 2>&1)
  exit_code=$?
  end=$(date +%s%3N)
  elapsed=$(( end - start ))

  if [ $exit_code -eq 28 ]; then
    printf '%s\t%s\tTIMEOUT\t\t\t\t\t\t%s\t\t\n' "$profile" "$model" "$(echo "scale=1;$elapsed/1000"|bc)" >> "$TSV"
    echo "    [$profile] TIMEOUT after ${timeout}s"
    return 1
  fi
  if [ $exit_code -ne 0 ]; then
    printf '%s\t%s\tERROR-curl%s\t\t\t\t\t\t\t\t\n' "$profile" "$model" "$exit_code" >> "$TSV"
    echo "    [$profile] ERROR (curl exit $exit_code)"
    return 1
  fi

  local apierr
  apierr=$(echo "$resp" | jq -r '.error // empty' 2>/dev/null)
  if [ -n "$apierr" ]; then
    printf '%s\t%s\tERROR-api\t\t\t\t\t\t\t\t\n' "$profile" "$model" >> "$TSV"
    echo "    [$profile] API ERROR: ${apierr:0:120}"
    return 1
  fi

  local ec ed ld pe td think_txt think_ct tps
  ec=$(echo "$resp" | jq -r '.eval_count // 0')
  ed=$(echo "$resp" | jq -r '.eval_duration // 0')
  ld=$(echo "$resp" | jq -r '.load_duration // 0')
  pe=$(echo "$resp" | jq -r '.prompt_eval_duration // 0')
  td=$(echo "$resp" | jq -r '.total_duration // 0')
  # newer ollama returns reasoning separately in .thinking
  think_txt=$(echo "$resp" | jq -r '.thinking // ""')
  think_ct=$(echo -n "$think_txt" | wc -w)

  if [ "$ed" -gt 0 ] 2>/dev/null && [ "$ec" -gt 0 ] 2>/dev/null; then
    tps=$(echo "scale=1; $ec * 1000000000 / $ed" | bc)
  else
    tps="0"
  fi

  # VRAM while still resident
  local vram size
  vram=$(curl -s --max-time 5 "$SERVER/api/ps" | jq -r --arg m "$model" '(.models[]? | select(.name==$m) | .size_vram/1e9*100|floor/100) // empty')
  size=$(curl -s --max-time 5 "$SERVER/api/ps" | jq -r --arg m "$model" '(.models[]? | select(.name==$m) | .size/1e9*100|floor/100) // empty')

  printf '%s\t%s\tOK\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$profile" "$model" "$tps" "$ec" "$think_ct" \
    "$(echo "scale=2;$ld/1000000000"|bc)" \
    "$(echo "scale=3;$pe/1000000000"|bc)" \
    "$(echo "scale=2;$td/1000000000"|bc)" \
    "${vram:-}" "${size:-}" >> "$TSV"

  local split=""
  if [ -n "$vram" ] && [ -n "$size" ]; then
    [ "$(echo "$vram < $size - 0.05" | bc)" = "1" ] && split="  SPLIT!"
  fi
  printf '    [%s] OK  %s tok/s  %s tokens  load %ss  total %ss  vram %s/%s GB%s\n' \
    "$profile" "$tps" "$ec" "$(echo "scale=1;$ld/1000000000"|bc)" \
    "$(echo "scale=1;$td/1000000000"|bc)" "${vram:-?}" "${size:-?}" "$split"
  [ "$think_ct" -gt 0 ] && echo "        thinking block: ~$think_ct words"
  return 0
}

for MODEL in $MODELS; do
  if echo "$MODEL" | grep -qE "$SKIP_PATTERN"; then
    echo "[$MODEL] SKIP (vision/embedding/image)"
    continue
  fi
  echo "[$MODEL]"
  unload_all
  FIRST=1
  for P in $PROFILES; do
    if [ "$P" = "S" ]; then PROMPT="$PROMPT_S"; NP=$NUM_PREDICT_S
    else                    PROMPT="$PROMPT_L"; NP=$NUM_PREDICT_L; fi
    if [ $FIRST -eq 1 ]; then TO=$COLD_TIMEOUT; FIRST=0; else TO=$WARM_TIMEOUT; fi
    run_one "$MODEL" "$P" "$PROMPT" "$NP" "$TO"
  done
  echo ""
done

unload_all

echo ""
echo "=============================================="
echo " Summary — $SERVER (ollama $VERSION)"
echo "=============================================="
column -t -s $'\t' "$TSV"
echo ""
echo "TSV: $TSV"
