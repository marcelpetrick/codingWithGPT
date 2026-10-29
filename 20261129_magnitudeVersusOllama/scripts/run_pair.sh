#!/usr/bin/env bash
# run_pair.sh: measure one Magnitude arm and one Ollama arm, one engine on the GPU at a time.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/run_pair.sh SITE CELLS REPS MAG_ARM MAG_MODEL OLLAMA_ARM OLLAMA_MODEL
#   e.g.  scripts/run_pair.sh laptop-quick A:4096,B:1024 3 \
#           magnitude-gemma-e2b gemma-4-e2b-it-qat:gguf:q4 ollama-gemma-e2b gemma4:e2b-it-qat
# Steps:  unload Ollama -> load the Magnitude model -> mvo run -> stop it ->
#         mvo run for Ollama -> unload Ollama -> mvo report.
# Idempotent: mvo run skips rows that exist, so a re-run resumes.
# Exit:   0 done; 1 rows failed; 2 an engine stopped the run (unreachable or load failed).
set -uo pipefail
cd "$(dirname "$0")/.."
[ $# -eq 7 ] || { sed -n 4,6p "$0"; exit 1; }
site=$1 cells=$2 reps=$3 mag_arm=$4 mag_model=$5 oll_arm=$6 oll_model=$7
MVO=.venv/bin/mvo
rc=0

vram() { nvidia-smi --query-gpu=memory.used --format=csv,noheader; }
unload_ollama() {
  curl -s -m 60 http://127.0.0.1:11434/api/generate -d "{\"model\":\"$oll_model\",\"keep_alive\":0}" >/dev/null
}

echo "== $(date -Is) unload Ollama; VRAM $(vram)"
unload_ollama
echo "== $(date -Is) load Magnitude $mag_model"
magnitude models load "$mag_model" >/dev/null || exit 2
for _ in $(seq 1 120); do
  magnitude models status "$mag_model" | grep -q 'Runtime *Ready' && break
  sleep 5
done
magnitude models status "$mag_model" | grep -q 'Runtime *Ready' || { echo "Magnitude did not load"; exit 2; }
echo "== $(date -Is) Magnitude ready; VRAM $(vram)"
$MVO run --site "$site" --arm "$mag_arm" --cells "$cells" --reps "$reps" || rc=$?
[ "$rc" -eq 2 ] && exit 2
magnitude models stop "$mag_model" >/dev/null
sleep 5
echo "== $(date -Is) Magnitude stopped; VRAM $(vram)"
$MVO run --site "$site" --arm "$oll_arm" --cells "$cells" --reps "$reps" || rc=$?
unload_ollama
echo "== $(date -Is) Ollama unloaded; VRAM $(vram)"
$MVO report
exit "$rc"
