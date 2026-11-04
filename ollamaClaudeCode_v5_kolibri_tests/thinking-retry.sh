#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Repeat v4 T1 with adaptive thinking as a separately labelled A/B arm.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model='kolibri1:q3ks-ctx147456-nothink-ab'
out='results/t1-adaptive'
mkdir -p "$out/results"
exec 8>results/thinking.lock
flock -n 8 || { echo 'Another thinking retry is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri adaptive-thinking gate finished" "Exit status: $rc. See results/thinking.log." 2>/dev/null || true' EXIT
exec 9>results/fidelity.lock
flock 9
[[ -f results/fidelity/results/gate-extra.tsv ]] || { echo 'Fidelity retry is incomplete.' >&2; exit 1; }
[[ $(wc -l < results/fidelity/results/gate-extra.raw.jsonl) -eq 8 ]] || { echo 'Fidelity runs are incomplete.' >&2; exit 1; }
[[ ! -e "$out/results/gate-rerun.raw.jsonl" ]] || { echo 'Existing result; review before restarting.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
cp ../ollamaClaudeCode_v4_tielCoder/gate-rerun.py "$out/gate-rerun.py"
python3 - "$out/gate-rerun.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
for old,new in [('d.get("content", [])','(d.get("content") or [])'),('"thinking": {"type": "disabled"}','"thinking": {"type": "adaptive"}')]:
    assert s.count(old)==1
    s=s.replace(old,new)
p.write_text(s)
PY
NO_PROXY='*' no_proxy='*' python3 -u "$out/gate-rerun.py" --n 8 --gate T1 "$model"
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"], "GPU spill"' "$model"
curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
