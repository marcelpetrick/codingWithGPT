#!/usr/bin/env bash
# sampling-test.sh — does the vendor's default sampling break structured tool calls?
#
# Every model on both hosts ships the qwen prose defaults:
#     temperature 1, top_p 0.95, top_k 20, presence_penalty 1.5
#
# Two of those are hostile to tool use:
#   - temperature 1 makes tool calls nondeterministic, so a single-trial gate
#     reports a coin flip as a capability
#   - presence_penalty 1.5 penalises tokens already emitted. In JSON that means
#     quotes, braces and *repeated field names* -- and an array-of-objects schema
#     must repeat "path"/"mode"/"old"/"new" once per element. The penalty pushes
#     directly against the required output.
#
# This is what qwen3.5:9b-ctx96k's lone T5 failure looks like, while the same
# weights at ctx80k passed: nondeterminism, not a context effect.
#
# Runs the T5 nested-schema call N times per configuration and reports pass rates.
# Usage: ./sampling-test.sh [N]
set -uo pipefail

N="${1:-8}"
DIR="$(dirname "$(readlink -f "$0")")"
OUT="$DIR/sampling/results.tsv"
mkdir -p "$DIR/sampling"
[ -s "$OUT" ] || printf 'host\tmodel\tconfig\tpasses\ttrials\tdetail\n' > "$OUT"

COMPLEX='[{"name":"apply_patch","description":"Apply a structured multi-file patch to the repository","input_schema":{"type":"object","properties":{"commit_message":{"type":"string"},"strategy":{"type":"string","enum":["merge","rebase","squash"]},"edits":{"type":"array","items":{"type":"object","properties":{"path":{"type":"string"},"mode":{"type":"string","enum":["create","modify","delete"]},"hunks":{"type":"array","items":{"type":"object","properties":{"old":{"type":"string"},"new":{"type":"string"}},"required":["old","new"]}}},"required":["path","mode"]}}},"required":["commit_message","strategy","edits"]}}]'
PROMPT='Rename the function foo to bar in src/main.py, and delete src/old.py. Use the squash strategy and commit message "refactor: rename foo to bar".'

# One trial. $3 is extra JSON merged into the request body ("" = model defaults).
trial() {
  local host="$1" model="$2" extra="$3"
  [ -z "$extra" ] && extra='{}'
  local body
  body=$(jq -nc --arg m "$model" --argjson t "$COMPLEX" --arg p "$PROMPT" \
    --argjson x "$extra" \
    '{model:$m,max_tokens:4000,thinking:{type:"disabled"},tools:$t,
      messages:[{role:"user",content:$p}]} * $x')
  curl -s --max-time 300 -X POST "http://$host:11434/v1/messages" \
    -H "Content-Type: application/json" -d "$body" \
  | python3 -c "
import json,sys
try: d=json.loads(sys.stdin.read(),strict=False)
except Exception: print('FAIL unparseable'); raise SystemExit
if d.get('error'): print('FAIL api_error:'+str(d['error'])[:40]); raise SystemExit
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
if not tu: print('FAIL no_tool_call'); raise SystemExit
i=tu[0].get('input',{}); ed=i.get('edits')
if not isinstance(ed,list) or not ed or not isinstance(ed[0],dict):
    print('FAIL edits_not_array'); raise SystemExit
miss=set()
for e in ed: miss |= ({'path','mode'} - set(e.keys()))
if miss: print('FAIL drift_missing_'+','.join(sorted(miss))); raise SystemExit
if i.get('strategy')!='squash': print('FAIL strategy_'+str(i.get('strategy'))); raise SystemExit
print('PASS %d_edits'%len(ed))
"
}

run_config() {
  local host="$1" model="$2" name="$3" extra="$4"
  local pass=0 details=""
  printf '  %-28s ' "$name"
  for i in $(seq 1 "$N"); do
    local r; r=$(trial "$host" "$model" "$extra")
    case "$r" in PASS*) pass=$((pass+1)); printf '.' ;; *) printf 'x'; details="$details${r#FAIL };" ;; esac
  done
  printf '  %d/%d %s\n' "$pass" "$N" "$details"
  printf '%s\t%s\t%s\t%d\t%d\t%s\n' "$host" "$model" "$name" "$pass" "$N" "${details:-clean}" >> "$OUT"
}

for spec in "192.168.100.37 qwen3.5:9b-ctx96k" \
            "192.168.100.37 qwen3.5:9b-ctx80k" \
            "192.168.100.67 qwen3.6:35b-a3b-q4_K_M-ctx256k"; do
  set -- $spec
  echo "############ $2 on $1 ($N trials each) ############"
  run_config "$1" "$2" "model defaults"          ""
  run_config "$1" "$2" "temperature 0"           '{"temperature":0}'
  run_config "$1" "$2" "temp 0 + top_p 1"        '{"temperature":0,"top_p":1}'
  # unload between models so the next one starts clean
  for m in $(curl -s --max-time 10 "http://$1:11434/api/ps" | jq -r '.models[]?.name'); do
    curl -s --max-time 30 -X POST "http://$1:11434/api/generate" \
      -H "Content-Type: application/json" -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1
  done
done
echo "=> $OUT"
