#!/usr/bin/env bash
# kv-probe.sh — measure what a context window actually costs in bytes.
#
# Muse Glimmer has hybrid attention: 39 of its 52 layers are sliding-window
# capped at 2048 tokens, 13 are full. Whether Ollama's implementation honours
# that or allocates full-length KV for all 52 layers changes the answer to two
# separate questions in muse_ollama.md, and cannot be read out of the GGUF:
#
#   SWA-aware  13*1024*n + 39*1024*2048   ->  1.83 GB at n=131072
#   naive      52*1024*n                  ->  6.98 GB at n=131072
#
# (1024 bytes per token per full-attention layer = 2 (K,V) * 2 KV heads *
#  128 head dim * 2 bytes at f16.)
#
# Method: build a variant at each num_ctx, load it, read total size from
# /api/ps. The intercept is the weights, the slope is the real per-token KV
# cost. A slope near 13312 B/tok means SWA is honoured; near 53248 means it is
# not. This works on any host, including a laptop that could never hold the
# full window -- we are measuring an allocation rate, not running a benchmark,
# so the small windows carry the signal.
#
# Usage: ./kv-probe.sh [--host H] [--port P] [--model M]
set -uo pipefail

HOST="127.0.0.1"; PORT="11435"; MODEL="muse-glimmer:30b"
CTXS="4096 8192 16384 32768"
while [ $# -gt 0 ]; do
  case "$1" in
    --host)  HOST="$2"; shift 2 ;;
    --port)  PORT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --ctxs)  CTXS="$2"; shift 2 ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done
API="http://${HOST}:${PORT}"

printf '%-10s %14s %14s %14s\n' num_ctx total_GB vram_GB pct_gpu
RESULTS=""
for N in $CTXS; do
  TAG="muse-kvprobe-$N"
  curl -s -X POST "$API/api/create" -H "Content-Type: application/json" \
    -d "{\"model\":\"$TAG\",\"from\":\"$MODEL\",\"parameters\":{\"num_ctx\":$N},\"stream\":false}" >/dev/null

  # Load it. keep_alive is short so the next iteration is not fighting this one
  # for memory on a small box.
  curl -s -m 1800 -X POST "$API/api/chat" \
    -d "{\"model\":\"$TAG\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false,\"keep_alive\":\"60s\"}" >/dev/null

  LINE=$(curl -s "$API/api/ps" | python3 -c '
import sys,json
ms=json.load(sys.stdin).get("models",[])
if not ms: print("0 0 0"); raise SystemExit
m=ms[0]; t=m.get("size",0); v=m.get("size_vram",0)
print(t, v, (100*v/t if t else 0))
')
  set -- $LINE
  TOT="$1"; VRAM="$2"; PCT="$3"
  printf '%-10s %14.3f %14.3f %13.0f%%\n' "$N" \
    "$(python3 -c "print($TOT/1e9)")" "$(python3 -c "print($VRAM/1e9)")" "$PCT"
  RESULTS="$RESULTS$N $TOT
"
  curl -s -X POST "$API/api/delete" -H "Content-Type: application/json" -d "{\"model\":\"$TAG\"}" >/dev/null
done

echo
printf '%s' "$RESULTS" | python3 -c '
import sys
pts=[tuple(map(float,l.split())) for l in sys.stdin if l.strip()]
pts=[p for p in pts if p[1]>0]
if len(pts)<2: print("not enough successful loads to fit a slope"); raise SystemExit
# least squares on (num_ctx, total_bytes)
n=len(pts); sx=sum(p[0] for p in pts); sy=sum(p[1] for p in pts)
sxx=sum(p[0]*p[0] for p in pts); sxy=sum(p[0]*p[1] for p in pts)
slope=(n*sxy-sx*sy)/(n*sxx-sx*sx); inter=(sy-slope*sx)/n
print("fit: total_bytes = %.0f + %.1f * num_ctx"%(inter,slope))
print("  weights (intercept)      %.2f GB"%(inter/1e9))
print("  KV cost per token        %.0f bytes"%slope)
print("  SWA-aware prediction     13312 bytes/token  (13 full layers)")
print("  naive prediction         53248 bytes/token  (all 52 layers)")
d_swa=abs(slope-13312); d_naive=abs(slope-53248)
verdict="SWA HONOURED" if d_swa<d_naive else "NAIVE (full KV for all 52 layers)"
print("  -> %s"%verdict)
print("  implied KV at 131072     %.2f GB"%(slope*131072/1e9))
print("  implied total at 131072  %.2f GB"%((inter+slope*131072)/1e9))
'
