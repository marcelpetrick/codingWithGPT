#!/usr/bin/env bash
#
# The quality gate. The same entry point runs locally and in CI, so "it passed
# on my machine" and "it passed in CI" mean the same thing.
#
# Usage:
#   scripts/quality.sh            # lint, format check, shellcheck, tests
#   scripts/quality.sh --fix      # apply lint and format fixes first
#   scripts/quality.sh --no-cov   # skip coverage (faster inner loop)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname -- "$SCRIPT_DIR")"
cd -- "$PROJECT_ROOT"

FIX=0
COVERAGE=1
for argument in "$@"; do
    case "$argument" in
        --fix) FIX=1 ;;
        --no-cov) COVERAGE=0 ;;
        -h | --help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            printf 'unknown option: %s\n' "$argument" >&2
            exit 2
            ;;
    esac
done

failures=0

step() {
    printf '\n\033[1m== %s ==\033[0m\n' "$1"
}

fail() {
    printf '\033[31mFAILED: %s\033[0m\n' "$1" >&2
    failures=$((failures + 1))
}

# Prefer the tools from an active virtualenv, then the user's PATH. Falling
# back to `python -m` keeps this working where only the module is installed.
run_tool() {
    local tool="$1"
    shift
    if command -v "$tool" > /dev/null 2>&1; then
        "$tool" "$@"
    elif python3 -c "import $tool" > /dev/null 2>&1; then
        python3 -m "$tool" "$@"
    else
        printf 'missing tool: %s\n' "$tool" >&2
        return 127
    fi
}

step "ruff (lint)"
if [ "$FIX" -eq 1 ]; then
    run_tool ruff check --fix . || fail "ruff check"
else
    run_tool ruff check . || fail "ruff check"
fi

step "ruff (format)"
if [ "$FIX" -eq 1 ]; then
    run_tool ruff format . || fail "ruff format"
else
    run_tool ruff format --check . || fail "ruff format --check"
fi

step "shellcheck"
if command -v shellcheck > /dev/null 2>&1; then
    # Every tracked shell script, including this one. `git ls-files` rather than
    # `find` so untracked scratch files never gate the build.
    mapfile -t scripts < <(git ls-files '*.sh')
    if [ "${#scripts[@]}" -gt 0 ]; then
        shellcheck --severity=style "${scripts[@]}" || fail "shellcheck"
    else
        printf 'no shell scripts tracked yet\n'
    fi
else
    printf 'shellcheck not installed; skipping\n' >&2
fi

step "pytest"
if [ "$COVERAGE" -eq 1 ]; then
    run_tool pytest --cov=agent_watch --cov-report=term-missing --cov-report=xml \
        --cov-fail-under=85 \
        || fail "pytest"
else
    run_tool pytest || fail "pytest"
fi

step "version consistency"
python3 - <<'PY' || fail "version consistency"
import pathlib
import re
import sys

sys.path.insert(0, "src")
from agent_watch.version import __version__

changelog = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
match = re.search(r"^## \[([^\]]+)\]", changelog, flags=re.MULTILINE)
newest = match.group(1) if match else "<none>"
if newest != __version__:
    print(f"CHANGELOG.md newest entry is {newest}, __version__ is {__version__}")
    raise SystemExit(1)
print(f"version {__version__} matches the changelog")
PY

printf '\n'
if [ "$failures" -ne 0 ]; then
    printf '\033[31m%d check(s) failed\033[0m\n' "$failures" >&2
    exit 1
fi
printf '\033[32mall checks passed\033[0m\n'
