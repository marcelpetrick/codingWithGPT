#!/usr/bin/env bash
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PYTHON="${VENV_DIR}/bin/python3"
PIPELINE_LOG_DIR="${TMPDIR:-/tmp}/boldemort-pipeline-$$"
trap 'rm -rf "${PIPELINE_LOG_DIR}"' EXIT

declare -a SUMMARY_LINES=()

VENV_OK=0
INSTALL_OK=0
MYPY_OK=0
FLAKE8_OK=0
TESTS_OK=0

MYPY_DETAILS=""
FLAKE8_DETAILS=""
TESTS_DETAILS=""

# ---------------------------------------------------------------------------

log()   { printf '[INFO] %s\n' "$*"; }
warn()  { printf '[WARN] %s\n' "$*" >&2; }
error() { printf '[ERROR] %s\n' "$*" >&2; }

mark_result() {
    local label="$1" status="$2" details="$3"
    SUMMARY_LINES+=("$(printf '%-16s : %-4s %s' "${label}" "${status}" "${details}")")
}

run_with_log() {
    local log_path="$1"; shift
    mkdir -p "${PIPELINE_LOG_DIR}"
    "$@" 2>&1 | tee "${log_path}"
    return "${PIPESTATUS[0]}"
}

extract_mypy_details() {
    local log_path="$1"
    local line
    line="$(grep -E "^(Success|Found [0-9]+ error)" "${log_path}" | tail -n 1 || true)"
    if [[ "${line}" == Success* ]]; then
        printf '%s\n' "0 errors"
    elif [[ -n "${line}" ]]; then
        printf '%s\n' "${line}"
    else
        printf '%s\n' "see mypy output"
    fi
}

extract_flake8_details() {
    local log_path="$1"
    local count
    count="$(grep -c ":" "${log_path}" 2>/dev/null || true)"
    if [[ "${count}" -eq 0 ]]; then
        printf '%s\n' "0 violations"
    else
        printf '%s violation(s)\n' "${count}"
    fi
}

extract_test_details() {
    local log_path="$1"
    local line
    line="$(grep -E "[0-9]+ passed" "${log_path}" | tail -n 1 || true)"
    line="${line//=/}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    if [[ -n "${line}" ]]; then
        printf '%s\n' "${line}"
    else
        printf '%s\n' "see pytest output"
    fi
}

print_summary() {
    printf '\n========== Boldemort Pipeline Summary ==========\n'
    local line
    for line in "${SUMMARY_LINES[@]}"; do
        printf '%s\n' "${line}"
    done
    printf '=================================================\n'
}

# ---------------------------------------------------------------------------

prepare_virtual_environment() {
    if [[ -x "${PYTHON}" ]]; then
        log "Reusing existing virtual environment: ${VENV_DIR}"
        return 0
    fi
    log "Creating virtual environment: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
}

install_dependencies() {
    log "Installing dev dependencies from requirements-dev.txt"
    "${PYTHON}" -m pip install --quiet --upgrade pip
    "${PYTHON}" -m pip install --quiet -r "${SCRIPT_DIR}/requirements-dev.txt"
}

run_mypy() {
    log "Running mypy --strict"
    local log_path="${PIPELINE_LOG_DIR}/mypy.log"
    if run_with_log "${log_path}" "${PYTHON}" -m mypy --strict "${SCRIPT_DIR}/boldemort.py"; then
        MYPY_DETAILS="$(extract_mypy_details "${log_path}")"
        return 0
    fi
    MYPY_DETAILS="$(extract_mypy_details "${log_path}")"
    return 1
}

run_flake8() {
    log "Running flake8"
    local log_path="${PIPELINE_LOG_DIR}/flake8.log"
    if run_with_log "${log_path}" "${PYTHON}" -m flake8 \
            "${SCRIPT_DIR}/boldemort.py" "${SCRIPT_DIR}/tests/" \
            --max-line-length=88; then
        FLAKE8_DETAILS="$(extract_flake8_details "${log_path}")"
        return 0
    fi
    FLAKE8_DETAILS="$(extract_flake8_details "${log_path}")"
    return 1
}

run_tests() {
    log "Running pytest"
    local log_path="${PIPELINE_LOG_DIR}/pytest.log"
    if run_with_log "${log_path}" "${PYTHON}" -m pytest \
            "${SCRIPT_DIR}/tests/" -v; then
        TESTS_DETAILS="$(extract_test_details "${log_path}")"
        return 0
    fi
    TESTS_DETAILS="$(extract_test_details "${log_path}")"
    return 1
}

# ---------------------------------------------------------------------------

main() {
    local exit_code=1

    if prepare_virtual_environment; then
        VENV_OK=1
        mark_result "Virtualenv" "PASS" ".venv is available"
    else
        mark_result "Virtualenv" "FAIL" "Could not create or reuse .venv"
    fi

    if [[ "${VENV_OK}" -eq 1 ]]; then
        if install_dependencies; then
            INSTALL_OK=1
            mark_result "Dependencies" "PASS" "requirements-dev.txt installed"
        else
            mark_result "Dependencies" "FAIL" "Dependency installation failed"
        fi
    else
        mark_result "Dependencies" "SKIP" "Skipped because .venv is unavailable"
    fi

    if [[ "${INSTALL_OK}" -eq 1 ]]; then
        if run_mypy; then
            MYPY_OK=1
            mark_result "mypy" "PASS" "${MYPY_DETAILS}"
        else
            mark_result "mypy" "FAIL" "${MYPY_DETAILS}"
        fi

        if run_flake8; then
            FLAKE8_OK=1
            mark_result "flake8" "PASS" "${FLAKE8_DETAILS}"
        else
            mark_result "flake8" "FAIL" "${FLAKE8_DETAILS}"
        fi

        if run_tests; then
            TESTS_OK=1
            mark_result "pytest" "PASS" "${TESTS_DETAILS}"
        else
            mark_result "pytest" "FAIL" "${TESTS_DETAILS}"
        fi
    else
        mark_result "mypy"   "SKIP" "Skipped because dependencies are unavailable"
        mark_result "flake8" "SKIP" "Skipped because dependencies are unavailable"
        mark_result "pytest" "SKIP" "Skipped because dependencies are unavailable"
    fi

    if [[ "${VENV_OK}" -eq 1 && "${INSTALL_OK}" -eq 1 && "${MYPY_OK}" -eq 1 && "${FLAKE8_OK}" -eq 1 && "${TESTS_OK}" -eq 1 ]]; then
        exit_code=0
    fi

    if [[ "${exit_code}" -eq 0 ]]; then
        log "localPipeline.sh completed successfully"
    else
        error "localPipeline.sh completed with failing stage(s)"
    fi

    print_summary
    exit "${exit_code}"
}

main "$@"
