#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Inspect one native Ollama chat tool call at temperature zero.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model='kolibri1:q3ks-ctx147456-nothink-ab'
mkdir -p results/native-tool
exec 9>results/native-tool.lock
flock -n 9 || { echo 'Another native-tool probe is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri native tool probe finished" "Exit status: $rc. See results/native-tool.log." 2>/dev/null || true' EXIT
[[ ! -e results/native-tool/response.json ]] || { echo 'Existing response; review before retrying.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
python3 - "$model" <<'PY'
import json,sys
from pathlib import Path
tool={"type":"function","function":{"name":"write_file","description":"Write content to a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}}
body={"model":sys.argv[1],"messages":[{"role":"user","content":"Write hello world to /tmp/test.txt"}],"tools":[tool],"think":False,"stream":False,"options":{"temperature":0,"seed":42,"num_predict":512}}
Path('results/native-tool/request.json').write_text(json.dumps(body,indent=2)+'\n')
PY
curl --noproxy '*' -fsS -m 1800 "$base/api/chat" -H 'Content-Type: application/json' --data-binary @results/native-tool/request.json >results/native-tool/response.json
python3 - <<'PY'
import json
from pathlib import Path
d=json.loads(Path('results/native-tool/response.json').read_text())
m=d.get('message') or {}
if not d.get('done') or not (m.get('content') or m.get('tool_calls')) or not d.get('prompt_eval_count'):
    raise SystemExit('Incomplete or empty native response')
print('Native response:',json.dumps(m,ensure_ascii=False))
PY
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"] and m[0]["context_length"]>=147456, "Spill or wrong context"' "$model"
curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
