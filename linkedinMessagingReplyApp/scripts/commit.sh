#!/usr/bin/env bash
# commit.sh: one green, logged, pushed commit. Runs the pipeline, logs the check in plan.md, commits, pushes.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/commit.sh <patch|minor|major|none> "<conventional subject>" ["<body: why>"] [extra check]
#         Stage nothing yourself: the script stages this project directory and the project CI workflows.
#         "none" keeps the version (only for the very first commit of a version).
#         [extra check] is a text for the plan row, for example "live Ollama check ok".
# Steps:  1 bump version  2 ./localPipeline.sh  3 append a row to the commit log in plan.md
#         4 git add + commit  5 git push
# Exit:   0 committed and pushed; 1 pipeline red (nothing committed, version bump kept for the retry);
#         2 bad arguments; 3 push failed (commit exists locally).
set -uo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 2 ] || { sed -n '2,13p' "$0"; exit 2; }
part=$1 subject=$2 body=${3:-} extra=${4:-}
if [ "$part" != none ]; then scripts/bump_version.sh "$part" >/dev/null || exit 2; fi
version=$(sed -nE 's/^__version__ = "(.*)"$/\1/p' src/linkedin_reply_assistant/version.py)

log=$(mktemp)
if ! ./localPipeline.sh >"$log" 2>&1; then
  grep -E "^(FAILED|ERROR) |^E  " "$log" | head -20
  tail -15 "$log"; cp "$log" /tmp/lra-last-red-pipeline.log
  echo "pipeline red: nothing committed (full log: /tmp/lra-last-red-pipeline.log)"; exit 1
fi
stages=$(grep -c '^ok ' "$log")
check="\`./localPipeline.sh\` ($stages stages)"
[ -n "$extra" ] && check="$check; $extra"
coverage=$(grep -oE '^TOTAL.* ([0-9.]+%)$' "$log" | grep -oE '[0-9.]+%$' || echo "n/a")
row="| $version | $subject | $check | green, coverage $coverage |"
# Insert the row after the last line of the commit log table.
python3 - "$row" <<'PY'
import sys, pathlib
p = pathlib.Path("plan.md"); lines = p.read_text().splitlines()
start = next(i for i, l in enumerate(lines) if l.startswith("## Commit log"))
i = start + 1
while i < len(lines) and not lines[i].startswith("|"): i += 1
while i < len(lines) and lines[i].startswith("|"): i += 1
lines.insert(i, sys.argv[1]); p.write_text("\n".join(lines) + "\n")
PY
git add -A . ../.github/workflows/linkedin-reply-assistant*.yml 2>/dev/null || git add -A .
msg="$subject (v$version)"
if [ -n "$body" ]; then git commit -q -m "$msg" -m "$body"; else git commit -q -m "$msg"; fi
git log --oneline -1
git push -q || { echo "push failed"; exit 3; }
echo "pushed v$version"
