#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${1:-$repo_root/build-win}"
deploy_dir="${2:-$repo_root/dist/windows}"
triplet="${WINDOWS_MINGW_TRIPLET:-x86_64-w64-mingw32}"

if [[ -n "${MXE_PREFIX:-}" && -z "${WINDOWS_QT_PREFIX:-}" ]]; then
    qt_prefix="$MXE_PREFIX/usr/$triplet/qt5"
else
    qt_prefix="${WINDOWS_QT_PREFIX:-}"
fi

target_prefix=""
if [[ -n "${MXE_PREFIX:-}" ]]; then
    target_prefix="$MXE_PREFIX/usr/$triplet"
fi

exe="$build_dir/QtPrinterFinderExample.exe"
if [[ ! -f "$exe" ]]; then
    printf 'missing executable: %s\n' "$exe" >&2
    exit 1
fi

if [[ -z "$qt_prefix" || ! -d "$qt_prefix" ]]; then
    printf 'missing Windows Qt prefix. Set WINDOWS_QT_PREFIX or MXE_PREFIX.\n' >&2
    exit 1
fi

mkdir -p "$deploy_dir/platforms"
cp "$exe" "$deploy_dir/"

copy_first_found() {
    local name="$1"
    local found=""
    for prefix in "$qt_prefix" "$target_prefix"; do
        [[ -n "$prefix" && -d "$prefix" ]] || continue
        while IFS= read -r candidate; do
            found="$candidate"
            break
        done < <(find "$prefix" -type f -name "$name" 2>/dev/null)
        [[ -n "$found" ]] && break
    done

    if [[ -n "$found" ]]; then
        cp "$found" "$deploy_dir/"
        printf 'copied: %s\n' "$name"
    else
        printf 'warn: not found: %s\n' "$name" >&2
    fi
}

for dll in \
    Qt5Core.dll \
    Qt5Gui.dll \
    Qt5Widgets.dll \
    Qt5PrintSupport.dll \
    Qt5Network.dll \
    libgcc_s_seh-1.dll \
    libstdc++-6.dll \
    libwinpthread-1.dll; do
    copy_first_found "$dll"
done

qwindows=""
while IFS= read -r candidate; do
    qwindows="$candidate"
    break
done < <(find "$qt_prefix" -type f -path '*/plugins/platforms/qwindows.dll' 2>/dev/null)

if [[ -z "$qwindows" ]]; then
    printf 'missing Qt platform plugin: qwindows.dll\n' >&2
    exit 1
fi

cp "$qwindows" "$deploy_dir/platforms/"
printf 'copied: platforms/qwindows.dll\n'
printf 'deployment bundle: %s\n' "$deploy_dir"
