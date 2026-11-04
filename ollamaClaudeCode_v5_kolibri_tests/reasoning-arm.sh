#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Test the official disabled-reasoning instruction as a separate template arm.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
model='kolibri1:q3ks-ctx147456-reason-ab'
exec 8>results/reasoning.lock
flock -n 8 || { echo 'Another reasoning arm is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri reasoning-template test finished" "Exit status: $rc. See results/reasoning.log." 2>/dev/null || true' EXIT
exec 9>results/bilingual.lock
flock 9
[[ -f results/bilingual/results.jsonl ]] || { echo 'Bilingual results missing.' >&2; exit 1; }
[[ $(wc -l < results/bilingual/results.jsonl) -eq 12 ]] || { echo 'Bilingual stage is incomplete.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
curl --noproxy '*' -fsS -m 10 "$base/api/tags" | python3 -c 'import json,sys; assert not any(m["name"].lower()==sys.argv[1].lower() for m in json.load(sys.stdin)["models"]), "Target tag exists"' "$model"
python3 - <<'PY'
import json
from pathlib import Path
body={"model":"kolibri1:q3ks-ctx147456-reason-ab", "from":"kolibri1:q3ks-ctx147456-nothink-ab", "template":Path("templates/kolibri-reasoning-effort.gotmpl").read_text(), "stream":False}
Path("results/reasoning-create.json").write_text(json.dumps(body))
PY
curl --noproxy '*' -fsS -m 120 "$base/api/create" -H 'Content-Type: application/json' --data-binary @results/reasoning-create.json | python3 -c 'import json,sys; assert json.load(sys.stdin).get("status") == "success"'
./gate-reliability.sh "$model" reason-effort
