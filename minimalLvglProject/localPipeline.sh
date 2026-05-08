#!/usr/bin/env bash
set -euo pipefail

# ── dependency check (Manjaro / Arch) ─────────────────────────────────────────
MISSING=()
command -v cmake  &>/dev/null || MISSING+=(cmake)
command -v ninja  &>/dev/null || MISSING+=(ninja)
command -v git    &>/dev/null || MISSING+=(git)
pacman -Q sdl2   &>/dev/null || MISSING+=(sdl2)

if (( ${#MISSING[@]} > 0 )); then
    echo "Installing missing packages: ${MISSING[*]}"
    sudo pacman -S --needed "${MISSING[@]}"
fi

# ── build ─────────────────────────────────────────────────────────────────────
BUILD_DIR="build"
rm -rf "$BUILD_DIR"

echo ">>> Configure"
cmake -S . -B "$BUILD_DIR" -G Ninja

echo ">>> Build  ($(nproc) jobs)"
cmake --build "$BUILD_DIR" -- -j"$(nproc)"

echo ">>> Run"
./"$BUILD_DIR"/lvgl_demo
