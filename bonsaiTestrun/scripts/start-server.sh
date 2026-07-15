#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
SERVER="$ROOT/runtime/llama.cpp/build/bin/llama-server"
MODEL="$ROOT/models/Bonsai-27B-Q1_0.gguf"
LOG_DIR="$ROOT/logs"
PID_FILE="$LOG_DIR/llama-server.pid"

[[ -x "$SERVER" ]] || { printf 'Run scripts/build-llama.sh first.\n' >&2; exit 1; }
[[ -f "$MODEL" ]] || { printf 'Run scripts/download-model.sh first.\n' >&2; exit 1; }
mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  printf 'Server is already running (PID %s).\n' "$(cat "$PID_FILE")" >&2
  exit 1
fi
rm -f "$PID_FILE"

nohup "$SERVER" \
  --model "$MODEL" \
  --host 127.0.0.1 --port 8080 \
  --ctx-size 4096 \
  --n-gpu-layers 99 \
  --parallel 1 \
  --cache-ram 0 \
  --no-warmup \
  >"$LOG_DIR/llama-server.log" 2>&1 &
echo $! >"$PID_FILE"

for _ in {1..30}; do
  if curl --fail --silent --show-error http://127.0.0.1:8080/health >/dev/null; then
    printf 'Server is ready at http://127.0.0.1:8080 (PID %s).\n' "$(cat "$PID_FILE")"
    exit 0
  fi
  sleep 1
done

printf 'Server did not become ready; see %s\n' "$LOG_DIR/llama-server.log" >&2
exit 1
