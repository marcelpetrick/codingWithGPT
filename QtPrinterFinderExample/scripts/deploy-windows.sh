#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${1:-$repo_root/build-win}"
deploy_dir="${2:-$repo_root/dist/windows}"
triplet="${WINDOWS_MINGW_TRIPLET:-x86_64-w64-mingw32}"

if [[ -n "${WINDOWS_MINGW_BIN:-}" ]]; then
    export PATH="$WINDOWS_MINGW_BIN:$PATH"
fi

if [[ -n "${MXE_PREFIX:-}" && -z "${WINDOWS_QT_PREFIX:-}" ]]; then
    qt_prefix="$MXE_PREFIX/usr/$triplet/qt5"
else
    qt_prefix="${WINDOWS_QT_PREFIX:-}"
fi

target_prefix=""
if [[ -n "${MXE_PREFIX:-}" ]]; then
    target_prefix="$MXE_PREFIX/usr/$triplet"
fi
objdump="${WINDOWS_OBJDUMP:-${triplet}-objdump}"

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
mkdir -p "$deploy_dir/printsupport"
cp "$exe" "$deploy_dir/"

copy_first_found() {
    local name="$1"
    local quiet="${2:-0}"
    local found=""
    for prefix in "$qt_prefix" "$target_prefix"; do
        [[ -n "$prefix" && -d "$prefix" ]] || continue
        while IFS= read -r candidate; do
            found="$candidate"
            break
        done < <(find "$prefix" -type f -iname "$name" 2>/dev/null)
        [[ -n "$found" ]] && break
    done

    if [[ -n "$found" ]]; then
        cp "$found" "$deploy_dir/"
        printf 'copied: %s\n' "$name"
    else
        if [[ "$quiet" != "1" ]]; then
            printf 'warn: not found: %s\n' "$name" >&2
        fi
    fi
}

find_first() {
    local pattern="$1"
    local found=""
    for prefix in "$qt_prefix" "$target_prefix"; do
        [[ -n "$prefix" && -d "$prefix" ]] || continue
        while IFS= read -r candidate; do
            found="$candidate"
            break
        done < <(find "$prefix" -type f -path "$pattern" 2>/dev/null)
        [[ -n "$found" ]] && break
    done
    printf '%s' "$found"
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

qwindows="$(find_first '*/plugins/platforms/qwindows.dll')"

if [[ -z "$qwindows" ]]; then
    printf 'missing Qt platform plugin: qwindows.dll\n' >&2
    exit 1
fi

cp "$qwindows" "$deploy_dir/platforms/"
printf 'copied: platforms/qwindows.dll\n'

printer_plugin="$(find_first '*/plugins/printsupport/windowsprintersupport.dll')"
if [[ -n "$printer_plugin" ]]; then
    cp "$printer_plugin" "$deploy_dir/printsupport/"
    printf 'copied: printsupport/windowsprintersupport.dll\n'
else
    printf 'warn: not found: printsupport/windowsprintersupport.dll\n' >&2
fi

if command -v "$objdump" >/dev/null 2>&1; then
    declare -A seen
    while :; do
        copied_any=0
        while IFS= read -r binary; do
            while IFS= read -r dll; do
                [[ -n "$dll" ]] || continue
                key="${dll,,}"
                [[ -n "${seen[$key]:-}" ]] && continue
                seen[$key]=1

                if [[ -f "$deploy_dir/$dll" ]]; then
                    continue
                fi

                before_count="$(find "$deploy_dir" -type f | wc -l)"
                copy_first_found "$dll" 1 >/dev/null
                after_count="$(find "$deploy_dir" -type f | wc -l)"
                if [[ "$after_count" != "$before_count" && -f "$deploy_dir/$dll" ]]; then
                    copied_any=1
                    printf 'copied dependency: %s\n' "$dll"
                fi
            done < <("$objdump" -p "$binary" 2>/dev/null | sed -n 's/^[[:space:]]*DLL Name: //p')
        done < <(find "$deploy_dir" -type f \( -iname '*.exe' -o -iname '*.dll' \))

        [[ "$copied_any" -eq 0 ]] && break
    done
else
    printf 'warn: objdump not found: %s; recursive DLL dependency scan skipped\n' "$objdump" >&2
fi

printf 'deployment bundle: %s\n' "$deploy_dir"
