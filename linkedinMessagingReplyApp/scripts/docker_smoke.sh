#!/usr/bin/env bash
# docker_smoke.sh: build the image and prove it works without network and without a display.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/docker_smoke.sh [image-tag]        default tag: linkedin-reply-assistant:local
# Checks: 1 docker build  2 `lra --version` equals the package version  3 `lra selftest` with
#         --network none (OCR + rules + demo backend)  4 `lra screenshot` renders the real UI offscreen
# Exit:   0 all checks passed; 1 a check failed; 2 docker is not available.
set -euo pipefail
cd "$(dirname "$0")/.."
tag=${1:-linkedin-reply-assistant:local}
command -v docker >/dev/null || { echo "docker not found" >&2; exit 2; }
version=$(sed -nE 's/^__version__ = "(.*)"$/\1/p' src/linkedin_reply_assistant/version.py)
docker build -q -t "$tag" . >/dev/null
got=$(docker run --rm "$tag" --version)
[ "$got" = "lra $version" ] || { echo "version mismatch: '$got' vs '$version'" >&2; exit 1; }
echo "version     $got"
docker run --rm --network none "$tag" selftest | tail -1
out=$(mktemp -d)
chmod 777 "$out"
docker run --rm --network none -v "$out:/out" "$tag" screenshot /out/ui.png 2>/dev/null | tail -1
[ -s "$out/ui.png" ] || { echo "no screenshot" >&2; rm -rf "$out"; exit 1; }
rm -rf "$out"
echo "docker smoke OK ($tag)"
