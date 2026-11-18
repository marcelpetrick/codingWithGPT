#!/usr/bin/env bash
# build.sh -- make the two Ollama tags of round v6 from the Q8_0 base and the pi LoRA.
#
#   base arm: Q8_0 -> Q4_K_M                     -> qwen3.8-base:27b-q4km-ctx200k-nothink
#   pi arm:   Q8_0 + LoRA (in place) -> Q4_K_M   -> qwen3.8-pi:27b-q4km-ctx200k-nothink
#
# Both arms go through the same requantization, so the only difference is the adapter.
# Idempotent: every step leaves a marker in $WORK and a re-run skips it.
# Disk: the Q8_0 lives on / ($WORK), each Q4_K_M lives on /home ($OUT) only until it is uploaded.
# Usage: setsid nohup systemd-inhibit --what=sleep:idle ./build.sh >/dev/null 2>&1 & disown
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
HOST=192.168.100.67; BASE="http://$HOST:11434"
WORK=/var/tmp/v6; OUT="$HOME/.cache/v6-out"; mkdir -p "$OUT"
Q8="$WORK/Qwen3.8-27B-Q8_0.gguf"
Q8_SHA=6bc9e7220d8400574fd62df25f04a961cb5cbb0d766cf0118c21c36c0059c35a
LORA="${LORA:-/var/tmp/v6/Qwen3.8-27B-pi-lora-F16.gguf}"
LORA_SHA=a64f91844f19e67da500d8628bdf9383aa334e61b7ab687805802e7d272d7b67
QUANT="$HOME/.cache/v6-llamacpp/build/bin/llama-quantize"
PY="$HOME/.cache/v6-venv/bin/python"
LOG="$HERE/results/build.log"; mkdir -p "$HERE/results"
export NO_PROXY="$HOST,${NO_PROXY:-}" no_proxy="$HOST,${no_proxy:-}"
say () { printf '[%s] %s\n' "$(date +%T)" "$*" | tee -a "$LOG"; }
trap 'say "BUILD FAILED at line $LINENO"' ERR
done_ () { [ -e "$WORK/.$1" ]; }
mark () { touch "$WORK/.$1"; }

curl -sf -m 10 "$BASE/api/version" >/dev/null || { say "STOPPED: server unreachable"; exit 3; }

if ! done_ q8-verified; then
  say "verify Q8_0 sha256"
  echo "$Q8_SHA  $Q8" | sha256sum -c --quiet - && mark q8-verified
fi
echo "$LORA_SHA  $LORA" | sha256sum -c --quiet -

publish () {  # <tag> <q4 file>: upload the blob and create the tag
  local tag="$1" f="$2" sha
  sha="$(sha256sum "$f" | cut -d' ' -f1)"
  say "$tag: blob sha256:$sha"
  if [ "$(curl -s -o /dev/null -w '%{http_code}' -I "$BASE/api/blobs/sha256:$sha")" != 200 ]; then
    say "$tag: upload $(du -h "$f" | cut -f1)"
    curl -sf -T "$f" -X POST "$BASE/api/blobs/sha256:$sha" >/dev/null
  fi
  "$PY" -I - "$BASE" "$tag" "$sha" "$HERE/templates/qwen38-nothink.gotmpl" <<'EOF' | tee -a "$LOG"
import json, sys, urllib.request
base, tag, sha, tmpl = sys.argv[1:5]
body = {"model": tag, "files": {"model.gguf": "sha256:" + sha},
        "template": open(tmpl).read(), "parser": "qwen3-coder",
        "parameters": {"num_ctx": 200000, "temperature": 0.8, "top_p": 0.95, "top_k": 20,
                       "min_p": 0, "presence_penalty": 0, "repeat_penalty": 1,
                       "stop": ["<|im_end|>", "<|im_start|>"]},
        "stream": False}
r = urllib.request.urlopen(urllib.request.Request(base + "/api/create", json.dumps(body).encode()), timeout=1800)
out = r.read().decode()
print(tag, out.strip()[-200:])
sys.exit(0 if '"success"' in out else 1)
EOF
}

# 1. base arm
if ! done_ base-published; then
  [ -s "$OUT/base-Q4_K_M.gguf" ] && done_ base-quantized || {
    say "quantize base Q8_0 -> Q4_K_M"
    "$QUANT" --allow-requantize "$Q8" "$OUT/base-Q4_K_M.gguf" Q4_K_M >>"$LOG" 2>&1; mark base-quantized; }
  publish qwen3.8-base:27b-q4km-ctx200k-nothink "$OUT/base-Q4_K_M.gguf"
  mark base-published; rm -f "$OUT/base-Q4_K_M.gguf"; say "base arm published, local Q4 removed"
fi

# A half-merged file must never be merged again: that would add the delta twice.
done_ merge-started && ! done_ merged && { say "STOPPED: a merge was interrupted; download the Q8_0 again"; exit 4; }
# 2. merge the LoRA into the Q8_0, in place (the Q8_0 is no longer the base after this)
if ! done_ merged; then
  say "merge LoRA dry run"
  "$PY" -I "$HERE/merge_lora_inplace.py" "$Q8" "$LORA" --dry-run 2>&1 | tail -1 | tee -a "$LOG"
  say "merge LoRA in place"
  mark merge-started
  "$PY" -I "$HERE/merge_lora_inplace.py" "$Q8" "$LORA" 2>&1 | tail -3 | tee -a "$LOG"
  mark merged
fi

# 3. pi arm
if ! done_ pi-published; then
  [ -s "$OUT/pi-Q4_K_M.gguf" ] && done_ pi-quantized || {
    say "quantize merged Q8_0 -> Q4_K_M"
    "$QUANT" --allow-requantize "$Q8" "$OUT/pi-Q4_K_M.gguf" Q4_K_M >>"$LOG" 2>&1; mark pi-quantized; }
  publish qwen3.8-pi:27b-q4km-ctx200k-nothink "$OUT/pi-Q4_K_M.gguf"
  mark pi-published; rm -f "$OUT/pi-Q4_K_M.gguf"; say "pi arm published, local Q4 removed"
fi
say "BUILD-DONE"
timeout 5 notify-send "v6 build done" "both tags on .67" 2>/dev/null || true
