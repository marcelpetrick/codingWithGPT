#!/usr/bin/env bash
# s16-extra.sh -- dense candidates, added 11-02 on the owner's list. Same arm, rule and harness as s15.
# The earlier decisions rejected dense models for speed; this round ranks correctness first.
# The owner fixed their window at 200k (num_ctx 200000), the Claude Code cap here; the main field stays baked at 262144.
# Waits for s15, pulls and bakes, then runs s15 on these tags only. Idempotent. Deletes nothing.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")"
HOST=192.168.100.67; BASE="http://$HOST:11434"; LOG=results/s16-extra.log
export NO_PROXY="$HOST,${NO_PROXY:-}" no_proxy="$HOST,${no_proxy:-}"
say () { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }
while pgrep -f '^bash \./s15-refresh\.sh|^/usr/bin/env bash \./s15-refresh\.sh|[ /]s15-refresh\.sh$' | grep -qv "^$$\$"; do sleep 30; done
curl -s -m 10 "$BASE/api/version" >/dev/null || { say "STOPPED: server unreachable"; exit 3; }
exists () { curl -s -m 10 "$BASE/api/show" -d "{\"name\":\"$1\"}" | grep -q '"modelfile"'; }
pull () { exists "$1" && return 0; say "pull $1"; curl -s -m 3600 "$BASE/api/pull" -d "{\"name\":\"$1\",\"stream\":false}" | grep -q '"status":"success"'; }
bake () {  # <tag> <from> <parameters>
  exists "$1" && return 0
  curl -s -m 600 "$BASE/api/create" -d "{\"model\":\"$1\",\"from\":\"$2\",\"parameters\":{$3},\"stream\":false}" | grep -q '"status":"success"' \
    || say "bake failed: $1"
}
pull qwen3.6:27b || say "pull failed: qwen3.6:27b"
pull gemma4:31b || say "pull failed: gemma4:31b"
bake qwen3.8:27b-q4_K_M-ctx200k-agentic qwen3.8:27b-q4_K_M-ctx128k-agentic '"num_ctx":200000'
bake qwen3.6-27b:q4km-ctx200k-agentic qwen3.6:27b '"num_ctx":200000,"presence_penalty":0'
bake gemma4:31b-ctx200k-agentic gemma4:31b '"num_ctx":200000,"presence_penalty":0'
for t in qwen3.8:27b-q4_K_M-ctx200k-agentic qwen3.6-27b:q4km-ctx200k-agentic gemma4:31b-ctx200k-agentic; do
  say "$t: $(curl -s -m 10 "$BASE/api/show" -d "{\"name\":\"$t\"}" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("details",{}).get("quantization_level"),d.get("details",{}).get("family"))')"
done
MODELS_OVERRIDE="qwen3.8:27b-q4_K_M-ctx200k-agentic qwen3.6-27b:q4km-ctx200k-agentic gemma4:31b-ctx200k-agentic" RUNS=3 ./s15-refresh.sh
say "S16-EXTRA-END exit $?"
