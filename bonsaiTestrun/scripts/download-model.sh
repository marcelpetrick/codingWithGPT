#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
MODEL_DIR="$ROOT/models"
MODEL_FILE="Bonsai-27B-Q1_0.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
PARTIAL_PATH="$MODEL_PATH.partial"

mkdir -p "$MODEL_DIR" "$ROOT/.cache/huggingface"
export HF_HOME="$ROOT/.cache/huggingface"

if [[ -f "$MODEL_PATH" ]]; then
  printf 'Model already present: %s\n' "$MODEL_PATH"
  exit 0
fi

command -v curl >/dev/null || {
  printf 'curl is required but was not found. No packages were installed.\n' >&2
  exit 1
}

curl --fail --location --continue-at - \
  --output "$PARTIAL_PATH" \
  "https://huggingface.co/prism-ml/Bonsai-27B-gguf/resolve/main/$MODEL_FILE?download=true"
mv "$PARTIAL_PATH" "$MODEL_PATH"
printf 'Downloaded model: %s\n' "$MODEL_PATH"
