#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Repeat v4 T1 or T5 eight times with strict scoring and raw responses.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model="${1:?Pass the exact model tag}"
label="${2:?Pass a result label}"
gate="${3:-T1}"
[[ "$model" =~ ^[A-Za-z0-9._:/-]+$ ]] || { echo 'Invalid model tag.' >&2; exit 1; }
[[ "$gate" == T1 || "$gate" == T5 ]] || { echo 'Use T1 or T5.' >&2; exit 1; }
[[ "$label" =~ ^[a-z0-9_-]+$ ]] || { echo 'Invalid result label.' >&2; exit 1; }
out="results/${gate,,}-$label"
mkdir -p "$out/results"
exec 9>results/t1.lock
flock -n 9 || { echo 'Another gate run is active.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri tool gate finished" "Exit status: $rc. See the gate log." 2>/dev/null || true' EXIT
[[ ! -e "$out/results/gate-rerun.raw.jsonl" ]] || { echo 'Existing result; review before retrying.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert not m or (len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower()), "Server is busy"' "$model"
cp ../ollamaClaudeCode_v4_tielCoder/gate-rerun.py "$out/gate-rerun.py"
cp gate_score.py "$out/gate_score.py"
python3 patch_v4_gate.py "$out/gate-rerun.py"
python3 -u "$out/gate-rerun.py" --n 8 --gate "$gate" "$model"
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"] and m[0]["context_length"]>=147456, "Unexpected spill or context"' "$model"
curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
