#!/usr/bin/env bash
# p7-chain.sh -- P7 as one sequential chain: download Q8_0, verify, merge the LoRA in place,
# upload as qwen3.8-pi:27b-q8-ctx64k-nothink, run the arm (v6-q8.sh), regenerate the report.
# Idempotent: each step has a marker in /var/tmp/v6. Deletes nothing on the box.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; W=/var/tmp/v6; PY="$HOME/.cache/v6-venv/bin/python"
Q8="$W/Qwen3.8-27B-Q8_0.gguf"; LORA="$W/Qwen3.8-27B-pi-lora-F16.gguf"
Q8_SHA=6bc9e7220d8400574fd62df25f04a961cb5cbb0d766cf0118c21c36c0059c35a
LORA_SHA=a64f91844f19e67da500d8628bdf9383aa334e61b7ab687805802e7d272d7b67
URL=https://huggingface.co/ggml-org/Qwen3.8-27B-GGUF/resolve/main/Qwen3.8-27B-Q8_0.gguf
LOG="$HERE/results/build.log"
say () { printf '[%s] p7: %s\n' "$(date +%T)" "$*" | tee -a "$LOG"; }
trap 'say "FAILED at line $LINENO"; timeout 5 notify-send "v6 P7 failed" "$LOG" 2>/dev/null || true' ERR
cd "$HERE"
echo "$LORA_SHA  $LORA" | sha256sum -c --quiet -
# Markers without the Q8_0 file are stale (the file was deleted to free /): start from the download.
[ -f "$Q8" ] || rm -f "$W/.q8-verified" "$W/.merge-started" "$W/.merged"
df -B1 --output=avail "$W" | tail -1 | awk '{exit !($1 > 31e9)}' || [ -f "$Q8" ] || { say "STOPPED: need 31 GB free on $W"; exit 5; }
# A half-merged file must never be merged again (the delta would be added twice).
[ -e "$W/.merge-started" ] && [ ! -e "$W/.merged" ] && { say "STOPPED: interrupted merge; delete $Q8 and the markers"; exit 4; }
if [ ! -e "$W/.merged" ]; then
  if [ ! -e "$W/.q8-verified" ]; then
    say "download Q8_0 (28.6 GB)"
    curl -fsSL -C - --retry 5 --retry-delay 30 -o "$Q8" "$URL"
    say "verify Q8_0 sha256"
    echo "$Q8_SHA  $Q8" | sha256sum -c --quiet -; touch "$W/.q8-verified"
  fi
  say "merge LoRA in place"; touch "$W/.merge-started"
  "$PY" -I "$HERE/merge_lora_inplace.py" "$Q8" "$LORA" >>"$LOG" 2>&1; touch "$W/.merged"
  say "merged"
fi
./publish_q8.sh
./v6-q8.sh
python3 ../ollamaClaudeCode_v4_tielCoder/refresh-compare.py --arm pi1118q8 >"results/refresh-pi1118q8.md" 2>&1 || true
python3 make_report.py >>"$LOG" 2>&1 || true
say "P7-CHAIN-END"
timeout 5 notify-send "v6 P7 done" "$LOG" 2>/dev/null || true
