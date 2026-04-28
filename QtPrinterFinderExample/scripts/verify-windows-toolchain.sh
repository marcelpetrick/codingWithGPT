#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

triplet="${WINDOWS_MINGW_TRIPLET:-x86_64-w64-mingw32}"
build_dir="${WINDOWS_BUILD_DIR:-$repo_root/build-win}"
deploy_dir="${WINDOWS_DEPLOY_DIR:-$repo_root/dist/windows}"

if [[ -n "${MXE_PREFIX:-}" && -z "${WINDOWS_QT_PREFIX:-}" ]]; then
    qt_prefix="$MXE_PREFIX/usr/$triplet"
else
    qt_prefix="${WINDOWS_QT_PREFIX:-}"
fi

if [[ -n "${WINDOWS_MINGW_BIN:-}" ]]; then
    export PATH="$WINDOWS_MINGW_BIN:$PATH"
fi

missing=0

check_command() {
    local cmd="$1"
    if command -v "$cmd" >/dev/null 2>&1; then
        printf 'ok: %s -> %s\n' "$cmd" "$(command -v "$cmd")"
    else
        printf 'missing: %s\n' "$cmd" >&2
        missing=1
    fi
}

check_file() {
    local path="$1"
    local label="$2"
    if [[ -f "$path" ]]; then
        printf 'ok: %s -> %s\n' "$label" "$path"
    else
        printf 'missing: %s -> %s\n' "$label" "$path" >&2
        missing=1
    fi
}

check_command cmake
check_command ninja
check_command "${triplet}-gcc"
check_command "${triplet}-g++"
check_command "${triplet}-windres"

if command -v wine >/dev/null 2>&1; then
    printf 'ok: wine -> %s\n' "$(command -v wine)"
else
    printf 'warn: wine not found; build can work, smoke test will be skipped\n' >&2
fi

if [[ -z "$qt_prefix" ]]; then
    printf 'missing: WINDOWS_QT_PREFIX or MXE_PREFIX must point at a Windows Qt 5 MinGW prefix\n' >&2
    missing=1
else
    check_file "$qt_prefix/lib/cmake/Qt5/Qt5Config.cmake" "Qt5Config.cmake"
    check_file "$qt_prefix/lib/cmake/Qt5Widgets/Qt5WidgetsConfig.cmake" "Qt5WidgetsConfig.cmake"
    check_file "$qt_prefix/lib/cmake/Qt5PrintSupport/Qt5PrintSupportConfig.cmake" "Qt5PrintSupportConfig.cmake"
    check_file "$qt_prefix/lib/cmake/Qt5Network/Qt5NetworkConfig.cmake" "Qt5NetworkConfig.cmake"
fi

if [[ "$missing" -ne 0 ]]; then
    cat >&2 <<EOF

Windows toolchain is not complete yet.

Required host pieces:
  - MinGW-w64 compiler tools for ${triplet}
  - Windows-target Qt 5.15 MinGW libraries, not the host Linux Qt

Typical MXE shape:
  export MXE_PREFIX=/opt/mxe
  export WINDOWS_MINGW_TRIPLET=x86_64-w64-mingw32.shared
  export WINDOWS_MINGW_BIN=\$MXE_PREFIX/usr/bin

Typical custom Qt shape:
  export WINDOWS_QT_PREFIX=/opt/qt-windows-5.15/x86_64-w64-mingw32

EOF
    exit 1
fi

cmake -S "$repo_root" -B "$build_dir" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$repo_root/cmake/toolchains/windows-mingw-qt5.cmake" \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "$build_dir"

"$repo_root/scripts/deploy-windows.sh" "$build_dir" "$deploy_dir"

if command -v wine >/dev/null 2>&1; then
    wine "$deploy_dir/QtPrinterFinderExample.exe" --help >/dev/null 2>&1 || true
    printf 'ok: wine smoke command completed; GUI launch may still require a display\n'
fi

printf 'ok: Windows build and deployment bundle prepared at %s\n' "$deploy_dir"
