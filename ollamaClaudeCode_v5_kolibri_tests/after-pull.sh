#!/usr/bin/env bash
# Wait for the pull lock, then run the residency ladder if the pull succeeded.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p results
exec 8>results/chain.lock
flock -n 8 || { echo 'Another chain is running.' >&2; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; timeout 5 notify-send "Kolibri residency run finished" "Exit status: $rc. See results/chain.log." 2>/dev/null || true' EXIT
exec 9>results/pull.lock
flock 9
python3 residency.py
