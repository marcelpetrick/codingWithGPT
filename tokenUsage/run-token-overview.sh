#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly TOOL_DIR="${SCRIPT_DIR}/.tools/tokenuse"
readonly RESULTS_DIR="${SCRIPT_DIR}/results"
readonly TIMINGS_FILE="${RESULTS_DIR}/timings.tsv"
readonly REPORT_YEAR="${1:-$(date +%Y)}"
readonly TOKENUSE_CONFIG_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/tokenuse"

if [[ ! "$REPORT_YEAR" =~ ^[0-9]{4}$ ]]; then
  printf 'Year must be four digits, for example: %s 2026\n' "$0" >&2
  exit 1
fi

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) asset="tokenuse-linux-amd64" ;;
  Linux-aarch64|Linux-arm64) asset="tokenuse-linux-arm64" ;;
  *)
    printf 'Unsupported platform: %s-%s\n' "$(uname -s)" "$(uname -m)" >&2
    printf 'Token Forest itself supports only Windows and macOS; this runner uses the Linux-compatible Token Use alternative.\n' >&2
    exit 1
    ;;
esac

mkdir -p "$TOOL_DIR" "$RESULTS_DIR"
readonly TOKENUSE_BIN="${TOOL_DIR}/tokenuse"

now_ns() {
  date +%s%N
}

run_timed() {
  local label="$1"
  local output="$2"
  shift 2
  local start_ns end_ns elapsed_ms
  start_ns="$(now_ns)"
  "$@" >"$output"
  end_ns="$(now_ns)"
  elapsed_ms=$(( (end_ns - start_ns) / 1000000 ))
  printf '%s\t%s\n' "$label" "$elapsed_ms" | tee -a "$TIMINGS_FILE"
}

if [[ ! -x "$TOKENUSE_BIN" ]]; then
  readonly base_url="https://github.com/russmckendrick/tokenuse/releases/latest/download"
  start_ns="$(now_ns)"
  curl --fail --location --silent --show-error \
    "${base_url}/${asset}" --output "${TOOL_DIR}/${asset}"
  curl --fail --location --silent --show-error \
    "${base_url}/${asset}.sha256" --output "${TOOL_DIR}/${asset}.sha256"
  (
    cd "$TOOL_DIR"
    sha256sum --check "${asset}.sha256"
  )
  chmod 0755 "${TOOL_DIR}/${asset}"
  mv "${TOOL_DIR}/${asset}" "$TOKENUSE_BIN"
  end_ns="$(now_ns)"
  install_ms=$(( (end_ns - start_ns) / 1000000 ))
else
  install_ms=0
fi

printf 'step\telapsed_ms\n' >"$TIMINGS_FILE"
printf 'install\t%s\n' "$install_ms" >>"$TIMINGS_FILE"
run_timed "doctor" "${RESULTS_DIR}/doctor.json" "$TOKENUSE_BIN" doctor --json
run_timed "overview_first" "${RESULTS_DIR}/overview.json" "$TOKENUSE_BIN" overview --json
run_timed "overview_repeat" "${RESULTS_DIR}/overview-repeat.json" "$TOKENUSE_BIN" overview --json
run_timed "render_html" "${RESULTS_DIR}/render.log" \
  python3 "${SCRIPT_DIR}/render-overview.py" \
  "${RESULTS_DIR}/overview.json" "${RESULTS_DIR}/overview.html"
run_timed "render_year" "${RESULTS_DIR}/render-year-${REPORT_YEAR}.log" \
  python3 "${SCRIPT_DIR}/render-yearly.py" \
  "${TOKENUSE_CONFIG_DIR}/archive.db" "$REPORT_YEAR" "$RESULTS_DIR"
if [[ -f "${HOME}/.claude/stats-cache.json" && -f "${HOME}/.codex/state_5.sqlite" ]]; then
  run_timed "render_linkedin" "${RESULTS_DIR}/render-linkedin-${REPORT_YEAR}.log" \
    python3 "${SCRIPT_DIR}/render-linkedin.py" \
    "${HOME}/.claude/stats-cache.json" "${HOME}/.codex/state_5.sqlite" \
    "$REPORT_YEAR" "${RESULTS_DIR}/linkedin-${REPORT_YEAR}.html"
fi
if command -v chromium >/dev/null 2>&1; then
  run_timed "render_year_png" "${RESULTS_DIR}/render-year-${REPORT_YEAR}-png.log" \
    chromium --headless --disable-gpu --no-sandbox --hide-scrollbars --log-level=3 \
    --window-size=1440,1400 \
    --screenshot="${RESULTS_DIR}/year-${REPORT_YEAR}.png" \
    "file://${RESULTS_DIR}/year-${REPORT_YEAR}.html"
  if [[ -f "${RESULTS_DIR}/linkedin-${REPORT_YEAR}.html" ]]; then
    run_timed "render_linkedin_png" "${RESULTS_DIR}/render-linkedin-${REPORT_YEAR}-png.log" \
      chromium --headless --disable-gpu --no-sandbox --hide-scrollbars --log-level=3 \
      --window-size=1200,1500 \
      --screenshot="${RESULTS_DIR}/linkedin-${REPORT_YEAR}.png" \
      "file://${RESULTS_DIR}/linkedin-${REPORT_YEAR}.html"
  fi
fi

printf '\nResults written to %s\n' "$RESULTS_DIR"
printf 'Open the one-command chart at: %s\n' "${RESULTS_DIR}/overview.html"
printf 'Open the monthly chart at: %s\n' "${RESULTS_DIR}/year-${REPORT_YEAR}.html"
if [[ -f "${RESULTS_DIR}/linkedin-${REPORT_YEAR}.html" ]]; then
  printf 'Open the LinkedIn chart at: %s\n' "${RESULTS_DIR}/linkedin-${REPORT_YEAR}.html"
fi
printf 'Open the interactive charts with: %s\n' "$TOKENUSE_BIN"
printf 'Generate an HTML/PDF/PNG report with: %s report\n' "$TOKENUSE_BIN"
