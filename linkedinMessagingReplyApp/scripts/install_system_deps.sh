#!/usr/bin/env bash
# install_system_deps.sh: install the system packages for build, tests and runtime on Debian/Ubuntu (CI, Docker).
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  sudo scripts/install_system_deps.sh        (Debian/Ubuntu only; Manjaro: see README "Setup")
# Installs: Tesseract + English data, GStreamer + PipeWire source, GObject introspection build files
#           (for PyGObject), D-Bus daemon (fake portal tests), Qt runtime libraries (offscreen tests).
# Exit:   0 installed; 1 apt failed; 2 not a Debian-like system.
set -euo pipefail
command -v apt-get >/dev/null || { echo "apt-get not found: not Debian/Ubuntu" >&2; exit 2; }
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q --no-install-recommends \
  tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-pipewire \
  gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
  libgirepository-2.0-dev libcairo2-dev pkg-config gcc \
  dbus-daemon \
  libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 libglib2.0-0 fonts-dejavu-core
