#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Wait for the adaptive T1 retry, then run paired English and German prompts.
set -euo pipefail
cd "$(dirname "$0")"
exec 8>results/bilingual.lock
flock -n 8 || { echo 'Another bilingual probe is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri bilingual probe finished" "Exit status: $rc. See results/bilingual.log." 2>/dev/null || true' EXIT
mode="${1:-after-thinking}"
case "$mode" in
  after-thinking)
    exec 9>results/thinking.lock
    flock 9
    [[ -f results/t1-adaptive/results/gate-rerun.raw.jsonl ]] || { echo 'Adaptive T1 results missing.' >&2; exit 1; }
    [[ $(wc -l < results/t1-adaptive/results/gate-rerun.raw.jsonl) -eq 8 ]] || { echo 'Adaptive T1 stage is incomplete.' >&2; exit 1; }
    ;;
  after-raw)
    exec 9>results/raw-diagnostic.lock
    flock 9
    python3 -c 'import json; d=json.load(open("results/raw-diagnostic/response.json")); assert d.get("done") and d.get("response"), "Raw diagnostic is incomplete"'
    ;;
  *) echo 'Use after-thinking or after-raw.' >&2; exit 1 ;;
esac
python3 -u bilingual.py
