#!/usr/bin/env bash
# needle-retest.sh — rerun ONLY the T6 needle gates and splice the corrected rows
# over the invalid ones in agentic/<model>.tsv.
#
# Why this exists: the first matrix ran with a one-character bug in agentic-test.sh
# (a missing comma made the haystack "ThThThTh..." instead of prose), so every T6
# result it produced is meaningless. The other gates and all speed figures are
# unaffected, so re-running the entire matrix would waste hours. This re-runs the
# needle gates alone, against the fixed generator, and replaces the T6_* rows.
#
# Usage: ./needle-retest.sh [host]           # every model already in agentic/
set -uo pipefail

HOST="${1:-192.168.100.67}"
DIR="$(dirname "$(readlink -f "$0")")"
BASE="http://$HOST:11434"
LOG="$DIR/needle-retest.log"
TIMEOUT=900

log() { printf '%s  %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

# Regenerate the needle body exactly as the fixed agentic-test.sh does.
build_body() {
  local w="$1" model="$2" out="$3" baked="$4"
  python3 - "$w" "$model" "$out" "$baked" <<'PY'
import json,sys
w=int(sys.argv[1]); model=sys.argv[2]; out=sys.argv[3]; baked=int(sys.argv[4])
secret="The deployment passphrase is CRIMSON-PANGOLIN-4471."
sent=("The service {0} handles inbound requests and logs to shard {1}. ",
      "Retention for bucket {0} is {1} days under the standard policy. ")
assert isinstance(sent, tuple) and len(sent) == 2, "filler must be a 2-tuple"
parts=[]; words=0; i=0
while words < w:
    p=sent[i%2].format("svc%d"%i, i); parts.append(p); words+=len(p.split()); i+=1
mid=len(parts)//2
doc="".join(parts[:mid])+"\n\n"+secret+"\n\n"+"".join(parts[mid:])
q=("Answer only the question, using the document below.\n"
   "QUESTION: What is the deployment passphrase?\n\n"
   "=== DOCUMENT START ===\n"+doc+"\n=== DOCUMENT END ===\n\n"
   "QUESTION (repeat): What is the deployment passphrase? "
   "Reply with the passphrase only, nothing else.")
ctx=min(int(w*2.0)+8192, baked)
json.dump({"model":model,"stream":False,"think":False,
           "options":{"num_predict":64,"num_ctx":ctx,"temperature":0},
           "messages":[{"role":"user","content":q}]}, open(out,"w"))
print("%d %d %d" % (words, len(doc), ctx))
PY
}

baked_ctx() {
  local b
  b=$(curl -s --max-time 15 -X POST "$BASE/api/show" \
      -H "Content-Type: application/json" -d "{\"model\":\"$1\"}" \
      | jq -r '.parameters // ""' | grep -oP 'num_ctx\s+\K[0-9]+' | head -1)
  [ -z "$b" ] && b=32768
  echo "$b"
}

unload_all() {
  for m in $(curl -s --max-time 10 "$BASE/api/ps" | jq -r '.models[]?.name'); do
    curl -s --max-time 30 -X POST "$BASE/api/generate" -H "Content-Type: application/json" \
      -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1
  done
}

retest_model() {
  local MODEL="$1"
  local TSV="$DIR/agentic/$(echo "$MODEL" | tr ':' '_').tsv"
  [ -f "$TSV" ] || { log "SKIP $MODEL (no $TSV)"; return; }

  local baked; baked=$(baked_ctx "$MODEL")
  log "--- $MODEL (baked num_ctx=$baked) ---"

  local NEW="$TSV.new"
  # keep every non-T6 row exactly as measured
  grep -v $'^T6_needle' "$TSV" > "$NEW"

  local pairs="2700:4k 10700:16k 40000:60k 80000:120k"
  for pair in $pairs; do
    local w="${pair%%:*}" label="${pair##*:}"
    local body="/tmp/nr_body_$$.json" shape
    shape=$(build_body "$w" "$MODEL" "$body" "$baked")
    local R; R=$(curl -s --max-time "$TIMEOUT" -X POST "$BASE/api/chat" \
      -H "Content-Type: application/json" -d @"$body")
    rm -f "$body"
    printf '%s\n' "$R" >> "$DIR/agentic/$(echo "$MODEL" | tr ':' '_').raw.jsonl"

    local ans err pe res detail
    ans=$(echo "$R" | jq -r '.message.content // ""')
    err=$(echo "$R" | jq -r '.error // empty')
    pe=$(echo "$R" | jq -r '.prompt_eval_count // "?"')
    if echo "$ans" | grep -qi "CRIMSON-PANGOLIN-4471"; then
      res=PASS; detail="found_at_${pe}_prompt_tokens"
    elif [ -n "$err" ]; then
      res=ERROR; detail="$(echo "$err" | head -c 60)"
    else
      res=FAIL; detail="missed_at_${pe}_prompt_tokens"
    fi
    printf 'T6_needle_%s\t%s\t%s\n' "$label" "$res" "$detail" >> "$NEW"
    log "      T6_needle_$label  $res  $detail  (shape: $shape)"
  done

  mv "$NEW" "$TSV"
  unload_all
}

: > "$LOG"
log "=== needle retest on $HOST (corrected prose haystack) ==="
if [ -n "${2:-}" ]; then
  retest_model "$2"
else
  for t in "$DIR"/agentic/*.tsv; do
    [ -e "$t" ] || continue
    retest_model "$(basename "$t" .tsv | sed 's/_/:/')"
  done
fi
log "=== needle retest finished ==="
