#!/usr/bin/env bash
# run_long.sh: the long run on the laptop, as one sequential chain (no parallel jobs).
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  setsid nohup systemd-inhibit --what=sleep:idle --why="mvo long run" \
#           scripts/run_long.sh >> results/long_run.log 2>&1 &
# Cells:  A:4096,A:16384,B:1024,B:8192 with n = 5, then C:4096 and V:4096 with n = 1 (greedy).
# Order:  Qwen3.5 2B (Magnitude vs Ollama plain, then vs Ollama MTP); then Gemma 4 E4B, the model
#         that fills the 8 GB GPU (downloads first, after a free-space check).
# Idempotent: re-running resumes; existing rows are skipped; downloads skip installed models.
# Exit:   2 when a pair stops (engine unreachable or load failed) or the disk is too full.
set -uo pipefail
cd "$(dirname "$0")/.."

pair() {  # pair MAG_ARM MAG_MODEL OLL_ARM OLL_MODEL
  local cells reps rc
  for spec in "A:4096,A:16384,B:1024,B:8192 5" "C:4096 1" "V:4096 1"; do
    cells=${spec% *} reps=${spec#* }
    scripts/run_pair.sh laptop "$cells" "$reps" "$@"; rc=$?
    [ "$rc" -eq 2 ] && { echo "STOP: run_pair exit 2"; exit 2; }
  done
  return 0
}

need_gb() {  # need_gb GB: stop when /home has less free space
  local free
  free=$(df -BG --output=avail /home | tail -1 | tr -dc 0-9)
  [ "$free" -ge "$1" ] || { echo "STOP: only ${free} GB free on /home"; exit 2; }
}

Q=hf:unsloth/Qwen3.5-2B-GGUF/Qwen3.5-2B-Q4_K_M.gguf
pair magnitude-qwen2b "$Q" ollama-qwen2b qwen3.5:2b-q4_K_M
pair magnitude-qwen2b "$Q" ollama-qwen2b-mtp qwen3.5:2b-mtp-q4_K_M

E4B=gemma-4-e4b-it-qat:gguf:q4
need_gb 20
echo "== $(date -Is) download Gemma 4 E4B (both engines)"
ollama pull gemma4:e4b-it-qat >/dev/null 2>&1 || { echo "STOP: ollama pull failed"; exit 2; }
magnitude catalog pull "$E4B" >/dev/null 2>&1
for _ in $(seq 1 360); do
  st=$(magnitude models status "$E4B" 2>&1)
  echo "$st" | grep -q 'Installation *Installed' && break
  echo "$st" | grep -q -i 'failed' && { echo "STOP: Magnitude download failed"; exit 2; }
  sleep 10
done
pair magnitude-gemma-e4b "$E4B" ollama-gemma-e4b gemma4:e4b-it-qat
echo "LONG RUN DONE $(date -Is)"
