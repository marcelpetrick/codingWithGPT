#!/usr/bin/env bash
# localPipeline.sh: the full quality gate. CI runs exactly this script.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  ./localPipeline.sh            run all stages, stop at the first failure
#         MUTATION=1 ./localPipeline.sh  also run mutation testing (slow, about 10 minutes)
# Stages: install (uv, locked) · license headers · ruff lint · black check · mypy --strict ·
#         node --check of the dashboard script · pytest (unit, integration, e2e in Chromium)
#         with line coverage >= 99% · CLI smoke (demo dashboard) · optional mutation testing.
# Needs:  uv, Python 3.14, Node.js (syntax check only). Playwright downloads Chromium once.
#         No GitLab and no Ollama: the tests use fake HTTP servers.
# Exit:   0 all green; 1 a stage failed (the summary names it).
set -uo pipefail
cd "$(dirname "$0")"

declare -a SUMMARY=()

stage() {  # stage <name> <command...>
  local name=$1; shift
  printf '\n=== %s ===\n' "$name"
  local start=$SECONDS
  if "$@"; then
    SUMMARY+=("ok    $name ($((SECONDS - start)) s)")
  else
    SUMMARY+=("FAIL  $name")
    print_summary
    exit 1
  fi
}

print_summary() {
  printf '\n=== summary ===\n'
  printf '%s\n' "${SUMMARY[@]}"
}

install() {
  uv sync --locked -q && uv run playwright install chromium >/dev/null
}

license_headers() {
  local missing
  missing=$(git ls-files --cached --others --exclude-standard '*.py' '*.sh' '*.js' '*.css' '*.html' \
    | grep -v '^docs/demo/' | xargs -r grep -L 'SPDX-License-Identifier: GPL-3.0-or-later' || true)
  [ -z "$missing" ] || { echo "missing license header:"; echo "$missing"; return 1; }
}

cli_smoke() {
  local tmp
  tmp=$(mktemp -d)
  uv run mrreview --version &&
    uv run mrreview demo --out "$tmp" 2>/dev/null &&
    grep -q 'Content-Security-Policy' "$tmp/dashboard.html" &&
    grep -q 'id="data"' "$tmp/dashboard.html"
  local rc=$?
  rm -rf "$tmp"
  return $rc
}

mutation() {
  rm -rf mutants && uv run mutmut run --max-children 4 >/dev/null 2>&1
  uv run mutmut results 2>/dev/null | tee mutation_results.txt | tail -20
  return 0
}

stage "install"           install
stage "license headers"   license_headers
stage "ruff lint"         uv run ruff check .
stage "black format"      uv run black --check -q src tests scripts
stage "mypy strict"       uv run mypy
stage "dashboard syntax"  node --check src/mrreview/assets/dashboard.js
stage "pytest coverage"   uv run pytest -q
stage "cli smoke"         cli_smoke
if [ "${MUTATION:-0}" = "1" ]; then stage "mutation testing" mutation; fi
print_summary
