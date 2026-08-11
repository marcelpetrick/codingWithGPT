#!/usr/bin/env bash
# muse-bench.sh — the full Muse Glimmer evaluation on a remote Ollama host.
#
# Deliberately thin. The hard work — the seven agentic gates, the 16K context
# cliff probe, the throughput harness — was written and validated in
# ../ollamaClaudeCode_v1 and is model-agnostic, taking host and model as
# arguments. Reimplementing any of it here would mean re-earning trust in a
# second copy, so this drives the originals and adds only the two things Muse
# Glimmer has that nothing in v1 could test: vision, and the reasoning-effort
# dial.
#
# The preflight exists because the interesting failure here is not a crash. On
# Ollama < 0.32.8 the registry refuses the manifest with a 412 and nothing is
# installed, so every stage below would "run" against a model that is not there
# and report a wall of FAILs that look like model defects. Fail loudly, first.
#
# Usage:
#   ./muse-bench.sh                          # defaults to 192.168.100.67
#   ./muse-bench.sh --host 192.168.100.67
#   ./muse-bench.sh --host X --skip-pull     # model + variant already present
#   ./muse-bench.sh --host X --stage vision  # one stage only
set -uo pipefail

HOST="192.168.100.67"
PORT="11434"
BASE_TAG="muse-glimmer:30b"
VARIANT="muse-glimmer:30b-ctx128k-agentic"
NUM_CTX=131072
SKIP_PULL=0
STAGE="all"
V1="$(dirname "$(readlink -f "$0")")/../ollamaClaudeCode_v1"
OUT="$(dirname "$(readlink -f "$0")")/results"

while [ $# -gt 0 ]; do
  case "$1" in
    --host)      HOST="$2"; shift 2 ;;
    --port)      PORT="$2"; shift 2 ;;
    --variant)   VARIANT="$2"; shift 2 ;;
    --num-ctx)   NUM_CTX="$2"; shift 2 ;;
    --skip-pull) SKIP_PULL=1; shift ;;
    --stage)     STAGE="$2"; shift 2 ;;
    -h|--help)   sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

API="http://${HOST}:${PORT}"
mkdir -p "$OUT"
LOG="$OUT/run-$(date +%Y%m%d-%H%M%S).log"
say() { printf '\n\033[1m== %s\033[0m\n' "$*" | tee -a "$LOG"; }
note() { printf '   %s\n' "$*" | tee -a "$LOG"; }
run_stage() { [ "$STAGE" = "all" ] || [ "$STAGE" = "$1" ]; }

# ---------------------------------------------------------------- preflight --
say "preflight: $API"

VER=$(curl -s -m 5 "$API/api/version" | python3 -c 'import sys,json; print(json.load(sys.stdin)["version"])' 2>/dev/null)
if [ -z "$VER" ]; then
  note "FATAL: no Ollama answering at $API"; exit 1
fi
note "ollama $VER"

# The gate is per-model metadata, not a global policy: muse-glimmer's registry
# config carries "requires":"0.32.8". Every model previously pulled onto .67
# declared either nothing or 0.17.1, which is why pulls have always just worked
# until now. NVIDIA support landed in 0.32.8; 0.32.7 was Apple/MLX only, so
# 0.32.7 is not good enough on this box.
REQUIRED="0.32.8"
if [ "$(printf '%s\n%s\n' "$REQUIRED" "$VER" | sort -V | head -1)" != "$REQUIRED" ]; then
  cat <<EOF | tee -a "$LOG"

   FATAL: $HOST runs Ollama $VER, and muse-glimmer requires >= $REQUIRED.

   The registry refuses the manifest with HTTP 412 before transferring any
   weights, so nothing below can run. Fix it on the host itself:

       curl -fsSL https://ollama.com/install.sh | sh
       sudo systemctl restart ollama
       ollama --version      # expect >= $REQUIRED

   Then re-run this script.
EOF
  exit 1
fi

say "stage 1/7: pull and variant"
if [ "$SKIP_PULL" = "1" ]; then
  note "skipped by --skip-pull"
else
  note "pulling $BASE_TAG (~18 GB, downloaded by the server, not by us)"
  curl -s -X POST "$API/api/pull" -d "{\"model\":\"$BASE_TAG\"}" \
    | python3 -c '
import sys,json
last=""
for line in sys.stdin:
    try: d=json.loads(line)
    except Exception: continue
    if d.get("error"): print("   PULL ERROR:",d["error"]); raise SystemExit(1)
    if d.get("status")!=last: last=d["status"]; print("   ",last)
' | tee -a "$LOG" || exit 1

  # num_ctx MUST be baked in. /v1/messages — the endpoint Claude Code speaks —
  # has no num_ctx knob, so a bare tag silently caps at 16384 tokens and stops
  # emitting tool_use blocks with no error. Measured in v1/ctx-cliff.sh.
  # temperature 0 is v1/review2.md's reliability fix; presence_penalty 0 guards
  # against the vendor default that cost 35-53% of throughput there.
  note "creating $VARIANT (num_ctx=$NUM_CTX, temperature=0, presence_penalty=0)"
  curl -s -X POST "$API/api/create" -H "Content-Type: application/json" \
    -d "{\"model\":\"$VARIANT\",\"from\":\"$BASE_TAG\",
         \"parameters\":{\"num_ctx\":$NUM_CTX,\"temperature\":0,\"presence_penalty\":0},
         \"stream\":false}" | tee -a "$LOG"
  echo
fi

# ------------------------------------------------------- residency and KV ----
if run_stage residency; then
say "stage 2/7: residency and real KV cost"
# Touch the model so it loads, then read /api/ps. Two questions at once: does it
# sit fully on GPU, and does Ollama honour the 3:1 sliding-window pattern?
#   39 of 52 layers are sliding-window capped at 2048 tokens; only 13 are full.
#   SWA-aware KV @131072 = 13*1024*131072 + 39*1024*2048 = 1.83 GB
#   naive     KV @131072 = 52*1024*131072                = 6.98 GB
# Which one Ollama allocates decides whether q8_0 could ever have fit. It is the
# single measurement this whole document is waiting on.
curl -s -m 900 -X POST "$API/api/chat" \
  -d "{\"model\":\"$VARIANT\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false}" >/dev/null
curl -s "$API/api/ps" | python3 -c '
import sys,json
for m in json.load(sys.stdin).get("models",[]):
    tot=m.get("size",0); vram=m.get("size_vram",0)
    pct=100*vram/tot if tot else 0
    print("   %-42s total %.2f GB  vram %.2f GB  (%.0f%% GPU)"%(m["name"],tot/1e9,vram/1e9,pct))
    if pct<99.5: print("   WARNING: not fully resident on GPU — expect a throughput cliff")
    w=18.16
    print("   implied KV+overhead: %.2f GB   (SWA-aware predicts 1.83, naive predicts 6.98)"%(tot/1e9-w))
' | tee -a "$LOG"
fi

# ------------------------------------------------------------ context cliff --
if run_stage cliff; then
say "stage 3/7: the 16K context cliff"
note "bare tag is EXPECTED to cap ~16386 with tool_use=NO; the variant must not"
"$V1/ctx-cliff.sh" "$BASE_TAG" "$VARIANT" 2>&1 | tee -a "$LOG"
fi

# ----------------------------------------------------------- agentic gates ---
if run_stage agentic; then
say "stage 4/7: seven agentic gates"
"$V1/agentic-test.sh" "$HOST" "$VARIANT" "$OUT/agentic" 2>&1 | tee -a "$LOG"
fi

# ---------------------------------------------------------------- throughput -
if run_stage throughput; then
say "stage 5/7: throughput"
# The incumbent is measured at 131.5 tok/s. Muse Glimmer is dense at 16.76 GB,
# so bandwidth arithmetic predicts ~25-32 tok/s. This stage replaces that
# estimate with a number; delete the estimate from muse_ollama.md once it does.
# -dflash is the one variable with real upside, so measure it in the same run.
"$V1/benchmark.sh" --host "$HOST" \
  --models "$VARIANT,qwen3.6:35b-a3b-q4_K_M-agentic" \
  --profile S 2>&1 | tee -a "$LOG"
fi

# -------------------------------------------------------------------- vision -
if run_stage vision; then
say "stage 6/7: vision"
# Nothing in v1 tests this because nothing on the farm could do it. Uses an
# image already in the repo so the test is reproducible and needs no network.
IMG="$(dirname "$(readlink -f "$0")")/../ollamaClaudeCode_v0/failingOutput.png"
if [ ! -f "$IMG" ]; then
  note "SKIP: no test image at $IMG"
else
  note "describing $(basename "$IMG") ($(du -h "$IMG" | cut -f1))"
  python3 - "$API" "$VARIANT" "$IMG" <<'PY' 2>&1 | tee -a "$LOG"
import base64,json,sys,urllib.request,time
api,model,img=sys.argv[1],sys.argv[2],sys.argv[3]
b64=base64.b64encode(open(img,'rb').read()).decode()
body=json.dumps({"model":model,"stream":False,
  "messages":[{"role":"user","content":"Describe this screenshot. What is it showing, and is anything failing?","images":[b64]}]}).encode()
t=time.time()
try:
    r=json.load(urllib.request.urlopen(urllib.request.Request(api+"/api/chat",body,{"Content-Type":"application/json"}),timeout=900))
except Exception as e:
    print("   VISION FAIL:",str(e)[:200]); raise SystemExit
txt=(r.get("message") or {}).get("content","")
print("   %.1fs, %d chars"%(time.time()-t,len(txt)))
print("   VISION",("PASS" if len(txt.strip())>80 else "FAIL — response too short to be a real description"))
print("   ---\n  ",txt[:600].replace("\n","\n   "))
PY
fi
fi

# ---------------------------------------------------------- reasoning effort -
if run_stage reasoning; then
say "stage 7/7: reasoning effort (low / medium / high / xhigh)"
# The model card advertises four levels. What is unknown is how Ollama plumbs
# them and what each costs, which decides whether the dial is usable per-task or
# has to be baked into four separate variants like num_ctx was.
for LVL in low medium high xhigh; do
  python3 - "$API" "$VARIANT" "$LVL" <<'PY' 2>&1 | tee -a "$LOG"
import json,sys,time,urllib.request
api,model,lvl=sys.argv[1],sys.argv[2],sys.argv[3]
q="A repo has a flaky test that fails 1 in 20 runs only in CI. Outline how you would isolate the cause."
body=json.dumps({"model":model,"stream":False,"think":lvl,
  "messages":[{"role":"user","content":q}]}).encode()
t=time.time()
try:
    r=json.load(urllib.request.urlopen(urllib.request.Request(api+"/api/chat",body,{"Content-Type":"application/json"}),timeout=900))
except Exception as e:
    print("   %-6s ERROR %s"%(lvl,str(e)[:110])); raise SystemExit
m=r.get("message") or {}
th=len(m.get("thinking") or "")
ec=r.get("eval_count",0); ed=r.get("eval_duration",1) or 1
print("   %-6s %6.1fs  thinking=%-6d answer=%-5d  %.1f tok/s"%(
      lvl,time.time()-t,th,ec,ec/(ed/1e9)))
PY
done
note "if all four rows show thinking=0 and identical timing, the dial is not plumbed"
fi

say "done — transcript: $LOG"
