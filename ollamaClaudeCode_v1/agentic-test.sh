#!/usr/bin/env bash
# agentic-test.sh — does this model actually work as a coding agent?
#
# A single "can it emit one tool_use block" probe is far too weak a gate. Real
# agentic software engineering needs the model to survive a much harder set of
# conditions, so this exercises seven of them:
#
#   T1 single tool, simple schema        — the basic gate
#   T2 tool selection among 4 tools      — does it pick the right one, or the first one
#   T3 multi-turn with tool_result       — can it consume its own tool output and continue
#   T4 parallel tool calls               — two independent calls in one turn
#   T5 complex nested schema             — enums, arrays, nested objects (real CC tools)
#   T6 needle-in-a-haystack retrieval    — is the context window real or nominal
#   T7 tool call at large context        — the killer: tool use often degrades when
#                                          the context is nearly full, which is exactly
#                                          the state a coding agent lives in
#
# T6/T7 matter most. A model advertising 256K that loses tool calling at 100K is
# useless for repository-scale work, and that failure does not show up in any
# speed benchmark.
#
# Usage: ./agentic-test.sh <host> <model> [outdir]
set -uo pipefail

HOST="${1:?usage: agentic-test.sh <host> <model> [outdir]}"
MODEL="${2:?usage: agentic-test.sh <host> <model> [outdir]}"
OUT="${3:-$(dirname "$(readlink -f "$0")")/agentic}"
BASE="http://${HOST}:11434"
mkdir -p "$OUT"
SAFE=$(echo "$MODEL" | tr ':/' '__')
RES="$OUT/$SAFE.tsv"
RAW="$OUT/$SAFE.raw.jsonl"
: > "$RAW"
printf 'test\tresult\tdetail\n' > "$RES"

MSG_URL="$BASE/v1/messages"
HDR=(-H "Content-Type: application/json" -H "x-api-key: ollama" -H "anthropic-version: 2023-06-01")
TIMEOUT=1200

rec() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$RES"; printf '  %-28s %-8s %s\n' "$1" "$2" "$3"; }

post() {  # post <json-body> ; echoes response, tees to raw log
  local body="$1" resp
  resp=$(curl -s --max-time "$TIMEOUT" -X POST "$MSG_URL" "${HDR[@]}" -d "$body" 2>&1)
  printf '%s\n' "$resp" >> "$RAW"
  printf '%s' "$resp"
}

# Tool definitions reused across tests -- shaped like real Claude Code tools.
TOOLS_MULTI='[
 {"name":"read_file","description":"Read the contents of a file from disk","input_schema":{"type":"object","properties":{"path":{"type":"string","description":"Absolute path"}},"required":["path"]}},
 {"name":"write_file","description":"Write content to a file on disk","input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
 {"name":"run_tests","description":"Run the project test suite and return results","input_schema":{"type":"object","properties":{"suite":{"type":"string"}},"required":["suite"]}},
 {"name":"search_code","description":"Search the repository for a regex pattern","input_schema":{"type":"object","properties":{"pattern":{"type":"string"},"glob":{"type":"string"}},"required":["pattern"]}}
]'

echo "############ agentic tests: $MODEL on $HOST ############"

# ---- T1: single tool, simple schema ----------------------------------------
R=$(post "{\"model\":\"$MODEL\",\"max_tokens\":700,\"tools\":[{\"name\":\"write_file\",\"description\":\"Write content to a file\",\"input_schema\":{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\"},\"content\":{\"type\":\"string\"}},\"required\":[\"path\",\"content\"]}}],\"messages\":[{\"role\":\"user\",\"content\":\"Write hello world to /tmp/test.txt\"}]}")
eval "$(echo "$R" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('V=FAIL; D=unparseable'); raise SystemExit
if d.get('error'): print('V=FAIL; D=api_error'); raise SystemExit
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
sr=d.get('stop_reason')
if sr=='tool_use' and tu and tu[0]['input'].get('path')=='/tmp/test.txt': print('V=PASS; D=correct_args')
elif tu: print('V=PARTIAL; D=tool_use_but_args_off')
else: print('V=FAIL; D=stop_reason='+str(sr))
")"
rec T1_single_tool "$V" "$D"

# ---- T2: tool selection among four ----------------------------------------
R=$(post "{\"model\":\"$MODEL\",\"max_tokens\":700,\"tools\":$TOOLS_MULTI,\"messages\":[{\"role\":\"user\",\"content\":\"Find every place in the repo where we call deprecated_api(). Do not read or write any file yet.\"}]}")
eval "$(echo "$R" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('V=FAIL; D=unparseable'); raise SystemExit
if d.get('error'): print('V=FAIL; D=api_error'); raise SystemExit
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
if not tu: print('V=FAIL; D=no_tool_call'); raise SystemExit
n=tu[0]['name']
print('V=PASS; D=chose_'+n) if n=='search_code' else print('V=FAIL; D=chose_'+n)
")"
rec T2_tool_selection "$V" "$D"

# ---- T3: multi-turn, feed tool_result back --------------------------------
# First turn: ask it to read a file. Then hand back a result and require it to
# act on the content rather than re-reading.
R1=$(post "{\"model\":\"$MODEL\",\"max_tokens\":700,\"tools\":$TOOLS_MULTI,\"messages\":[{\"role\":\"user\",\"content\":\"Read /app/version.txt and tell me what version it contains.\"}]}")
TID=$(echo "$R1" | jq -r '[.content[]?|select(.type=="tool_use")][0].id // empty' 2>/dev/null)
if [ -z "$TID" ]; then
  rec T3_multiturn FAIL "no_tool_use_on_turn1"
else
  ASSIST=$(echo "$R1" | jq -c '{role:"assistant", content:.content}')
  R2=$(post "$(jq -nc --arg m "$MODEL" --argjson tools "$TOOLS_MULTI" --argjson a "$ASSIST" --arg tid "$TID" \
    '{model:$m, max_tokens:700, tools:$tools, messages:[
       {role:"user", content:"Read /app/version.txt and tell me what version it contains."},
       $a,
       {role:"user", content:[{type:"tool_result", tool_use_id:$tid, content:"4.2.1-rc3"}]}
     ]}')")
  eval "$(echo "$R2" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('V=FAIL; D=unparseable'); raise SystemExit
if d.get('error'): print('V=FAIL; D=api_error_turn2'); raise SystemExit
txt=' '.join(b.get('text','') for b in d.get('content',[]) if b.get('type')=='text')
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
if '4.2.1' in txt: print('V=PASS; D=used_tool_result')
elif tu: print('V=PARTIAL; D=called_tool_again')
else: print('V=FAIL; D=no_mention_of_result')
")"
  rec T3_multiturn "$V" "$D"
fi

# ---- T4: parallel tool calls ----------------------------------------------
R=$(post "{\"model\":\"$MODEL\",\"max_tokens\":900,\"tools\":$TOOLS_MULTI,\"messages\":[{\"role\":\"user\",\"content\":\"Read both /app/a.txt and /app/b.txt. Issue both reads at once in a single turn.\"}]}")
eval "$(echo "$R" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('V=FAIL; D=unparseable'); raise SystemExit
if d.get('error'): print('V=FAIL; D=api_error'); raise SystemExit
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
print('V=PASS; D=%d_parallel_calls'%len(tu)) if len(tu)>=2 else print('V=PARTIAL; D=%d_call_only'%len(tu))
")"
rec T4_parallel_calls "$V" "$D"

# ---- T5: complex nested schema -------------------------------------------
COMPLEX='[{"name":"apply_patch","description":"Apply a structured multi-file patch to the repository","input_schema":{"type":"object","properties":{"commit_message":{"type":"string"},"strategy":{"type":"string","enum":["merge","rebase","squash"]},"edits":{"type":"array","items":{"type":"object","properties":{"path":{"type":"string"},"mode":{"type":"string","enum":["create","modify","delete"]},"hunks":{"type":"array","items":{"type":"object","properties":{"old":{"type":"string"},"new":{"type":"string"}},"required":["old","new"]}}},"required":["path","mode"]}}},"required":["commit_message","strategy","edits"]}}]'
R=$(post "$(jq -nc --arg m "$MODEL" --argjson t "$COMPLEX" '{model:$m,max_tokens:1200,tools:$t,messages:[{role:"user",content:"Rename the function foo to bar in src/main.py, and delete src/old.py. Use the squash strategy and commit message \"refactor: rename foo to bar\"."}]}')")
eval "$(echo "$R" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('V=FAIL; D=unparseable'); raise SystemExit
if d.get('error'): print('V=FAIL; D=api_error'); raise SystemExit
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
if not tu: print('V=FAIL; D=no_tool_call'); raise SystemExit
i=tu[0].get('input',{})
ed=i.get('edits')
ok_strategy = i.get('strategy')=='squash'
if not isinstance(ed,list) or not ed or not isinstance(ed[0],dict):
    print('V=FAIL; D=edits_not_an_array'); raise SystemExit
# Distinguish 'wrong shape' from 'right idea, invented field names' -- the
# latter still breaks a strict tool runtime but is a different defect.
required={'path','mode'}
drift=[]
for e in ed:
    missing=required-set(e.keys())
    if missing: drift.append('+'.join(sorted(missing)))
if not drift and ok_strategy: print('V=PASS; D=nested_schema_exact_%d_edits'%len(ed))
elif not drift: print('V=PARTIAL; D=schema_ok_strategy=%s'%i.get('strategy'))
else: print('V=PARTIAL; D=schema_drift_missing_%s'%(','.join(sorted(set(drift)))[:40]))
")"
rec T5_complex_schema "$V" "$D"

# ---- T6: needle in a haystack --------------------------------------------
# Build filler of a known token scale, bury a fact in the middle, ask for it.
# Tests whether the advertised context is usable, not merely allocatable.
needle_test() {
  local words="$1" label="$2"
  local body="/tmp/nh_body_$$.json"
  # Build the whole request body in Python and post it from a file. Passing a
  # 120k-word document through argv overflows the exec limit ("Argument list too
  # long"), and /api/chat framing is required -- raw /api/generate with
  # low-entropy filler makes models echo the prompt and stop after a token or two.
  python3 - "$words" "$MODEL" "$body" <<'PY'
import json,sys
w=int(sys.argv[1]); model=sys.argv[2]; out=sys.argv[3]
secret="The deployment passphrase is CRIMSON-PANGOLIN-4471."
# Natural-language filler, varied enough not to collapse into repetition.
sent=("The service {0} handles inbound requests and logs to shard {1}. "
      "Retention for bucket {0} is {1} days under the standard policy. ")
parts=[]; i=0
while sum(len(p.split()) for p in parts) < w:
    parts.append(sent[i%2].format("svc%d"%i, i)); i+=1
mid=len(parts)//2
doc="".join(parts[:mid])+"\n\n"+secret+"\n\n"+"".join(parts[mid:])
q=("Answer only the question, using the document below.\n"
   "QUESTION: What is the deployment passphrase?\n\n"
   "=== DOCUMENT START ===\n"+doc+"\n=== DOCUMENT END ===\n\n"
   "QUESTION (repeat): What is the deployment passphrase? "
   "Reply with the passphrase only, nothing else.")
ctx=int(w*2.0)+8192
json.dump({"model":model,"stream":False,"think":False,
           "options":{"num_predict":64,"num_ctx":ctx,"temperature":0},
           "messages":[{"role":"user","content":q}]}, open(out,"w"))
PY
  local R; R=$(curl -s --max-time "$TIMEOUT" -X POST "$BASE/api/chat" \
    -H "Content-Type: application/json" -d @"$body")
  rm -f "$body"
  printf '%s\n' "$R" >> "$RAW"
  local ans err pe
  ans=$(echo "$R" | jq -r '.message.content // ""')
  err=$(echo "$R" | jq -r '.error // empty')
  pe=$(echo "$R" | jq -r '.prompt_eval_count // "?"')
  if echo "$ans" | grep -qi "CRIMSON-PANGOLIN-4471"; then
    rec "T6_needle_$label" PASS "found_at_${pe}_prompt_tokens"
  elif [ -n "$err" ]; then
    rec "T6_needle_$label" ERROR "$(echo "$err" | head -c 60)"
  else
    rec "T6_needle_$label" FAIL "missed_at_${pe}_prompt_tokens"
  fi
}
needle_test 4000   4k
needle_test 16000  16k
needle_test 60000  60k
needle_test 120000 120k

# ---- T7: tool call with a nearly-full context ----------------------------
# The state a coding agent actually lives in. Many models silently stop
# emitting tool_use blocks once the context is loaded up.
# /v1/messages has no num_ctx knob, so the model's own default context applies.
# Each line below is ~20 tokens, so 2500 lines is ~50k tokens: heavily loaded for
# an 80k model, comfortably inside a 256k one, and over the 32k default that
# .67 ships with -- which is itself worth observing.
python3 - > /tmp/big_$$.txt <<'PY'
import sys
for i in range(2500):
    sys.stdout.write("def helper_%d(x): return x + %d  # legacy shim\n" % (i, i))
PY
BIG=$(python3 -c "
import json
d=open('/tmp/big_$$.txt').read()
print(json.dumps('Here is a large excerpt of our codebase:\n\n'+d+'\n\nNow: write the string \"done\" to the file /tmp/final.txt using the available tool.'))")
rm -f /tmp/big_$$.txt
# Repeated 3x on purpose. During harness validation this test returned PASS and
# then FAIL on byte-identical input at the same 53281 tokens, so the behaviour is
# probabilistic rather than binary. A single trial would report a coin flip as a
# capability. What a coding agent needs to know is the *rate*.
T7_PASS=0; T7_TOKENS="?"; T7_MODES=""
for trial in 1 2 3; do
  R=$(post "$(jq -nc --arg m "$MODEL" --argjson tools "$TOOLS_MULTI" --argjson c "$BIG" \
    '{model:$m,max_tokens:700,tools:$tools,messages:[{role:"user",content:$c}]}')")
  eval "$(echo "$R" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('V=FAIL; T=?'); raise SystemExit
if d.get('error'): print('V=ERROR; T=?'); raise SystemExit
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
it=(d.get('usage') or {}).get('input_tokens','?')
if tu and tu[0]['name']=='write_file': print('V=PASS; T=%s'%it)
elif tu: print('V=WRONGTOOL; T=%s'%it)
else: print('V=FAIL; T=%s'%it)
")"
  [ "$V" = "PASS" ] && T7_PASS=$((T7_PASS+1))
  T7_TOKENS="$T"
  T7_MODES="$T7_MODES$V,"
done
if   [ "$T7_PASS" = "3" ]; then T7V=PASS
elif [ "$T7_PASS" = "0" ]; then T7V=FAIL
else T7V=FLAKY; fi
rec T7_tool_at_long_ctx "$T7V" "${T7_PASS}/3_at_${T7_TOKENS}_tokens[${T7_MODES%,}]"

# unload so the next model starts clean
for m in $(curl -s --max-time 10 "$BASE/api/ps" | jq -r '.models[]?.name'); do
  curl -s --max-time 30 -X POST "$BASE/api/generate" -H "Content-Type: application/json" \
    -d "{\"model\":\"$m\",\"keep_alive\":0}" >/dev/null 2>&1
done

echo "=> $RES"
