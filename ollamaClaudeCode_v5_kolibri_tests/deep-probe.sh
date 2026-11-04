#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Run v4 T3 and T7 with the other short gates, after coding sessions.
set -euo pipefail
cd "$(dirname "$0")"
base='http://192.168.100.67:11434'
out='results/deep'
mkdir -p "$out"
exec 8>results/deep.lock
flock -n 8 || { echo 'Another deep probe is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri deep gates finished" "Exit status: $rc. See results/deep.log." 2>/dev/null || true' EXIT
exec 9>results/coding.lock
flock 9
[[ -f results/coding/results/cc-session-sandboxed.tsv ]] || { echo 'Coding results missing.' >&2; exit 1; }
[[ $(wc -l < results/coding/results/cc-session-sandboxed.tsv) -eq 13 ]] || { echo 'Coding stage is incomplete.' >&2; exit 1; }
[[ ! -e "$out/agentic-test.sh" ]] || { echo 'Existing deep probe; review before restarting.' >&2; exit 1; }
cp ../ollamaClaudeCode_v4_tielCoder/agentic-test.sh "$out/agentic-test.sh"
python3 - "$out/agentic-test.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
safe='''safe_assign() {
  local value="$1" pattern='^V=([A-Z]+);[[:space:]]+(D|T)=([A-Za-z0-9_:+,?.-]+)$'
  [[ "$value" =~ $pattern ]] || { echo "Unexpected scorer output; stopping" >&2; return 1; }
  V="${BASH_REMATCH[1]}"
  if [[ "${BASH_REMATCH[2]}" == D ]]; then D="${BASH_REMATCH[3]}"; else T="${BASH_REMATCH[3]}"; fi
}
'''
anchor='rec() { printf'
assert s.count(anchor)==1
s=s.replace(anchor,safe+anchor)
assert s.count('eval "$(')==6
s=s.replace('eval "$(', 'safe_assign "$(')
assert s.count("d.get('content',[])")==7
s=s.replace("d.get('content',[])", "(d.get('content') or [])")
s=s.replace('set -uo pipefail','set -euo pipefail')
old='  resp=$(curl -s --max-time "$TIMEOUT" -X POST "$MSG_URL" "${HDR[@]}" -d "$body" 2>&1)'
new='  resp=$(curl -fsS --max-time "$TIMEOUT" -X POST "$MSG_URL" "${HDR[@]}" -d "$body") || return $?\n  printf "%s" "$resp" | python3 -c \'import json,sys; d=json.load(sys.stdin); assert not d.get("error"), "API error"\' || return $?'
assert s.count(old)==1
s=s.replace(old,new)
for line in ('needle_test 2700  4k','needle_test 10700 16k','needle_test 40000 60k','needle_test 80000 120k'):
    assert s.count(line)==1
    s=s.replace(line, '# Retrieval measured separately: '+line)
p.write_text(s)
PY
for model in kolibri1:q3ks-ctx147456-nothink-ab qwen3.6:35b-a3b-q4_K_M-agentic; do
  label="${model%%:*}"
  curl --noproxy '*' -fsS -m 10 "$base/api/version" | python3 -c 'import json,sys; assert json.load(sys.stdin)["version"] == "0.40.11"'
  curl --noproxy '*' -fsS -m 10 "$base/api/ps" | python3 -c 'import json,sys; assert json.load(sys.stdin)["models"] == [], "Server is busy"'
  NO_PROXY='*' no_proxy='*' bash "$out/agentic-test.sh" 192.168.100.67 "$model" "$out/$label"
  python3 - "$out/$label" <<'PY'
from pathlib import Path
import csv,re,sys
rows=list(csv.DictReader(next(Path(sys.argv[1]).glob('*.tsv')).open(),delimiter='\t'))
t7=[r for r in rows if r['test']=='T7_tool_at_long_ctx']
assert len(t7)==1, 'Missing long-context gate'
m=re.search(r'_at_(\d+)_tokens',t7[0]['detail'])
assert m and int(m.group(1)) >= 40000, 'Long-context prompt size was not verified'
PY
done
