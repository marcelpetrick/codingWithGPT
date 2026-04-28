#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MXE_PREFIX="${MXE_PREFIX:-/opt/mxe}"
TRIPLET="${WINDOWS_MINGW_TRIPLET:-x86_64-w64-mingw32.shared}"
JOBS="${JOBS:-$(nproc)}"

ok() { printf '\033[32mok\033[0m: %s\n' "$*"; }
warn() { printf '\033[33mwarn\033[0m: %s\n' "$*"; }
fail() { printf '\033[31mfail\033[0m: %s\n' "$*"; }
step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

run() {
    printf '+ %s\n' "$*"
    "$@"
}

need_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        fail "run this script with sudo/root for package install and /opt/mxe setup"
        printf 'try: sudo ./setup-windows-toolchain.sh\n'
        exit 1
    fi
}

check_cmd() {
    if command -v "$1" >/dev/null 2>&1; then
        ok "$1 -> $(command -v "$1")"
        return 0
    fi
    fail "missing command: $1"
    return 1
}

need_root

ORIGINAL_USER="${SUDO_USER:-$USER}"
ORIGINAL_HOME="$(getent passwd "$ORIGINAL_USER" | cut -d: -f6)"

step "Install Manjaro host packages"
run pacman -S --needed \
    base-devel \
    git \
    cmake \
    ninja \
    mingw-w64-gcc \
    mingw-w64-crt \
    mingw-w64-headers \
    wine \
    gperf \
    intltool \
    lzip \
    python-mako \
    python-setuptools \
    ruby \
    unzip

step "Check host commands"
missing=0
for cmd in cmake ninja git wine x86_64-w64-mingw32-gcc x86_64-w64-mingw32-g++ x86_64-w64-mingw32-windres; do
    check_cmd "$cmd" || missing=1
done

step "Prepare MXE at $MXE_PREFIX"
if [[ -d "$MXE_PREFIX/.git" ]]; then
    ok "MXE checkout exists"
else
    run mkdir -p "$(dirname "$MXE_PREFIX")"
    run git clone https://github.com/mxe/mxe.git "$MXE_PREFIX" || missing=1
fi
run chown -R "$ORIGINAL_USER:$ORIGINAL_USER" "$MXE_PREFIX"

# If MXE was moved from /opt to /home, a mistaken rerun can leave the ccache
# wrapper directory inside a nested MXE checkout. The generated compiler
# symlinks still point at $MXE_PREFIX/.ccache/bin/ccache, so repair that before
# CMake-based MXE packages try to configure.
if [[ ! -e "$MXE_PREFIX/.ccache/bin/ccache" && -e "$MXE_PREFIX/mxe/.ccache/bin/ccache" ]]; then
    warn "repairing nested MXE ccache directory left by a previous move"
    run mv "$MXE_PREFIX/mxe/.ccache" "$MXE_PREFIX/.ccache"
    run chown -R "$ORIGINAL_USER:$ORIGINAL_USER" "$MXE_PREFIX/.ccache"
fi

# Keep the nested tree for now because it may contain useful diagnostics while
# the build is still being fixed, but tell the user how to reclaim the space.
if [[ -d "$MXE_PREFIX/mxe" ]]; then
    warn "nested MXE tree found at $MXE_PREFIX/mxe"
    warn "after this build succeeds, remove it to free space: sudo rm -rf '$MXE_PREFIX/mxe'"
fi

step "Build/check Windows Qt 5 with MXE"
ok "parallel build jobs: $JOBS"
QT_PREFIX="$MXE_PREFIX/usr/$TRIPLET/qt5"
QT_CONFIG="$QT_PREFIX/lib/cmake/Qt5/Qt5Config.cmake"
if [[ -f "$QT_CONFIG" ]]; then
    ok "Windows Qt found: $QT_CONFIG"
else
    warn "Windows Qt not found; building MXE qtbase for $TRIPLET"
    warn "this can take a long time and may fail until system dependencies are installed"
    warn "MXE compiler wrappers such as $TRIPLET-g++ are created by this build"
    run sudo -u "$ORIGINAL_USER" env HOME="$ORIGINAL_HOME" make -C "$MXE_PREFIX" MXE_TARGETS="$TRIPLET" JOBS="$JOBS" qtbase || missing=1
fi

step "Run project verifier"
export MXE_PREFIX
export WINDOWS_MINGW_TRIPLET="$TRIPLET"
export WINDOWS_MINGW_BIN="$MXE_PREFIX/usr/bin"
export WINDOWS_QT_PREFIX="$QT_PREFIX"

if run sudo -u "$ORIGINAL_USER" env \
    HOME="$ORIGINAL_HOME" \
    MXE_PREFIX="$MXE_PREFIX" \
    WINDOWS_MINGW_TRIPLET="$WINDOWS_MINGW_TRIPLET" \
    WINDOWS_MINGW_BIN="$WINDOWS_MINGW_BIN" \
    WINDOWS_QT_PREFIX="$WINDOWS_QT_PREFIX" \
    "$ROOT/scripts/verify-windows-toolchain.sh"; then
    ok "Windows toolchain, build, and deployment verified"
else
    missing=1
    fail "verification failed; read the messages above and install/fix the missing part"
fi

step "Summary"
if [[ "$missing" -eq 0 ]]; then
    ok "ready: Windows bundle should be in $ROOT/dist/windows"
else
    fail "not ready yet"
    cat <<EOF

Common fixes:
  - Re-run after pacman finishes installing packages.
  - If MXE fails, install the dependency named in the MXE error and re-run.
  - If Qt is elsewhere, skip MXE and set:
      export WINDOWS_QT_PREFIX=/path/to/windows/qt5/mingw/prefix
      export WINDOWS_MINGW_TRIPLET=x86_64-w64-mingw32
      ./scripts/verify-windows-toolchain.sh

EOF
    exit 1
fi
