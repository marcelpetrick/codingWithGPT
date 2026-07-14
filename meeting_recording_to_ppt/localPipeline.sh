#!/usr/bin/env bash
set -u
set -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON="${VENV_DIR}/bin/python"
INSTALL_TRANSCRIPT_DEPS=true
WITH_REAL_VIDEO=false
REPORT_DIR=""
PIPELINE_LOG_DIR=""
REMOVE_PIPELINE_LOG_DIR=true

declare -a SUMMARY_LINES=()

PREREQS_OK=0
VENV_OK=0
CORE_INSTALL_OK=0
DEV_INSTALL_OK=0
TRANSCRIPT_INSTALL_OK=0
TESTS_OK=0
OPEN_COVERAGE_OK=0
CLI_SMOKE_OK=0
E2E_SMOKE_OK=0
REAL_VIDEO_OK=0
OPEN_REPORT_COMMAND=""
TESTS_DETAILS=""
E2E_SMOKE_DETAILS=""
REAL_VIDEO_DETAILS=""

print_usage() {
    cat <<EOF
Usage: ./localPipeline.sh [--no-transcript] [--with-real-video] [--report-dir PATH]

Local project pipeline:
  1. Check that ffmpeg/ffprobe are on PATH
  2. Create or reuse .venv
  3. Install core dependencies (requirements.txt)
  4. Install dev/test dependencies (requirements-dev.txt)
  5. Install optional transcript dependencies (requirements-transcript.txt)
     Use --no-transcript to skip this (faster, no faster-whisper download)
  6. Run pytest with coverage and generate htmlcov/index.html
  7. Open the generated coverage report when possible
  8. Smoke-check the CLI (--help / argument parsing)
  9. End-to-end smoke test against a small synthetically generated clip
     (green-bordered box with two distinct slides), so the pipeline never
     depends on any private recording being present
  10. Optionally (--with-real-video) also run the full pipeline against a
      real .mkv/.mp4 recording found in this directory, purely as an
      informational check -- never required for the pipeline to pass
  11. Print a final stage-by-stage summary

Generated HTML reports are opened with MEETING_RECORDING_TO_PPT_REPORT_BROWSER
when set, then firefox, then xdg-open, then open.

Use --report-dir to preserve stage logs, JUnit XML, coverage XML, and the
final summary. Without it, those trace files are temporary.
EOF
}

log() {
    printf '[INFO] %s\n' "$*"
}

warn() {
    printf '[WARN] %s\n' "$*" >&2
}

error() {
    printf '[ERROR] %s\n' "$*" >&2
}

mark_result() {
    local label="$1"
    local status="$2"
    local details="$3"
    SUMMARY_LINES+=("$(printf '%-16s : %-4s %s' "${label}" "${status}" "${details}")")
}

run_with_log() {
    local log_path="$1"
    shift

    mkdir -p "${PIPELINE_LOG_DIR}"
    "$@" 2>&1 | tee "${log_path}"
    return "${PIPESTATUS[0]}"
}

extract_test_details() {
    local log_path="$1"
    local coverage_line
    local result_line

    coverage_line="$(grep -E "^TOTAL .*[0-9]+%" "${log_path}" | tail -n 1 || true)"
    result_line="$(grep -E "=+ .*(passed|failed|skipped|error).*=+" "${log_path}" | tail -n 1 || true)"
    result_line="${result_line//=/}"
    result_line="${result_line#"${result_line%%[![:space:]]*}"}"
    result_line="${result_line%"${result_line##*[![:space:]]}"}"

    local coverage_pct=""
    if [[ -n "${coverage_line}" ]]; then
        coverage_pct="$(printf '%s\n' "${coverage_line}" | awk '{print $NF}') coverage"
    fi

    if [[ -n "${coverage_pct}" && -n "${result_line}" ]]; then
        printf '%s; %s\n' "${result_line}" "${coverage_pct}"
        return
    fi
    if [[ -n "${result_line}" ]]; then
        printf '%s\n' "${result_line}"
        return
    fi

    printf '%s\n' "see pytest output"
}

print_summary() {
    {
        printf '\n========== Local Pipeline Summary ==========\n'
        local line
        for line in "${SUMMARY_LINES[@]}"; do
            printf '%s\n' "${line}"
        done
        printf '============================================\n'
    } | tee "${PIPELINE_LOG_DIR}/summary.txt"
}

detect_open_command() {
    if [[ -n "${MEETING_RECORDING_TO_PPT_REPORT_BROWSER:-}" ]]; then
        printf '%s\n' "${MEETING_RECORDING_TO_PPT_REPORT_BROWSER}"
    fi

    printf '%s\n' "firefox"
    printf '%s\n' "xdg-open"
    printf '%s\n' "open"
}

open_html_report() {
    local report_label="$1"
    local report_path="$2"
    local open_command=""
    local opener_pid=0

    if [[ ! -f "${report_path}" ]]; then
        warn "${report_label} was not found: ${report_path}"
        return 1
    fi

    log "${report_label}: ${report_path}"
    while IFS= read -r open_command; do
        if [[ -z "${open_command}" ]]; then
            continue
        fi
        if ! command -v "${open_command}" >/dev/null 2>&1; then
            continue
        fi
        log "Opening ${report_label} with '${open_command}'."
        "${open_command}" "${report_path}" >/dev/null 2>&1 &
        opener_pid=$!

        sleep 1
        if kill -0 "${opener_pid}" >/dev/null 2>&1; then
            disown "${opener_pid}" >/dev/null 2>&1 || true
            OPEN_REPORT_COMMAND="${open_command}"
            return 0
        fi

        if wait "${opener_pid}"; then
            OPEN_REPORT_COMMAND="${open_command}"
            return 0
        fi
        warn "Could not open ${report_label} with '${open_command}'. Trying next opener."
    done < <(detect_open_command)

    warn "No supported opener could open ${report_label}. Open it manually at: ${report_path}"
    return 1
}

parse_arguments() {
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            --no-transcript)
                INSTALL_TRANSCRIPT_DEPS=false
                shift
                ;;
            --with-real-video)
                WITH_REAL_VIDEO=true
                shift
                ;;
            --report-dir)
                if [[ "$#" -lt 2 || -z "$2" ]]; then
                    error "--report-dir requires a path."
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

prepare_report_directory() {
    if [[ -n "${REPORT_DIR}" ]]; then
        PIPELINE_LOG_DIR="$(realpath -m "${REPORT_DIR}")"
        REMOVE_PIPELINE_LOG_DIR=false
    else
        PIPELINE_LOG_DIR="${TMPDIR:-/tmp}/meeting-recording-to-ppt-pipeline-$$"
    fi

    mkdir -p "${PIPELINE_LOG_DIR}"
    rm -f \
        "${PIPELINE_LOG_DIR}/core-dependencies.log" \
        "${PIPELINE_LOG_DIR}/dev-dependencies.log" \
        "${PIPELINE_LOG_DIR}/transcript-dependencies.log" \
        "${PIPELINE_LOG_DIR}/pytest.log" \
        "${PIPELINE_LOG_DIR}/coverage.xml" \
        "${PIPELINE_LOG_DIR}/junit.xml" \
        "${PIPELINE_LOG_DIR}/cli-smoke.log" \
        "${PIPELINE_LOG_DIR}/e2e-smoke.log" \
        "${PIPELINE_LOG_DIR}/real-video.log" \
        "${PIPELINE_LOG_DIR}/summary.txt"
    trap 'if [[ "${REMOVE_PIPELINE_LOG_DIR}" == true ]]; then rm -rf "${PIPELINE_LOG_DIR}"; fi' EXIT
}

check_prerequisites() {
    log "Checking for ffmpeg/ffprobe on PATH."
    if ! command -v ffmpeg >/dev/null 2>&1; then
        error "ffmpeg was not found on PATH."
        return 1
    fi
    if ! command -v ffprobe >/dev/null 2>&1; then
        error "ffprobe was not found on PATH."
        return 1
    fi
    return 0
}

prepare_virtual_environment() {
    if [[ -x "${PYTHON}" ]]; then
        log "Using existing virtual environment: ${VENV_DIR}"
        return 0
    fi

    log "Creating virtual environment: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
}

install_core_dependencies() {
    log "Installing core dependencies (requirements.txt)."
    run_with_log "${PIPELINE_LOG_DIR}/core-dependencies.log" \
        "${PYTHON}" -m pip install -r "${ROOT_DIR}/requirements.txt"
}

install_dev_dependencies() {
    log "Installing dev/test dependencies (requirements-dev.txt)."
    run_with_log "${PIPELINE_LOG_DIR}/dev-dependencies.log" \
        "${PYTHON}" -m pip install -r "${ROOT_DIR}/requirements-dev.txt"
}

install_transcript_dependencies() {
    log "Installing optional transcript dependencies (requirements-transcript.txt)."
    run_with_log "${PIPELINE_LOG_DIR}/transcript-dependencies.log" \
        "${PYTHON}" -m pip install -r "${ROOT_DIR}/requirements-transcript.txt"
}

run_tests_with_coverage() {
    log "Running pytest with coverage."
    local log_path="${PIPELINE_LOG_DIR}/pytest.log"

    if run_with_log \
        "${log_path}" \
        "${PYTHON}" -m pytest \
        --junitxml="${PIPELINE_LOG_DIR}/junit.xml" \
        --cov=slide_extractor \
        --cov-report="term-missing" \
        --cov-report="html:${ROOT_DIR}/htmlcov" \
        --cov-report="xml:${PIPELINE_LOG_DIR}/coverage.xml"; then
        TESTS_DETAILS="$(extract_test_details "${log_path}")"
        return 0
    fi

    TESTS_DETAILS="$(extract_test_details "${log_path}")"
    return 1
}

open_coverage_report() {
    local coverage_index="${ROOT_DIR}/htmlcov/index.html"
    open_html_report "Coverage report" "${coverage_index}"
}

run_cli_smoke_check() {
    log "Smoke-checking the CLI (--help)."
    run_with_log "${PIPELINE_LOG_DIR}/cli-smoke.log" \
        "${PYTHON}" -m slide_extractor --help
}

run_end_to_end_smoke_test() {
    log "Running an end-to-end smoke test against a small synthetic clip."
    local log_path="${PIPELINE_LOG_DIR}/e2e-smoke.log"
    local work_dir="${PIPELINE_LOG_DIR}/e2e-smoke"
    rm -rf "${work_dir}"
    mkdir -p "${work_dir}"

    {
        "${PYTHON}" - "${work_dir}" <<'PYEOF'
import subprocess
import sys
from pathlib import Path

import numpy as np

work_dir = Path(sys.argv[1])
width, height, fps, seconds_per_slide = 640, 360, 5, 2
green = (40, 200, 40)


def draw_border(frame, left, right, top, bottom, color, thickness=3):
    frame[top:top + thickness, left:right] = color
    frame[bottom - thickness:bottom, left:right] = color
    frame[top:bottom, left:left + thickness] = color
    frame[top:bottom, right - thickness:right] = color


def make_frame(interior_color, seed):
    frame = np.full((height, width, 3), (15, 15, 15), dtype=np.uint8)
    left, right, top, bottom = 40, 600, 40, 320
    draw_border(frame, left, right, top, bottom, green)
    frame[top + 4:bottom - 4, left + 4:right - 4] = interior_color
    rng = np.random.default_rng(seed)
    ys = rng.integers(top + 10, bottom - 10, size=300)
    xs = rng.integers(left + 10, right - 10, size=300)
    frame[ys, xs] = (0, 0, 0)
    return frame


frames = (
    [make_frame((255, 255, 255), 1) for _ in range(fps * seconds_per_slide)]
    + [make_frame((60, 90, 220), 2) for _ in range(fps * seconds_per_slide)]
)

clip_path = work_dir / "synthetic_recording.mp4"
cmd = [
    "ffmpeg", "-y",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
    "-i", "-",
    "-pix_fmt", "yuv420p",
    "-loglevel", "error",
    str(clip_path),
]
payload = b"".join(f.tobytes() for f in frames)
subprocess.run(cmd, input=payload, check=True)
print(f"Generated synthetic clip: {clip_path}")
PYEOF
    } 2>&1 | tee "${log_path}"
    local generate_status="${PIPESTATUS[0]}"
    if [[ "${generate_status}" -ne 0 ]]; then
        return 1
    fi

    {
        "${PYTHON}" -m slide_extractor \
            "${work_dir}/synthetic_recording.mp4" \
            -o "${work_dir}/slides_output" \
            --interval 0.4 \
            --top-trim-px 0 \
            --border-inset-px 5 \
            --min-sharpness 0.00001
    } 2>&1 | tee -a "${log_path}"
    local run_status="${PIPESTATUS[0]}"
    if [[ "${run_status}" -ne 0 ]]; then
        return 1
    fi

    local slide_count
    slide_count="$(find "${work_dir}/slides_output" -maxdepth 1 -name 'slide_*.png' | wc -l | tr -d ' ')"
    E2E_SMOKE_DETAILS="${slide_count} slide(s) extracted from synthetic clip"

    if [[ "${slide_count}" -lt 1 ]]; then
        error "Expected at least 1 slide from the synthetic clip, got ${slide_count}."
        return 1
    fi
    if [[ ! -f "${work_dir}/slides_output/manifest.json" ]]; then
        error "manifest.json was not produced."
        return 1
    fi
    return 0
}

find_real_video() {
    find "${ROOT_DIR}" -maxdepth 1 -type f \( -iname '*.mkv' -o -iname '*.mp4' \) -print -quit
}

run_real_video_check() {
    local video_path="$1"
    log "Running the pipeline against a real recording found in this directory (informational only)."
    local log_path="${PIPELINE_LOG_DIR}/real-video.log"
    local work_dir="${PIPELINE_LOG_DIR}/real-video-output"
    rm -rf "${work_dir}"

    if run_with_log \
        "${log_path}" \
        "${PYTHON}" -m slide_extractor "${video_path}" -o "${work_dir}" --interval 2; then
        local slide_count
        slide_count="$(find "${work_dir}" -maxdepth 1 -name 'slide_*.png' | wc -l | tr -d ' ')"
        REAL_VIDEO_DETAILS="${slide_count} slide(s) extracted from $(basename "${video_path}")"
        return 0
    fi

    REAL_VIDEO_DETAILS="pipeline run against $(basename "${video_path}") failed"
    return 1
}

main() {
    local exit_code=1

    parse_arguments "$@"
    prepare_report_directory

    if check_prerequisites; then
        PREREQS_OK=1
        mark_result "Prerequisites" "PASS" "ffmpeg and ffprobe are on PATH"
    else
        mark_result "Prerequisites" "FAIL" "ffmpeg/ffprobe missing from PATH"
    fi

    if [[ "${PREREQS_OK}" -eq 1 ]]; then
        if prepare_virtual_environment; then
            VENV_OK=1
            mark_result "Virtualenv" "PASS" ".venv is available"
        else
            mark_result "Virtualenv" "FAIL" "Could not create or reuse .venv"
        fi
    else
        mark_result "Virtualenv" "SKIP" "Skipped because prerequisites are missing"
    fi

    if [[ "${VENV_OK}" -eq 1 ]]; then
        if install_core_dependencies; then
            CORE_INSTALL_OK=1
            mark_result "Core Deps" "PASS" "numpy, Pillow, scikit-image installed"
        else
            mark_result "Core Deps" "FAIL" "Core dependency installation failed"
        fi
    else
        mark_result "Core Deps" "SKIP" "Skipped because .venv is unavailable"
    fi

    if [[ "${CORE_INSTALL_OK}" -eq 1 ]]; then
        if install_dev_dependencies; then
            DEV_INSTALL_OK=1
            mark_result "Dev Deps" "PASS" "pytest, pytest-cov installed"
        else
            mark_result "Dev Deps" "FAIL" "Dev dependency installation failed"
        fi
    else
        mark_result "Dev Deps" "SKIP" "Skipped because core dependencies are unavailable"
    fi

    if [[ "${INSTALL_TRANSCRIPT_DEPS}" == true ]]; then
        if [[ "${CORE_INSTALL_OK}" -eq 1 ]]; then
            if install_transcript_dependencies; then
                TRANSCRIPT_INSTALL_OK=1
                mark_result "Transcript Deps" "PASS" "faster-whisper installed"
            else
                mark_result "Transcript Deps" "FAIL" "Transcript dependency installation failed"
            fi
        else
            mark_result "Transcript Deps" "SKIP" "Skipped because core dependencies are unavailable"
        fi
    else
        mark_result "Transcript Deps" "SKIP" "Skipped by --no-transcript"
    fi

    if [[ "${DEV_INSTALL_OK}" -eq 1 ]]; then
        if run_tests_with_coverage; then
            TESTS_OK=1
            mark_result "Tests+Coverage" "PASS" "${TESTS_DETAILS}"
        else
            mark_result "Tests+Coverage" "FAIL" "${TESTS_DETAILS}"
        fi
    else
        mark_result "Tests+Coverage" "SKIP" "Skipped because dev dependencies are unavailable"
    fi

    if [[ "${TESTS_OK}" -eq 1 ]]; then
        OPEN_REPORT_COMMAND=""
        if open_coverage_report; then
            OPEN_COVERAGE_OK=1
            mark_result "Open Coverage" "PASS" "htmlcov/index.html was handed to ${OPEN_REPORT_COMMAND}"
        else
            mark_result "Open Coverage" "WARN" "Coverage path was printed but auto-open was unavailable or failed"
        fi
    else
        mark_result "Open Coverage" "SKIP" "Skipped because coverage was not generated"
    fi

    if [[ "${CORE_INSTALL_OK}" -eq 1 ]]; then
        if run_cli_smoke_check; then
            CLI_SMOKE_OK=1
            mark_result "CLI Smoke" "PASS" "python -m slide_extractor --help exits cleanly"
        else
            mark_result "CLI Smoke" "FAIL" "CLI --help failed"
        fi
    else
        mark_result "CLI Smoke" "SKIP" "Skipped because core dependencies are unavailable"
    fi

    if [[ "${CLI_SMOKE_OK}" -eq 1 ]]; then
        if run_end_to_end_smoke_test; then
            E2E_SMOKE_OK=1
            mark_result "E2E Smoke" "PASS" "${E2E_SMOKE_DETAILS}"
        else
            mark_result "E2E Smoke" "FAIL" "${E2E_SMOKE_DETAILS:-see e2e-smoke.log}"
        fi
    else
        mark_result "E2E Smoke" "SKIP" "Skipped because the CLI smoke check failed"
    fi

    if [[ "${WITH_REAL_VIDEO}" == true ]]; then
        if [[ "${E2E_SMOKE_OK}" -eq 1 ]]; then
            local real_video=""
            real_video="$(find_real_video)"
            if [[ -n "${real_video}" ]]; then
                if run_real_video_check "${real_video}"; then
                    REAL_VIDEO_OK=1
                    mark_result "Real Video" "PASS" "${REAL_VIDEO_DETAILS}"
                else
                    mark_result "Real Video" "WARN" "${REAL_VIDEO_DETAILS}"
                fi
            else
                mark_result "Real Video" "SKIP" "No .mkv/.mp4 recording found in ${ROOT_DIR}"
            fi
        else
            mark_result "Real Video" "SKIP" "Skipped because the synthetic smoke test failed"
        fi
    else
        mark_result "Real Video" "SKIP" "Suppressed; pass --with-real-video to enable"
    fi

    if [[ "${PREREQS_OK}" -eq 1 && "${VENV_OK}" -eq 1 && "${CORE_INSTALL_OK}" -eq 1 && "${DEV_INSTALL_OK}" -eq 1 && "${TESTS_OK}" -eq 1 && "${CLI_SMOKE_OK}" -eq 1 && "${E2E_SMOKE_OK}" -eq 1 ]]; then
        if [[ "${INSTALL_TRANSCRIPT_DEPS}" == false || "${TRANSCRIPT_INSTALL_OK}" -eq 1 ]]; then
            exit_code=0
        fi
    fi

    if [[ "${exit_code}" -eq 0 ]]; then
        log "localPipeline.sh completed successfully"
    else
        error "localPipeline.sh completed with failing mandatory stage(s)"
    fi
    print_summary
    exit "${exit_code}"
}

main "$@"
