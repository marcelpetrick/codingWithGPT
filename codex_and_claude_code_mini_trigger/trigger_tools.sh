#!/bin/sh

set -u

SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
DEFAULT_WORKDIR=$(dirname -- "$SCRIPT_DIR")
PROMPT="Return only the result of 1+1."
CLAUDE_MODEL="${CLAUDE_TRIGGER_MODEL:-fable}"
CODEX_MODEL="${CODEX_TRIGGER_MODEL:-gpt-5.4-mini}"
CODEX_REASONING_EFFORT="${CODEX_TRIGGER_REASONING_EFFORT:-low}"
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
  CLAUDE_TRIGGER_MODEL
                       Claude Code model to use. Defaults to ${CLAUDE_MODEL}.
  CODEX_TRIGGER_MODEL
                       Codex model to use. Defaults to ${CODEX_MODEL}.
  CODEX_TRIGGER_REASONING_EFFORT
                       Codex reasoning effort. Defaults to ${CODEX_REASONING_EFFORT}.
  TRIGGER_TIMEOUT_SECONDS
                       Per-command timeout in seconds. Defaults to 300.

Examples:
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} --verbose
  ./${SCRIPT_NAME} --verbose --wait
  ./${SCRIPT_NAME} --workdir "\$HOME/projects/example"
  CODEX_TRIGGER_MODEL=gpt-5.4-mini ./${SCRIPT_NAME}
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
  if command -v timeout >/dev/null 2>&1; then
    timeout "$TIMEOUT_SECONDS" "$@"
  else
    "$@"
  fi
}

extract_json_usage() {
  label="$1"
  output_file="$2"

  if ! command -v jq >/dev/null 2>&1; then
    printf '%s\n' "${label} token usage: jq not found; raw output shown above."
    return
  fi

  usage_summary=$(jq -r '
    [
      paths(scalars) as $path
      | ($path | map(tostring) | join(".")) as $key
      | select($key | test("(?i)(token|usage|cost|duration|elapsed)"))
      | "\($key)=\(getpath($path))"
    ]
    | unique
    | .[]
  ' "$output_file" 2>/dev/null)

  if [ -n "$usage_summary" ]; then
    printf '%s\n' "${label} reported usage/statistics:"
    printf '%s\n' "$usage_summary" | sed 's/^/  /'
  else
    printf '%s\n' "${label} token usage: no machine-readable usage fields found in output."
  fi
}

run_tool() {
  label="$1"
  output_format="$2"
  shift
  shift

  output_file=$(mktemp "${TMPDIR:-/tmp}/trigger-tools.XXXXXX") || {
    fail "could not create temporary output file"
    return 2
  }

  start_epoch=$(date +%s)
  printf '\n%s\n' "=== ${label} ==="
  printf '%s\n' "Started at: $(date)"
  printf '%s\n' "Working directory: ${PWD}"
  printf '%s\n' "Timeout: ${TIMEOUT_SECONDS}s"
  log "Command: $*"

  run_with_optional_timeout "$@" >"$output_file" 2>&1
  status=$?
  end_epoch=$(date +%s)
  elapsed_seconds=$((end_epoch - start_epoch))

  printf '%s\n' "--- ${label} output ---"
  cat "$output_file"
  printf '%s\n' "--- ${label} summary ---"
  printf '%s\n' "Exit code: ${status}"
  printf '%s\n' "Wall clock: ${elapsed_seconds}s"

  if [ "$output_format" = "json" ]; then
    extract_json_usage "$label" "$output_file"
  elif [ "$output_format" = "jsonl" ]; then
    jsonl_file="${output_file}.jsonl"
    grep '^[[:space:]]*{' "$output_file" >"$jsonl_file" 2>/dev/null || true
    extract_json_usage "$label" "$jsonl_file"
    rm -f "$jsonl_file"
  fi

  rm -f "$output_file"
  return "$status"
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

printf '%s\n' "Trigger workdir: ${WORKDIR}"
printf '%s\n' "Claude Code model: ${CLAUDE_MODEL}"
printf '%s\n' "Codex model: ${CODEX_MODEL}"
printf '%s\n' "Codex reasoning effort: ${CODEX_REASONING_EFFORT}"
printf '%s\n' "Prompt: ${PROMPT}"

cd "$WORKDIR" || {
  fail "could not enter workdir: ${WORKDIR}"
  exit 2
}

overall_status=0

if run_tool "Claude Code" json claude -p --model "$CLAUDE_MODEL" --output-format json --no-session-persistence "$PROMPT"; then
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

if run_tool "Codex" jsonl codex exec -m "$CODEX_MODEL" -c "model_reasoning_effort=\"${CODEX_REASONING_EFFORT}\"" --json -C "$WORKDIR" "$PROMPT"; then
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
