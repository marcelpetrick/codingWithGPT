#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Run the v4 retrieval ladder with stricter transport and empty-response checks.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model='kolibri1:q3ks-ctx147456-nothink-ab'
out='results/needle-nothink'
mkdir -p "$out/results"
exec 9>results/needle.lock
flock -n 9 || { echo 'Another needle test is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri retrieval test finished" "Exit status: $rc. See results/needle-nothink.log." 2>/dev/null || true' EXIT
[[ ! -e "$out/results/needle-v2.raw.jsonl" ]] || { echo 'Existing results; review before retrying.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
cp ../ollamaClaudeCode_v4_tielCoder/needle-v2.sh ../ollamaClaudeCode_v4_tielCoder/lib-preflight.sh "$out/"
python3 - "$out/needle-v2.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
changes=[('set -uo pipefail','set -euo pipefail'),('local R; R=$(curl -s --max-time "$TIMEOUT"','local R; R=$(curl -fsS --max-time "$TIMEOUT"'),("except Exception: print('  %-6s PARSE_FAIL'%lbl); raise SystemExit", "except Exception: raise SystemExit('invalid response')"),("if d.get('error'): print('  %-6s ERROR %s'%(lbl,str(d['error'])[:70])); raise SystemExit", "if d.get('error'): raise SystemExit('server error: '+str(d['error']))"),("ans=(d.get('message') or {}).get('content','') or ''", "ans=(d.get('message') or {}).get('content','') or ''\nif not ans.strip(): raise SystemExit('empty answer')")]
for old,new in changes:
    assert s.count(old)==1, old
    s=s.replace(old,new)
p.write_text(s)
PY
NO_PROXY='*' no_proxy='*' bash "$out/needle-v2.sh" --model "$model" --num-predict 2048 --depths '2700 10700 40000 80000'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"], "GPU spill"; print("Final resident context:",m[0]["context_length"])' "$model"
curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
