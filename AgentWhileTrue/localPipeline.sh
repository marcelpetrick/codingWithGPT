#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
declare -a PIPELINE_RESULTS=()
TEMP_ROOT=""

usage() {
    cat <<'EOF'
Usage: ./localPipeline.sh [--noRun]

Runs the same complete gate used by GitHub Actions:
  1. Verify Python 3.12+
  2. Ruff lint and format check, ShellCheck, tests and coverage
  3. Run every safety simulation
  4. Build the source distribution and wheel
  5. Install the wheel in an isolated environment
  6. Smoke-test both command names and all simulations

--noRun is accepted for consistency with this repository's other local
pipelines. Agent While True has no final interactive launch, so it is a no-op.
EOF
}

for argument in "$@"; do
    case "$argument" in
        --noRun | --no-run) ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            printf 'unknown option: %s\n' "$argument" >&2
            usage >&2
            exit 2
            ;;
    esac
done

cleanup() {
    if [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
        rm -rf -- "$TEMP_ROOT"
    fi
}

finish() {
    local status=$?
    printf '\n========== Agent While True Pipeline =========='
    printf '\n'
    for result in "${PIPELINE_RESULTS[@]}"; do
        printf '%s\n' "$result"
    done
    if [[ "$status" -eq 0 ]]; then
        printf 'Overall          : PASS\n'
    else
        printf 'Overall          : FAIL (exit %d)\n' "$status" >&2
    fi
    printf '================================================\n'
    cleanup
}

trap finish EXIT
cd -- "$PROJECT_ROOT"

printf '[INFO] Project root: %s\n' "$PROJECT_ROOT"
"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ required, found {sys.version.split()[0]}")
print(f"[INFO] Python {sys.version.split()[0]}")
PY
PIPELINE_RESULTS+=("Python baseline  : PASS (3.12+)")

scripts/quality.sh
PIPELINE_RESULTS+=("Quality gate     : PASS (Ruff, format, ShellCheck, pytest coverage)")

PYTHONPATH=src "$PYTHON_BIN" -m agent_watch.cli simulate --all
PIPELINE_RESULTS+=("Safety scenarios : PASS (all)")

TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/agent-while-true-pipeline.XXXXXX")"
ARTIFACT_DIR="$TEMP_ROOT/dist"
"$PYTHON_BIN" -m build --outdir "$ARTIFACT_DIR"
mkdir -p dist
cp -- "$ARTIFACT_DIR"/* dist/
PIPELINE_RESULTS+=("Package build    : PASS (sdist and wheel)")

"$PYTHON_BIN" -m venv "$TEMP_ROOT/smoke"
"$TEMP_ROOT/smoke/bin/python" -m pip install --disable-pip-version-check --no-deps \
    "$ARTIFACT_DIR"/*.whl
expected_version="$(PYTHONPATH=src "$PYTHON_BIN" -c 'from agent_watch.version import __version__; print(__version__)')"
[[ "$("$TEMP_ROOT/smoke/bin/agent-while-true" --version)" == *"$expected_version"* ]]
[[ "$("$TEMP_ROOT/smoke/bin/agent-watch" --version)" == *"$expected_version"* ]]
"$TEMP_ROOT/smoke/bin/agent-while-true" simulate --all
PIPELINE_RESULTS+=("Installed wheel  : PASS (both commands and simulations)")
