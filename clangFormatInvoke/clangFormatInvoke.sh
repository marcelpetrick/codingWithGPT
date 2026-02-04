#!/usr/bin/env bash
set -euo pipefail

# clang-format-parallel.sh
# Recursively finds C/C++ headers/sources and runs clang-format in parallel.
# Prints detected CPU count, supports --numthread=N override,
# prints the exact clang-format call executed by each worker, and reports wall time.

NUMTHREAD=""
ROOT="."

usage() {
  cat <<'EOF'
Usage:
  clang-format-parallel.sh [--numthread=N] [path]

Examples:
  ./clang-format-parallel.sh
  ./clang-format-parallel.sh --numthread=20
  ./clang-format-parallel.sh --numthread=10 ./src
EOF
}

# --- arg parsing ---
for arg in "$@"; do
  case "$arg" in
    --numthread=*)
      NUMTHREAD="${arg#*=}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      # last non-option becomes ROOT (simple + practical)
      if [[ "$arg" != --* ]]; then
        ROOT="$arg"
      else
        echo "Unknown option: $arg" >&2
        usage >&2
        exit 2
      fi
      ;;
  esac
done

if ! command -v clang-format >/dev/null 2>&1; then
  echo "ERROR: clang-format not found in PATH." >&2
  exit 127
fi

if ! command -v nproc >/dev/null 2>&1; then
  echo "ERROR: nproc not found (coreutils)."
  exit 127
fi

CPU_ALL="$(nproc --all)"
CPU_AVAIL="$(nproc)"

if [[ -z "${NUMTHREAD}" ]]; then
  NUMTHREAD="$CPU_AVAIL"
fi

if ! [[ "$NUMTHREAD" =~ ^[0-9]+$ ]] || [[ "$NUMTHREAD" -le 0 ]]; then
  echo "ERROR: --numthread must be a positive integer, got: '$NUMTHREAD'" >&2
  exit 2
fi

echo "Detected processors: nproc (available) = $CPU_AVAIL, nproc --all = $CPU_ALL"
echo "Using clang-format workers: $NUMTHREAD"
echo "Root: $ROOT"
echo

# Collect files (NUL-delimited) so we can count and also feed xargs reliably.
tmp_list="$(mktemp)"
trap 'rm -f "$tmp_list"' EXIT

find "$ROOT" -type f \( -iname '*.h' -o -iname '*.hpp' -o -iname '*.c' -o -iname '*.cc' -o -iname '*.cpp' \) -print0 >"$tmp_list"

# Count NUL-separated entries
FILECOUNT="$(tr -cd '\0' <"$tmp_list" | wc -c)"
echo "Files matched: $FILECOUNT"
if [[ "$FILECOUNT" -eq 0 ]]; then
  echo "Nothing to do."
  exit 0
fi
echo

# Wall-clock timer (GNU date on Manjaro supports %N)
start_ns="$(date +%s%N)"

# Run: one file per job, up to NUMTHREAD jobs in parallel.
# Each worker prints the exact call it is about to run, tagged by PID.
cat "$tmp_list" \
  | xargs -0 -r -n 1 -P "$NUMTHREAD" bash -c '
      set -euo pipefail
      f="$1"
      echo "[pid $$] clang-format -i -- \"$f\""
      clang-format -i -- "$f"
    ' _

end_ns="$(date +%s%N)"
elapsed_ns=$((end_ns - start_ns))

# Format elapsed time nicely
elapsed_s=$((elapsed_ns / 1000000000))
elapsed_ms=$(((elapsed_ns / 1000000) % 1000))

echo
echo "Done."
echo "Wall-clock time: ${elapsed_s}.${elapsed_ms}s"
