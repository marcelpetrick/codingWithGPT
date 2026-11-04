#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Wait for completed speed tests, then rerun retrieval below the overflow point.
set -euo pipefail
cd "$(dirname "$0")"
exec 8>results/near-limit.lock
flock -n 8 || { echo 'Another near-limit test is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri near-limit retrieval finished" "Exit status: $rc. See results/near-limit.log." 2>/dev/null || true' EXIT
exec 9>results/speed.lock
flock 9
[[ -f results/speed/results/tokrate.tsv ]] || { echo 'Speed results missing.' >&2; exit 1; }
[[ $(wc -l < results/speed/results/tokrate.tsv) -eq 19 ]] || { echo 'Speed stage is incomplete.' >&2; exit 1; }
./needle-probe.sh near '60000 70000'
