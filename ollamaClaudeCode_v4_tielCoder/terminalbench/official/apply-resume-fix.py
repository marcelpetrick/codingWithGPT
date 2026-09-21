#!/usr/bin/env python3
"""apply-resume-fix.py -- swap done_already() for the trial-count test.

Kept as a separate, idempotent script for one reason: GO_official_tb.sh was
RUNNING when the defect was found, and bash reads a script by byte offset as it
executes, so editing it mid-run can make it run garbage. This applies the fix
once the round has exited, and does nothing if it is already applied.
"""
import re
import sys
from pathlib import Path

GO = Path(__file__).resolve().parent / "GO_official_tb.sh"
NEW = '''done_already () {  # <model> <runs> -> 0 only if the pass is genuinely COMPLETE
  local slug arm d have want
  slug="$(echo "$1" | tr '/:' '__' | tr 'A-Z' 'a-z')"
  arm="think${TB_THINKING:-on}"
  want=$(( ${#TASKS[@]} * $2 ))
  for d in "$OUT/$slug-$arm-n$2-"*; do
    [ -d "$d" ] || continue
    have=$(find "$d" -mindepth 3 -name results.json 2>/dev/null | wc -l)
    [ "$have" -ge "$want" ] && return 0
  done
  return 1
}'''

s = GO.read_text()
if "want=$(( ${#TASKS[@]} * $2 ))" in s:
    print("resume fix: already applied")
    sys.exit(0)
m = re.search(r"done_already \(\) \{.*?\n\}", s, re.S)
if not m:
    print("resume fix: done_already() not found -- NOT applied", file=sys.stderr)
    sys.exit(1)
GO.write_text(s[: m.start()] + NEW + s[m.end():])
print("resume fix: applied")
