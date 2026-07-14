#!/usr/bin/env bash
set -u
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_DIR=""
PIPELINE_LOG_DIR=""
REMOVE_PIPELINE_LOG_DIR=true
INSTALL_DEPENDENCIES=false
RUN_E2E=true
FAILED_STAGES=0

declare -a SUMMARY_LINES=()

print_usage() {
  cat <<'EOF'
Usage: ./localPipeline.sh [--install] [--skip-e2e] [--report-dir PATH]

Run the Recognizer local quality pipeline:
  1. Optionally install locked dependencies with npm ci
  2. Check Prettier formatting
  3. Validate local Markdown links
  4. Run ESLint
  5. Run TypeScript type checking
  6. Run Vitest unit and component tests
  7. Build the production Progressive Web App
  8. Run Playwright desktop/mobile browser and accessibility tests

Options:
  --install            Run npm ci before the checks.
  --skip-e2e           Skip Playwright tests; useful when browsers are unavailable.
  --report-dir PATH    Preserve individual stage logs and summary in PATH.
  --help, -h           Show this help.

Without --report-dir, temporary logs are removed after the summary is printed.
EOF
}

log() {
  printf '[INFO] %s\n' "$*"
}

error() {
  printf '[ERROR] %s\n' "$*" >&2
}

parse_arguments() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --install)
        INSTALL_DEPENDENCIES=true
        shift
        ;;
      --skip-e2e)
        RUN_E2E=false
        shift
        ;;
      --report-dir)
        if [[ "$#" -lt 2 || -z "$2" ]]; then
          error '--report-dir requires a path.'
          print_usage
          exit 2
        fi
        REPORT_DIR="$2"
        shift 2
        ;;
      --help|-h)
        print_usage
        exit 0
        ;;
      *)
        error "Unknown argument: $1"
        print_usage
        exit 2
        ;;
    esac
  done
}

prepare_logs() {
  if [[ -n "${REPORT_DIR}" ]]; then
    PIPELINE_LOG_DIR="${REPORT_DIR}"
    REMOVE_PIPELINE_LOG_DIR=false
    mkdir -p "${PIPELINE_LOG_DIR}"
  else
    PIPELINE_LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/recognizer-pipeline.XXXXXX")"
  fi
}

record_stage() {
  local name="$1"
  local status="$2"
  local detail="$3"
  SUMMARY_LINES+=("$(printf '%-16s : %-4s %s' "${name}" "${status}" "${detail}")")
}

run_stage() {
  local name="$1"
  shift
  local log_path="${PIPELINE_LOG_DIR}/${name}.log"

  log "${name}: $*"
  if "$@" 2>&1 | tee "${log_path}"; then
    record_stage "${name}" "PASS" "${log_path}"
    return 0
  fi

  record_stage "${name}" "FAIL" "${log_path}"
  FAILED_STAGES=$((FAILED_STAGES + 1))
  return 1
}

print_summary() {
  {
    printf '\n========== Recognizer Local Pipeline Summary ==========\n'
    local line
    for line in "${SUMMARY_LINES[@]}"; do
      printf '%s\n' "${line}"
    done
    printf '========================================================\n'
  } | tee "${PIPELINE_LOG_DIR}/summary.txt"
}

cleanup() {
  if [[ "${REMOVE_PIPELINE_LOG_DIR}" == true ]]; then
    rm -rf "${PIPELINE_LOG_DIR}"
  else
    log "Saved pipeline reports: ${PIPELINE_LOG_DIR}"
  fi
}

main() {
  parse_arguments "$@"

  if ! command -v npm >/dev/null 2>&1; then
    error 'npm is required but was not found on PATH.'
    exit 127
  fi

  cd "${ROOT_DIR}"
  prepare_logs
  trap cleanup EXIT

  if [[ "${INSTALL_DEPENDENCIES}" == true ]]; then
    run_stage install npm ci || true
  elif [[ ! -d node_modules ]]; then
    record_stage install "FAIL" "node_modules is missing; run npm ci or pass --install"
    FAILED_STAGES=$((FAILED_STAGES + 1))
  else
    record_stage install "PASS" "existing node_modules reused"
  fi

  run_stage format npm run format:check || true
  run_stage docs-links npm run docs:check-links || true
  run_stage lint npm run lint || true
  run_stage typecheck npm run typecheck || true
  run_stage unit-tests npm test || true
  run_stage build npm run build || true

  if [[ "${RUN_E2E}" == true ]]; then
    run_stage browser-tests npm run test:e2e || true
  else
    record_stage browser-tests "SKIP" "disabled by --skip-e2e"
  fi

  print_summary

  if [[ "${FAILED_STAGES}" -gt 0 ]]; then
    error "${FAILED_STAGES} pipeline stage(s) failed."
    exit 1
  fi

  log 'All pipeline stages passed.'
}

main "$@"
