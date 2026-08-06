#!/usr/bin/env bash
# ctx-cliff.sh — find the point where /v1/messages silently truncates input and
# tool calling dies.
#
# Why this exists. A model whose Modelfile leaves num_ctx unset inherits the
# server default, and the Anthropic-compatible /v1/messages endpoint has no
# num_ctx knob to override it. Measured on .67 (2026-08-06):
#
#   qwen3.6:35b-a3b-q4_K_M  (num_ctx unset)     qwen3.5:9b-ctx80k (81920 baked)
#     16k sent -> 16090 processed, tool YES       16k -> 16090, tool YES
#     32k sent -> 16386 processed, tool NO        32k -> 33290, tool YES
#     50k sent -> 16386 processed, tool NO        50k -> 53090, tool YES
#
# The cap is 16384 tokens. Past it the tail of the prompt - which is where the
# instruction lives - is cut off, and the model stops emitting tool_use blocks
# entirely. No error is returned. A model advertising 256K, which fits 262144 in
# VRAM and retrieves needles at 60k through /api/chat, still gives Claude Code a
# silent 16K window.
#
# The fix is to bake num_ctx into a Modelfile variant:
#   curl -X POST $HOST/api/create -d '{"model":"NAME-ctx128k","from":"NAME",
#        "parameters":{"num_ctx":131072},"stream":false}'
# Verified: the ctx128k variant of the MoE processes all 53090 tokens with tool
# calling intact.
#
# Usage: ./ctx-cliff.sh <model> [<model>...]
probe() {
  local M="$1" N="$2" body=/tmp/pb_$$.json
  python3 - "$M" "$N" "$body" <<'PY'
import json,sys
m,n,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
filler="".join("def helper_%d(x): return x + %d  # legacy shim\n"%(i,i) for i in range(n))
msg=("Here is a large excerpt of our codebase:\n\n"+filler+
     "\n\nNow: write the string \"done\" to the file /tmp/final.txt using the available tool.")
tools=[{"name":"write_file","description":"Write content to a file",
        "input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}]
json.dump({"model":m,"max_tokens":700,"tools":tools,"messages":[{"role":"user","content":msg}]},open(out,"w"))
PY
  curl -s --max-time 900 -X POST http://192.168.100.67:11434/v1/messages \
    -H "Content-Type: application/json" -H "x-api-key: ollama" -H "anthropic-version: 2023-06-01" -d @"$body" \
  | python3 -c "
import json,sys
raw=sys.stdin.read()
try: d=json.loads(raw,strict=False)
except Exception as e: print('   PARSE_FAIL',str(e)[:60]); raise SystemExit
if d.get('error'): print('   ERROR',str(d['error'])[:70]); raise SystemExit
u=d.get('usage') or {}
tu=[b for b in d.get('content',[]) if b.get('type')=='tool_use']
print('   input_tokens=%-8s tool_use=%s' % (u.get('input_tokens','?'),'YES' if tu else 'NO'))
"
  rm -f "$body"
}
for M in "$@"; do
  echo "### $M ###"
  for N in 200 800 1600 2500; do printf " %5d lines (~%2dk tok sent):\n" "$N" $((N*20/1000)); probe "$M" "$N"; done
done
