#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Download the selected Q3 model to the Ollama server. See KOLIBRI_Q3_RUN.md.
set -euo pipefail
cd "$(dirname "$0")"
model='hf.co/Eliasfpv28/Kolibri-1-Q3_K_S-GGUF:Q3_K_S'
base='http://192.168.100.67:11434'
mkdir -p results
exec 9>results/pull.lock
flock -n 9 || { echo 'Another pull is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri pull finished" "Exit status: $rc. See results/pull.log." 2>/dev/null || true' EXIT
curl --noproxy '*' -fsS --max-time 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
curl --noproxy '*' -fsS --max-time 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
if curl --noproxy '*' -fsS --max-time 10 "$base/api/tags" | python3 -c 'import json,sys; sys.exit(0 if any(x["name"].lower() == sys.argv[1].lower() for x in json.load(sys.stdin)["models"]) else 1)' "$model"; then
  echo 'Model is already present.'
  exit 0
fi
curl --noproxy '*' -fsS --connect-timeout 10 --speed-time 300 --speed-limit 1 \
  "$base/api/pull" -H 'Content-Type: application/json' \
  --data "{\"model\":\"$model\",\"stream\":true}" | \
  python3 -u -c 'import json,sys
success = False
for line in sys.stdin:
    event = json.loads(line)
    if "error" in event:
        raise SystemExit(event["error"])
    print(json.dumps(event), flush=True)
    success = event.get("status") == "success"
if not success:
    raise SystemExit("Pull ended without success")'
