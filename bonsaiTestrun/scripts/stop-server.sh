#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
PID_FILE="$ROOT/logs/llama-server.pid"

[[ -f "$PID_FILE" ]] || { printf 'No local server PID file found.\n'; exit 0; }
PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  printf 'Stopped local server (PID %s).\n' "$PID"
fi
rm -f "$PID_FILE"
