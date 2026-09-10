#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

#
# The quality gate. The same entry point runs locally and in CI, so "it passed
# on my machine" and "it passed in CI" mean the same thing.
#
# Usage:
#   ./localPipeline.sh            lint, format check, tests + coverage gate,
#                                 smoke run, build, then launch the dashboard
#   ./localPipeline.sh --noRun    everything except the final interactive launch
#   ./localPipeline.sh --fix      apply ruff lint and format fixes first
#

set -euo pipefail

readonly PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly COVERAGE_GATE=90
cd -- "$PROJECT_ROOT"

run_app=1
fix=0
for argument in "$@"; do
    case "$argument" in
        --noRun) run_app=0 ;;
        --fix) fix=1 ;;
        -h | --help)
            sed -n '9,15p' "$0"
            exit 0
            ;;
        *)
            printf 'unknown option: %s\n' "$argument" >&2
            exit 2
            ;;
    esac
done

# Prefer the project virtualenv, then whatever python3 is on PATH (CI).
python="${PYTHON:-python3}"
if [[ -x .venv/bin/python ]]; then
    python=.venv/bin/python
fi

step() {
    printf '\n\033[1;36m== %s ==\033[0m\n' "$1"
}

step "Interpreter"
"$python" --version
"$python" -c 'import sys; sys.exit(sys.version_info < (3, 14))' || {
    printf 'Python 3.14 or newer is required.\n' >&2
    exit 1
}

if ((fix)); then
    step "Apply fixes"
    "$python" -m ruff check --fix src tests
    "$python" -m ruff format src tests
fi

step "Lint (ruff check)"
"$python" -m ruff check src tests

step "Format (ruff format --check)"
"$python" -m ruff format --check src tests

step "Tests with a ${COVERAGE_GATE}% branch-coverage gate"
"$python" -m pytest --cov --cov-report=term-missing:skip-covered --cov-report=xml \
    --cov-fail-under="$COVERAGE_GATE"

step "Smoke run (demo frame)"
PYTHONPATH=src "$python" -m tokenusage2 --demo --once --color never --tz UTC \
    --width 120 --height 40 >/dev/null
printf 'demo frame rendered\n'

step "Build (sdist + wheel)"
rm -rf dist
"$python" -m build --outdir dist . >/dev/null
ls -1 dist

printf '\n\033[1;32mAll checks passed.\033[0m\n'

if ((run_app)); then
    step "Launch the live dashboard"
    PYTHONPATH=src exec "$python" -m tokenusage2
fi
