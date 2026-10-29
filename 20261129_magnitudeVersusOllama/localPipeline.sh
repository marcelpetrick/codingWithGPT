#!/usr/bin/env bash
# localPipeline.sh: the full quality gate. CI runs exactly this script.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  ./localPipeline.sh     run all stages, stop at the first failure
# Stages: install (uv) · license headers · ruff lint · ruff format check · mypy --strict ·
#         pytest (unit + integration + e2e against a fake engine) with branch coverage >= 95% ·
#         CLI smoke (mvo --version, mvo report on the committed results)
# Needs:  uv, Python 3.14. It needs no GPU and no engine: the tests use a fake HTTP engine.
# Exit:   0 all green; 1 a stage failed (the summary names it).
set -uo pipefail
cd "$(dirname "$0")"

VENV=.venv
PY="$VENV/bin/python"
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
  [ -x "$PY" ] || uv venv -q -p 3.14 "$VENV"
  VIRTUAL_ENV=$VENV uv pip install -q -e '.[dev]'
}

license_headers() {
  local missing
  missing=$(git ls-files --cached --others --exclude-standard '*.py' '*.sh' \
    | xargs -r grep -L 'SPDX-License-Identifier: GPL-3.0-or-later' || true)
  [ -z "$missing" ] || { echo "missing license header:"; echo "$missing"; return 1; }
}

cli_smoke() {
  local tmp
  tmp=$(mktemp -d)
  cp arms.json "$tmp/" && cp -r results "$tmp/" &&
    "$VENV/bin/mvo" --version &&
    "$VENV/bin/mvo" --root "$tmp" report &&
    grep -q '## Verdict' "$tmp/report.md" &&
    grep -q '<table id="cmp">' "$tmp/dashboard.html"
  local rc=$?
  rm -rf "$tmp"
  return $rc
}

stage "install"          install
stage "license headers"  license_headers
stage "ruff lint"        "$VENV/bin/ruff" check .
stage "ruff format"      "$VENV/bin/ruff" format --check .
stage "mypy strict"      "$VENV/bin/mypy"
stage "pytest coverage"  "$VENV/bin/pytest" -q
stage "cli smoke"        cli_smoke
print_summary
