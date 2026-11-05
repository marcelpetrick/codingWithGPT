#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Run the resumable multi-turn and long-context probes on an idle server.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p results
exec 9>results/t1.lock
flock -n 9 || { echo 'Another gate run is active.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri targeted gates finished" "Exit status: $rc. See results/targeted-gates.log." 2>/dev/null || true' EXIT
python3 -u targeted_gate.py
