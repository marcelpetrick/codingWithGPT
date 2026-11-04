#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Run v4 tool gates on Kolibri and the control after the retrieval stages.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
out='results/agentic-battery'
mkdir -p "$out/results"
exec 8>results/battery.lock
flock -n 8 || { echo 'Another agentic battery is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri tool battery finished" "Exit status: $rc. See results/battery.log." 2>/dev/null || true' EXIT
exec 9>results/near-limit.lock
flock 9
grep -q '^=== finished ===$' results/needle-near/results/needle-v2.log || { echo 'Near-limit retrieval did not finish.' >&2; exit 1; }
[[ ! -e "$out/results/gate-rerun.raw.jsonl" && ! -e "$out/results/gate-extra.raw.jsonl" ]] || { echo 'Existing gate results; review before restarting.' >&2; exit 1; }
cp ../ollamaClaudeCode_v4_tielCoder/gate-rerun.py ../ollamaClaudeCode_v4_tielCoder/gate-extra.py "$out/"
cp gate_score.py "$out/gate_score.py"
python3 patch_v4_gate.py "$out/gate-rerun.py"
python3 - "$out" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'gate-extra.py'; s=p.read_text(); old='d.get("content", [])'; new='(d.get("content") or [])'
assert s.count(old)==2
p.write_text(s.replace(old,new))
p=root/'gate-extra.py'; s=p.read_text()
old_post='''        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)'''
new_post='''        with urllib.request.urlopen(req, timeout=timeout) as r:
            response = json.load(r)
        with (HERE / "results" / "api.raw.jsonl").open("a") as log:
            log.write(json.dumps({"path": path, "body": body, "response": response}) + "\\n")
        if (path == "/v1/messages" and not response.get("content")) or (path == "/api/chat" and not (response.get("message") or {}).get("content")):
            return {"error": "empty API content"}
        return response'''
assert s.count(old_post)==1
s=s.replace(old_post,new_post)
old='                verdicts.append(v)'; new='                if v == "ERROR":\n                    raise SystemExit("gate transport error: " + detail)\n                verdicts.append(v)'
assert s.count(old)==1
p.write_text(s.replace(old,new))
PY
for model in kolibri1:q3ks-ctx147456-nothink-ab qwen3.6:35b-a3b-q4_K_M-agentic; do
  curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
  curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
  for gate in T2 T4 T5; do
    NO_PROXY='*' no_proxy='*' python3 -u "$out/gate-rerun.py" --n 3 --gate "$gate" "$model"
  done
  NO_PROXY='*' no_proxy='*' python3 -u "$out/gate-extra.py" --n 3 "$model"
  curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"], "GPU spill"; print("Resident context:",m[0]["context_length"])' "$model"
  curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
done
