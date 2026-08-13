#!/usr/bin/env bash
# tokrate.sh — generation and prefill throughput, straight from Ollama's own counters.
#
# Why not reuse v1's benchmark.sh: that one sweeps profiles and writes a report.
# Here the question is narrower and gets asked of three different models on the
# same box in one sitting — muse-glimmer, nemotron-3.5-lightning, and the
# incumbent qwen3.6 MoE — so this stays a single table with one row per (model,
# prompt size).
#
# The numbers reported are Ollama's, not wall-clock:
#
#   generation tok/s = eval_count / eval_duration
#   prefill    tok/s = prompt_eval_count / prompt_eval_duration
#
# eval_duration excludes model load, which is what makes a cold and a warm run
# comparable. load_duration is printed separately rather than folded in, because
# on a 40 GB box the load is seconds and would otherwise dominate a short run.
#
# Every model is asked the same question with the same seed and temperature 0, so
# the only variable left is the model. num_predict is fixed rather than left to
# the model's own stopping point -- a chatty model would otherwise look slower
# purely by generating longer, and a terse one would post a rate measured over a
# handful of tokens.
#
# Usage: ./tokrate.sh [--host H] [--port P] [--n N] <model> [<model>...]
set -uo pipefail

HOST="192.168.100.67"; PORT="11434"; NPRED=256; TIMEOUT=1800
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --n)    NPRED="$2"; shift 2 ;;
    *) break ;;
  esac
done
[ $# -ge 1 ] || { echo "usage: tokrate.sh [--host H] [--n N] <model>..." >&2; exit 2; }
BASE="http://${HOST}:${PORT}"
OUT="$(dirname "$(readlink -f "$0")")/results"; mkdir -p "$OUT"
TSV="$OUT/tokrate.tsv"
[ -s "$TSV" ] || printf 'model\tprompt_words\tprompt_tok\tgen_tok\tprefill_tps\tgen_tps\tload_s\ttotal_s\n' > "$TSV"

run() {
  local M="$1" W="$2" body; body=$(mktemp)
  python3 - "$M" "$W" "$body" "$NPRED" <<'PY'
import json,sys
m,w,out,npred=sys.argv[1],int(sys.argv[2]),sys.argv[3],int(sys.argv[4])
# Same filler shape as needle-v2.sh so prompt-token counts stay comparable across
# this directory's scripts. The task at the end is fixed-length prose generation:
# it exercises the decode path without depending on whether the model can solve
# anything, which is what a speed test should be measuring.
sent=("The service svc{0} handles inbound requests and logs to shard {0}. ",
      "Retention for bucket b{0} is {0} days under the standard policy. ")
parts=[];words=0;i=0
while words<w:
    p=sent[i%2].format(i); parts.append(p); words+=len(p.split()); i+=1
ctx="".join(parts)
q=(("Here is an operations log:\n\n"+ctx+"\n\n") if w else "")+ \
  "Write a short technical description of a rate limiter. Plain prose."
json.dump({"model":m,"stream":False,"think":False,
           "options":{"num_predict":npred,"temperature":0,"seed":42},
           "messages":[{"role":"user","content":q}]},open(out,"w"))
PY
  local R; R=$(curl -s --max-time "$TIMEOUT" -X POST "$BASE/api/chat" \
    -H 'Content-Type: application/json' -d @"$body")
  rm -f "$body"
  printf '%s' "$R" | python3 -c "
import sys,json
m='$M'; w='$W'
try: d=json.load(sys.stdin)
except Exception: print('  %-42s PARSE_FAIL'%m); raise SystemExit
if d.get('error'): print('  %-42s ERROR %s'%(m,str(d['error'])[:60])); raise SystemExit
pe=d.get('prompt_eval_count',0); pd=d.get('prompt_eval_duration',0) or 1
ec=d.get('eval_count',0);        ed=d.get('eval_duration',0) or 1
ld=d.get('load_duration',0);     td=d.get('total_duration',0)
pf=pe/(pd/1e9); gt=ec/(ed/1e9)
print('  %-42s %7s %8s %8s %9.1f %9.2f %8.1f %8.1f'%(m,w,pe,ec,pf,gt,ld/1e9,td/1e9))
open('$TSV','a').write('%s\t%s\t%d\t%d\t%.1f\t%.2f\t%.1f\t%.1f\n'%(m,w,pe,ec,pf,gt,ld/1e9,td/1e9))
"
}

printf '%-44s %7s %8s %8s %9s %9s %8s %8s\n' \
  '  model' words prompt_t gen_t prefill_s gen_tps load_s total_s
for M in "$@"; do
  for W in 0 2000 20000; do
    run "$M" "$W"
  done
done
echo
echo "appended to $TSV"
