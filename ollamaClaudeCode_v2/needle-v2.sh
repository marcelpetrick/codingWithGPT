#!/usr/bin/env bash
# needle-v2.sh — the T6 needle gates, with a generation budget that does not
# manufacture failures.
#
# Why this exists. v1's agentic-test.sh and needle-retest.sh both send
# num_predict=64. That is enough for a terse model and it is NOT enough for Muse
# Glimmer, which spends most of that budget before the answer text starts. The
# first local run scored four straight FAILs, and the raw responses show why:
#
#   {"message":{"content":"CRIMSON-PANG"},"done_reason":"length","eval_count":64}
#
# The model found the needle. It was cut off mid-string, three characters into
# the passphrase, so the harness grep for CRIMSON-PANGOLIN-4471 missed and the
# row was recorded FAIL. That is the same class of budget artifact review2.md
# already documented for tool calls at max_tokens=1200 -- it was fixed there and
# left at 64 here.
#
# Everything else is deliberately identical to v1's generator (same secret, same
# two-sentence prose filler, same word counts, same think:false, temperature 0)
# so the numbers stay comparable with the .67 results in needle-retest.log.
#
# Also reports prompt_eval_count on every row, because the second failure mode
# is invisible otherwise: overflowing num_ctx makes Ollama silently keep only
# HALF the window (review2.md), and a needle buried mid-document is exactly what
# that discards.
#
# Usage: ./needle-v2.sh [--host H] [--port P] [--model M] [--num-predict N]
set -uo pipefail

HOST="127.0.0.1"; PORT="11434"; MODEL="muse-glimmer:30b-ctx128k-agentic"
NUM_PREDICT=512; TIMEOUT=3600
while [ $# -gt 0 ]; do
  case "$1" in
    --host)        HOST="$2"; shift 2 ;;
    --port)        PORT="$2"; shift 2 ;;
    --model)       MODEL="$2"; shift 2 ;;
    --num-predict) NUM_PREDICT="$2"; shift 2 ;;
    --timeout)     TIMEOUT="$2"; shift 2 ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done
BASE="http://${HOST}:${PORT}"
OUT="$(dirname "$(readlink -f "$0")")/results"
mkdir -p "$OUT"
LOG="$OUT/needle-v2.log"

baked=$(curl -s --max-time 15 -X POST "$BASE/api/show" -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\"}" | python3 -c '
import sys,json,re
try: p=json.load(sys.stdin).get("parameters","") or ""
except Exception: p=""
m=re.search(r"num_ctx\s+(\d+)",p); print(m.group(1) if m else "")')
[ -z "$baked" ] && baked=32768
printf '=== needle-v2 on %s: %s (baked num_ctx=%s, num_predict=%s) ===\n' \
  "$HOST" "$MODEL" "$baked" "$NUM_PREDICT" | tee -a "$LOG"

needle() {
  local w="$1" label="$2" body; body=$(mktemp)
  python3 - "$w" "$MODEL" "$body" "$baked" "$NUM_PREDICT" <<'PY'
import json,sys
w=int(sys.argv[1]); model=sys.argv[2]; out=sys.argv[3]
baked=int(sys.argv[4]); npred=int(sys.argv[5])
secret="The deployment passphrase is CRIMSON-PANGOLIN-4471."
# The comma is load-bearing -- see the v1 comment. Without it this is one string
# and the haystack degenerates to "ThThTh...", which every model passes.
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
           "options":{"num_predict":npred,"num_ctx":ctx,"temperature":0},
           "messages":[{"role":"user","content":q}]}, open(out,"w"))
sys.stderr.write("      %d words, num_ctx %d\n"%(words,ctx))
PY
  local R; R=$(curl -s --max-time "$TIMEOUT" -X POST "$BASE/api/chat" \
    -H "Content-Type: application/json" -d @"$body")
  rm -f "$body"
  printf '%s\n' "$R" >> "$OUT/needle-v2.raw.jsonl"
  printf '%s' "$R" | python3 -c "
import sys,json
lbl='$label'
try: d=json.load(sys.stdin)
except Exception: print('  %-6s PARSE_FAIL'%lbl); raise SystemExit
if d.get('error'): print('  %-6s ERROR %s'%(lbl,str(d['error'])[:70])); raise SystemExit
ans=(d.get('message') or {}).get('content','') or ''
pe=d.get('prompt_eval_count','?'); ec=d.get('eval_count','?')
dr=d.get('done_reason','?')
ok='CRIMSON-PANGOLIN-4471' in ans.upper()
# A truncated answer that had clearly started emitting the passphrase is the
# artifact this script exists to expose -- call it out rather than scoring FAIL.
partial=(not ok) and ('CRIMSON' in ans.upper())
v='PASS' if ok else ('TRUNCATED' if partial else 'FAIL')
print('  %-6s %-9s prompt_eval=%-7s eval=%-5s done=%-8s answer=%r'%(
      lbl,v,pe,ec,dr,ans[:60]))
" | tee -a "$LOG"
}

needle 2700  4k
needle 10700 16k
needle 40000 60k
needle 80000 120k
printf '=== finished ===\n' | tee -a "$LOG"
