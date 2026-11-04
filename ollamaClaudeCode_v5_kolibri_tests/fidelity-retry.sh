#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Recheck v4 T10 eight times and capture the complete API responses.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model='kolibri1:q3ks-ctx147456-nothink-ab'
out='results/fidelity'
mkdir -p "$out/results"
exec 8>results/fidelity.lock
flock -n 8 || { echo 'Another fidelity retry is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri fidelity retry finished" "Exit status: $rc. See results/fidelity.log." 2>/dev/null || true' EXIT
exec 9>results/deep.lock
flock 9
[[ -f results/deep/kolibri1/kolibri1_q3ks-ctx147456-nothink-ab.tsv ]] || { echo 'Deep gates are incomplete.' >&2; exit 1; }
[[ -f results/deep/qwen3.6/qwen3.6_35b-a3b-q4_K_M-agentic.tsv ]] || { echo 'Control deep gates are incomplete.' >&2; exit 1; }
[[ ! -e "$out/results/gate-extra.raw.jsonl" ]] || { echo 'Existing fidelity results; review before restarting.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
cp ../ollamaClaudeCode_v4_tielCoder/gate-extra.py "$out/gate-extra.py"
python3 - "$out/gate-extra.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='d.get("content", [])'; new='(d.get("content") or [])'
assert s.count(old)==2
s=s.replace(old,new)
old='''        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)'''
new='''        with urllib.request.urlopen(req, timeout=timeout) as r:
            response = json.load(r)
        with (HERE / "results" / "api.raw.jsonl").open("a") as log:
            log.write(json.dumps({"path": path, "body": body, "response": response}) + "\\n")
        return response'''
assert s.count(old)==1
s=s.replace(old,new)
old='                verdicts.append(v)'; new='                if v == "ERROR":\n                    raise SystemExit("gate transport error: " + detail)\n                verdicts.append(v)'
assert s.count(old)==1
p.write_text(s.replace(old,new))
PY
NO_PROXY='*' no_proxy='*' python3 -u "$out/gate-extra.py" --n 8 --gate T10_argument_fidelity "$model"
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"], "GPU spill"' "$model"
curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
