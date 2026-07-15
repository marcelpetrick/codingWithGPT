#!/usr/bin/env bash
set -euo pipefail

curl --fail --silent --show-error http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  --data '{"messages":[{"role":"user","content":"Reply with exactly: Bonsai local runtime is working."}],"temperature":0,"max_tokens":128}'
printf '\n'
