#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Wait for the residency chain, then refine a completed ladder.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p results
exec 8>results/refine.lock
flock -n 8 || { echo 'Another refinement is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri context search finished" "Exit status: $rc. See results/refine.log." 2>/dev/null || true' EXIT
exec 9>results/chain.lock
flock 9
python3 refine.py
