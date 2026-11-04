#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Run the v4 coding fixtures in an isolated container after the tool battery.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
out='results/coding'
mkdir -p "$out/results"
exec 8>results/coding.lock
flock -n 8 || { echo 'Another coding benchmark is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri coding benchmark finished" "Exit status: $rc. See results/coding.log." 2>/dev/null || true' EXIT
exec 9>results/battery.lock
flock 9
[[ -f results/agentic-battery/results/gate-rerun.raw.jsonl && -f results/agentic-battery/results/gate-extra.raw.jsonl ]] || { echo 'Agentic battery is incomplete.' >&2; exit 1; }
[[ $(wc -l < results/agentic-battery/results/gate-rerun.raw.jsonl) -eq 18 ]] || { echo 'Agentic gate runs are incomplete.' >&2; exit 1; }
[[ $(wc -l < results/agentic-battery/results/gate-extra.raw.jsonl) -eq 24 ]] || { echo 'Extra gate runs are incomplete.' >&2; exit 1; }
[[ ! -e "$out/results/cc-session-sandboxed.tsv" ]] || { echo 'Existing coding results; review before restarting.' >&2; exit 1; }
docker image inspect v4-cc-sandbox:latest >/dev/null
if docker network inspect v5-kolibri-egress >/dev/null 2>&1 || docker inspect v5-kolibri-relay >/dev/null 2>&1; then
  echo 'Sandbox network or relay already exists.' >&2; exit 1
fi
cp ../ollamaClaudeCode_v4_tielCoder/cc-session-sandboxed.sh ../ollamaClaudeCode_v4_tielCoder/cc-analyse.py "$out/"
cp -a ../ollamaClaudeCode_v4_tielCoder/fixtures "$out/fixtures"
python3 - "$out/cc-session-sandboxed.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
changes=[('set -uo pipefail','set -euo pipefail'),('NET="v4-egress-none"','NET="v5-kolibri-egress"'),('RELAY="v4-relay"','RELAY="v5-kolibri-relay"'),('CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000','CLAUDE_CODE_MAX_CONTEXT_TOKENS=147456'),('curl -s -m 900 "$API/api/generate"','curl -fsS -m 900 "$API/api/generate"'),('t.extractall(dest)','t.extractall(dest, filter="data")'),('    print("  WARNING: no working tree came back from the container", file=sys.stderr)','    raise SystemExit("No working tree came back from the container")'),('  W0=$(date +%s.%N)','  if [[ "$EGRESS" != *"relay=200"* || "$EGRESS" != *"internet=000"* ]]; then docker rm -f "$CID" >/dev/null 2>&1 || true; echo "Sandbox egress check failed: $EGRESS" >&2; exit 1; fi\n  W0=$(date +%s.%N)')]
for old,new in changes:
    assert s.count(old)==1, old
    s=s.replace(old,new)
p.write_text(s)
PY
for run in 1 2 3; do
  for fixture in easy hard; do
    for model in kolibri1:q3ks-ctx147456-nothink-ab qwen3.6:35b-a3b-q4_K_M-agentic; do
      curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
      curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
      printf 'Coding run %s, fixture %s, model %s\n' "$run" "$fixture" "$model"
      NO_PROXY='*' no_proxy='*' bash "$out/cc-session-sandboxed.sh" --fixture "$fixture" --runs 1 --first-run "$run" "$model"
      curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"], "GPU spill"; print("Resident context:",m[0]["context_length"])' "$model"
      curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
    done
  done
done
