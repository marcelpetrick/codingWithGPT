#!/bin/sh

set -u

SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
DEFAULT_WORKDIR=$(dirname -- "$SCRIPT_DIR")
PROMPT="Return only the result of 1+1."
VERBOSE=0
WAIT_ON_EXIT=0
TIMEOUT_SECONDS="${TRIGGER_TIMEOUT_SECONDS:-300}"
WORKDIR="$DEFAULT_WORKDIR"

print_help() {
  cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Run a minimal non-interactive 1+1 check with Claude Code and Codex.

Options:
  -h, --help           Show this help text and exit.
  -v, --verbose        Print commands, paths, and progress information.
      --wait           Wait for Enter before exiting.
      --workdir DIR    Directory to enter before running the checks.
                       Defaults to the parent of this script directory:
                       ${DEFAULT_WORKDIR}

Environment:
  TRIGGER_TIMEOUT_SECONDS
                       Per-command timeout in seconds. Defaults to 300.

Examples:
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} --verbose
  ./${SCRIPT_NAME} --verbose --wait
  ./${SCRIPT_NAME} --workdir "\$HOME/projects/example"
EOF
}

log() {
  if [ "$VERBOSE" -eq 1 ]; then
    printf '%s\n' "$*"
  fi
}

fail() {
  printf '%s\n' "Error: $*" >&2
}

require_command() {
  command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    fail "required command not found: ${command_name}"
    return 1
  fi

  log "Using ${command_name}: $(command -v "$command_name")"
}

run_with_optional_timeout() {
  label="$1"
  shift

  printf '%s\n' "Running ${label}..."
  log "Working directory: ${PWD}"
  log "Command: $*"

  if command -v timeout >/dev/null 2>&1; then
    timeout "$TIMEOUT_SECONDS" "$@"
  else
    "$@"
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      print_help
      exit 0
      ;;
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    --wait)
      WAIT_ON_EXIT=1
      shift
      ;;
    --workdir)
      if [ "$#" -lt 2 ]; then
        fail "--workdir requires a directory argument"
        exit 2
      fi
      WORKDIR="$2"
      shift 2
      ;;
    --workdir=*)
      WORKDIR="${1#--workdir=}"
      shift
      ;;
    *)
      fail "unknown option: $1"
      printf '%s\n' "Run '${SCRIPT_NAME} --help' for usage." >&2
      exit 2
      ;;
  esac
done

if [ -z "$WORKDIR" ]; then
  fail "workdir must not be empty"
  exit 2
fi

if [ ! -d "$WORKDIR" ]; then
  fail "workdir does not exist: ${WORKDIR}"
  exit 2
fi

case "$TIMEOUT_SECONDS" in
  ''|*[!0-9]*)
    fail "TRIGGER_TIMEOUT_SECONDS must be a positive integer"
    exit 2
    ;;
esac

if [ "$TIMEOUT_SECONDS" -lt 1 ]; then
  fail "TRIGGER_TIMEOUT_SECONDS must be a positive integer"
  exit 2
fi

require_command sh || exit 127
require_command claude || exit 127
require_command codex || exit 127

cd "$WORKDIR" || {
  fail "could not enter workdir: ${WORKDIR}"
  exit 2
}

overall_status=0

if run_with_optional_timeout "Claude Code" claude -p "$PROMPT"; then
  printf '%s\n' "Claude Code check completed."
else
  status=$?
  fail "Claude Code check failed with exit code ${status}"
  overall_status=1
fi

cd "$WORKDIR" || {
  fail "could not re-enter workdir: ${WORKDIR}"
  exit 2
}

if run_with_optional_timeout "Codex" codex exec -C "$WORKDIR" "$PROMPT"; then
  printf '%s\n' "Codex check completed."
else
  status=$?
  fail "Codex check failed with exit code ${status}"
  overall_status=1
fi

if [ "$WAIT_ON_EXIT" -eq 1 ]; then
  printf '\n%s' "Press Enter to close..."
  read _unused_input || true
fi

exit "$overall_status"
