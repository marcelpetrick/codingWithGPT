#!/usr/bin/env bash
# localPipeline.sh: the full quality gate. CI runs exactly this script.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  ./localPipeline.sh            run all stages, stop at the first failure
# Stages: 1 venv + install (uv)   2 license headers   3 ruff lint   4 ruff format check
#         5 mypy --strict          6 pytest + coverage >= 95%      7 build sdist + wheel
#         8 install the wheel in a clean venv and run `reply-desk --version`
# Later:  e2e (Playwright on the local UI) is added with phase 4. Docker: not planned yet.
# Needs:  uv, Python 3.14. No network access to LinkedIn, ever.
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

build_dist() {
  rm -rf dist build ./*.egg-info
  "$PY" -m build -q --outdir dist . >/dev/null
  ls dist
}

wheel_smoke() {
  local tmp
  tmp=$(mktemp -d)
  uv venv -q -p 3.14 "$tmp/venv" &&
    VIRTUAL_ENV="$tmp/venv" uv pip install -q dist/*.whl &&
    "$tmp/venv/bin/reply-desk" --version
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
stage "build"            build_dist
stage "wheel smoke"      wheel_smoke
print_summary
