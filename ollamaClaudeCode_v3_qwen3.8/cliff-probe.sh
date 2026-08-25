#!/usr/bin/env bash
# cliff-probe.sh — does this model still emit tool_use blocks as the prompt grows?
#
# A host-parameterised port of ../ollamaClaudeCode_v1/ctx-cliff.sh. The original
# is deliberately left untouched: it is validated, its measurements are quoted
# throughout review2.md, and it hardcodes 192.168.100.67 because that was the
# only box that mattered. This version takes --host/--port so the same probe can
# run against a laptop server, and reports processed-token counts the same way
# so the two sets of numbers stay directly comparable.
#
# What it is looking for, from the v1 finding it exists to re-test:
#
#   /v1/messages has no num_ctx knob. A model whose Modelfile leaves num_ctx
#   unset inherits the server default. Past that default the TAIL of the prompt
#   is silently discarded -- and the tail is where the instruction lives -- so
#   the model stops emitting tool_use entirely. No error is returned. On .67
#   that cap was 16384 tokens, on a model advertising 256K.
#
# So: a bare tag is EXPECTED to fail at large N. That is the finding, not a bug
# in this script. The baked variant is the one that must pass.
#
# Usage: ./cliff-probe.sh [--host H] [--port P] <model> [<model>...]
set -uo pipefail

HOST="127.0.0.1"; PORT="11435"; TIMEOUT=1800
while [ $# -gt 0 ]; do
  case "$1" in
    --host)    HOST="$2"; shift 2 ;;
    --port)    PORT="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    *) break ;;
  esac
done
[ $# -ge 1 ] || { echo "usage: cliff-probe.sh [--host H] [--port P] <model>..." >&2; exit 2; }
URL="http://${HOST}:${PORT}/v1/messages"

probe() {
  local M="$1" N="$2" body; body=$(mktemp)
  python3 - "$M" "$N" "$body" <<'PY'
import json,sys
m,n,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
# Same filler as v1 so token counts line up with the .67 numbers.
filler="".join("def helper_%d(x): return x + %d  # legacy shim\n"%(i,i) for i in range(n))
msg=("Here is a large excerpt of our codebase:\n\n"+filler+
     "\n\nNow: write the string \"done\" to the file /tmp/final.txt using the available tool.")
tools=[{"name":"write_file","description":"Write content to a file",
        "input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},
        "required":["path","content"]}}]
json.dump({"model":m,"max_tokens":4000,"tools":tools,
           "messages":[{"role":"user","content":msg}]},open(out,"w"))
PY
  curl -s --max-time "$TIMEOUT" -X POST "$URL" \
    -H "Content-Type: application/json" -H "x-api-key: ollama" \
    -H "anthropic-version: 2023-06-01" -d @"$body" \
  | python3 -c "
import json,sys
raw=sys.stdin.read()
if not raw.strip(): print('   EMPTY_RESPONSE (timeout?)'); raise SystemExit
try: d=json.loads(raw,strict=False)
except Exception as e: print('   PARSE_FAIL',str(e)[:60]); raise SystemExit
if d.get('error'): print('   ERROR',str(d['error'])[:90]); raise SystemExit
u=d.get('usage') or {}
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
print('   input_tokens=%-8s stop=%-12s tool_use=%s' % (
      u.get('input_tokens','?'), d.get('stop_reason','?'), 'YES' if tu else 'NO'))
"
  rm -f "$body"
}

for M in "$@"; do
  echo "### $M ###"
  for N in 200 800 1600 2500; do
    printf ' %5d lines (~%2dk tok sent):\n' "$N" $((N*20/1000))
    probe "$M" "$N"
  done
done
