#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
MODEL_DIR="$ROOT/models"
MODEL_FILE="Bonsai-27B-Q1_0.gguf"

mkdir -p "$MODEL_DIR" "$ROOT/.cache/huggingface"
export HF_HOME="$ROOT/.cache/huggingface"

if [[ -f "$MODEL_DIR/$MODEL_FILE" ]]; then
  printf 'Model already present: %s\n' "$MODEL_DIR/$MODEL_FILE"
  exit 0
fi

command -v huggingface-cli >/dev/null || {
  printf 'huggingface-cli is required but was not found. No packages were installed.\n' >&2
  exit 1
}

huggingface-cli download prism-ml/Bonsai-27B-gguf "$MODEL_FILE" --local-dir "$MODEL_DIR"
test -f "$MODEL_DIR/$MODEL_FILE"
printf 'Downloaded model: %s\n' "$MODEL_DIR/$MODEL_FILE"
