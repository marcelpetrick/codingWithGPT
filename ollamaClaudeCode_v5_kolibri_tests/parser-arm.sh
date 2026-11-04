#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Test Ollama's Qwen3 thinking parser with Kolibri's XML tool-call format.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model='kolibri1:q3ks-ctx147456-qwen3parser-ab'
exec 8>results/parser-arm.lock
flock -n 8 || { echo 'Another parser arm is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri parser-arm test finished" "Exit status: $rc. See results/parser-arm.log." 2>/dev/null || true' EXIT
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
curl --noproxy '*' -fsS -m 10 "$base/api/tags" | python3 -c 'import json,sys; assert not any(m["name"].lower()==sys.argv[1].lower() for m in json.load(sys.stdin)["models"]), "Target tag exists"' "$model"
python3 - "$model" <<'PY'
import json,sys
from pathlib import Path
body={'model':sys.argv[1], 'from':'kolibri1:q3ks-ctx147456-nothink-ab', 'parser':'qwen3-thinking', 'stream':False}
Path('results/parser-arm-create.json').write_text(json.dumps(body)+'\n')
PY
curl --noproxy '*' -fsS -m 120 "$base/api/create" -H 'Content-Type: application/json' --data-binary @results/parser-arm-create.json | python3 -c 'import json,sys; assert json.load(sys.stdin).get("status") == "success"'
curl --noproxy '*' -fsS -m 10 "$base/api/show" -H 'Content-Type: application/json' --data "{\"model\":\"$model\"}" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("parser")=="qwen3-thinking", "Parser not set"; assert "num_ctx                        147456" in d.get("parameters", ""), "Context not set"'
./gate-reliability.sh "$model" parser-arm
