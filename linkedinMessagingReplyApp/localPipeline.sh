#!/usr/bin/env bash
# localPipeline.sh: the full quality gate. CI runs exactly this script.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  ./localPipeline.sh            run all stages, stop at the first failure
# Stages: install (uv) · license headers · ruff lint · ruff format check · mypy --strict ·
#         guard (hard limits) · pytest + branch coverage >= 95% · build sdist + wheel ·
#         wheel smoke in a clean venv
# Needs:  uv, Python 3.14. Never contacts linkedin.com.
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
  missing=$(git ls-files --cached --others --exclude-standard '*.py' '*.sh' '*.js' \
    | xargs -r grep -L 'SPDX-License-Identifier: GPL-3.0-or-later' || true)
  [ -z "$missing" ] || { echo "missing license header:"; echo "$missing"; return 1; }
}

build_dist() {
  rm -rf dist build src/*.egg-info
  "$PY" -m build -q --outdir dist . >/dev/null
  ls dist
}

wheel_smoke() {
  local tmp
  tmp=$(mktemp -d)
  uv venv -q -p 3.14 "$tmp/venv" &&
    VIRTUAL_ENV="$tmp/venv" uv pip install -q dist/*.whl &&
    "$tmp/venv/bin/lra" --version &&
    "$tmp/venv/bin/python" -c "from pathlib import Path; from linkedin_reply_assistant.config.loader import load_config as f; c = f(Path('$tmp/none')); print(len(c.prompts), 'prompts shipped')"
  local rc=$?
  rm -rf "$tmp"
  return $rc
}

stage "install"          install
stage "license headers"  license_headers
stage "ruff lint"        "$VENV/bin/ruff" check .
stage "ruff format"      "$VENV/bin/ruff" format --check .
stage "mypy strict"      "$VENV/bin/mypy"
stage "guard"            "$VENV/bin/pytest" -q --no-cov tests/unit/test_guard.py
stage "pytest coverage"  "$VENV/bin/pytest" -q
stage "build"            build_dist
stage "wheel smoke"      wheel_smoke
print_summary
