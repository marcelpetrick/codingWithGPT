#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Inspect raw generation for a T1-shaped prompt without the chat tool parser.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model='kolibri1:q3ks-ctx147456-nothink-ab'
mkdir -p results/raw-diagnostic
exec 9>results/raw-diagnostic.lock
flock -n 9 || { echo 'Another raw diagnostic is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri raw diagnostic finished" "Exit status: $rc. See results/raw-diagnostic.log." 2>/dev/null || true' EXIT
[[ ! -e results/raw-diagnostic/response.json ]] || { echo 'Existing diagnostic; review before retrying.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
python3 - "$model" <<'PY'
import json,sys
from pathlib import Path
tool={"type":"function","function":{"name":"write_file","description":"Write content to a file","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}}
prompt=("<|im_start|>system\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n"+json.dumps(tool)+"\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call><|im_end|>\n<|im_start|>user\nWrite hello world to /tmp/test.txt<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n")
body={"model":sys.argv[1],"prompt":prompt,"raw":True,"stream":False,"options":{"temperature":0,"seed":42,"num_predict":512}}
Path('results/raw-diagnostic/request.json').write_text(json.dumps(body,indent=2)+'\n')
PY
curl --noproxy '*' -fsS -m 1800 "$base/api/generate" -H 'Content-Type: application/json' --data-binary @results/raw-diagnostic/request.json >results/raw-diagnostic/response.json
python3 - <<'PY'
import json
from pathlib import Path
d=json.loads(Path('results/raw-diagnostic/response.json').read_text())
if not d.get('done') or not d.get('response','').strip() or not d.get('prompt_eval_count'):
    raise SystemExit('Incomplete or empty raw response')
print('Raw response:',repr(d['response']))
PY
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"] and m[0]["context_length"]>=147456, "Spill or wrong context"' "$model"
curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
