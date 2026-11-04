#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Run the unchanged v4 T1 tool gate once against the baked Kolibri tag.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model="${1:-kolibri1:q3ks-ctx147456-agentic}"
label="${2:-stock}"
[[ "$model" =~ ^[A-Za-z0-9._:/-]+$ ]] || { echo 'Invalid model tag.' >&2; exit 1; }
[[ "$label" =~ ^[a-z0-9_-]+$ ]] || { echo 'Invalid result label.' >&2; exit 1; }
out="results/v4-smoke-$label"
mkdir -p "$out/results"
exec 9>results/v4-smoke.lock
flock -n 9 || { echo 'The smoke test is already running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri tool smoke test finished" "Exit status: $rc. See results/v4-smoke.log." 2>/dev/null || true' EXIT
[[ ! -e $out/results/gate-rerun.raw.jsonl ]] || { echo 'Existing smoke result; review before retrying.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
cp ../ollamaClaudeCode_v4_tielCoder/gate-rerun.py "$out/gate-rerun.py"
cp gate_score.py "$out/gate_score.py"
python3 patch_v4_gate.py "$out/gate-rerun.py"
python3 -u "$out/gate-rerun.py" --n 1 --gate T1 "$model"
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; models=json.load(sys.stdin)["models"]; assert len(models)==1 and models[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; m=models[0]; assert m["size_vram"]>=m["size"] and m["context_length"]>=147456, "Unexpected spill or context"' "$model"
curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
