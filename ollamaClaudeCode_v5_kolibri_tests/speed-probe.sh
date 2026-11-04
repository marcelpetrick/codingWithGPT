#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Measure cold v4 throughput for Kolibri and the control, three times each.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
out='results/speed'
mkdir -p "$out/results"
exec 8>results/speed.lock
flock -n 8 || { echo 'Another speed test is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri speed test finished" "Exit status: $rc. See results/speed.log." 2>/dev/null || true' EXIT
exec 9>results/needle.lock
flock 9
grep -q '^=== finished ===$' results/needle-nothink/results/needle-v2.log || { echo 'Retrieval stage did not finish.' >&2; exit 1; }
[[ ! -e "$out/results/tokrate.tsv" ]] || { echo 'Existing speed results; review before restarting.' >&2; exit 1; }
cp ../ollamaClaudeCode_v4_tielCoder/tokrate.sh ../ollamaClaudeCode_v4_tielCoder/lib-preflight.sh "$out/"
python3 - "$out/tokrate.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
changes=[('set -uo pipefail','set -euo pipefail'),('for W in 0 2000 20000; do','for W in "$WORD_COUNT"; do'),('local R; R=$(curl -s --max-time "$TIMEOUT"','local R; R=$(curl -fsS --max-time "$TIMEOUT"'),("  printf '%s' \"$R\" | python3 -c", "  printf '%s\\n' \"$R\" >> \"$OUT/tokrate.raw.jsonl\"\n  printf '%s' \"$R\" | python3 -c"),('except Exception: print(\'  %-42s PARSE_FAIL\'%m); raise SystemExit',"except Exception: raise SystemExit('invalid response')"),('if d.get(\'error\'): print(\'  %-42s ERROR %s\'%(m,str(d[\'error\'])[:60])); raise SystemExit',"if d.get('error'): raise SystemExit('server error: '+str(d['error']))"),('pe=d.get(\'prompt_eval_count\',0); pd=d.get(\'prompt_eval_duration\',0) or 1',"\nif not d.get('done') or not (d.get('message') or {}).get('content','').strip(): raise SystemExit('incomplete or empty answer')\nfor key in ('prompt_eval_count','prompt_eval_duration','eval_count','eval_duration'):\n    if not isinstance(d.get(key),int) or d[key] <= 0: raise SystemExit('missing counter: '+key)\npe=d['prompt_eval_count']; pd=d['prompt_eval_duration']")]
for old,new in changes:
    assert s.count(old)==1, old
    s=s.replace(old,new)
p.write_text(s)
PY
for run in 1 2 3; do
  for words in 0 2000 20000; do
    for model in kolibri1:q3ks-ctx147456-nothink-ab qwen3.6:35b-a3b-q4_K_M-agentic; do
      curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
      curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
      printf 'Run %s, words %s, model %s\n' "$run" "$words" "$model"
      WORD_COUNT="$words" NO_PROXY='*' no_proxy='*' bash "$out/tokrate.sh" "$model"
      curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; m=json.load(sys.stdin)["models"]; assert len(m)==1 and m[0]["name"].lower()==sys.argv[1].lower(), "Unexpected resident model"; assert m[0]["size_vram"]>=m[0]["size"], "GPU spill"; print("Resident context:",m[0]["context_length"])' "$model"
      curl --noproxy '*' -fsS -m 30 "$base/api/generate" -H 'Content-Type: application/json' --data "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
    done
  done
done
