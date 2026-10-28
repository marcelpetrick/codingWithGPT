#!/usr/bin/env bash
# install.sh: install the app for the current user (no root): venv, Tesseract data, native host, menu entry.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/install.sh
# Steps:  1 create .venv and install the package (uv)
#         2 fetch English/German Tesseract data if the system has no English data
#         3 register lra-native-host for Chromium, Chrome and Firefox
#         4 write the desktop entry (app id io.github.marcelpetrick.LinkedInReplyAssistant; the
#           GlobalShortcuts portal identifies the app by it)
#         5 run `lra selftest` and `lra preflight`
# Needs:  uv, Python 3.14, tesseract, GStreamer with pipewiresrc (see README "Setup").
# Exit:   0 installed and self-test OK; 1 a step failed.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
APP_ID=io.github.marcelpetrick.LinkedInReplyAssistant

[ -x .venv/bin/python ] || uv venv -q -p 3.14 .venv
VIRTUAL_ENV=.venv uv pip install -q -e .

if ! tesseract --list-langs 2>/dev/null | grep -qx eng; then
  scripts/fetch_tessdata.sh eng deu
fi

scripts/install_native_host.sh "$ROOT/.venv/bin/lra-native-host"

apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$apps"
cat > "$apps/$APP_ID.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=LinkedIn Reply Assistant
Comment=Capture a LinkedIn conversation, draft a reply locally, insert it. Never sends.
Exec=$ROOT/.venv/bin/lra gui
Icon=mail-reply-sender
Terminal=false
Categories=Network;Office;
StartupWMClass=lra
DESKTOP
command -v update-desktop-database >/dev/null && update-desktop-database -q "$apps" || true
echo "wrote $apps/$APP_ID.desktop"

.venv/bin/lra selftest
.venv/bin/lra preflight || echo "preflight reported problems (see above); the app still starts"
echo "Done. Start the app from the menu or with: $ROOT/.venv/bin/lra gui"
echo "Load the extension: chromium://extensions -> Developer mode -> Load unpacked -> $ROOT/extension"
