#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"
RUNTIME="$ROOT/runtime/llama.cpp"
BUILD="$RUNTIME/build"

mkdir -p "$ROOT/runtime" "$ROOT/.cache"

if [[ ! -d "$RUNTIME/.git" ]]; then
  git clone --depth 1 https://github.com/PrismML-Eng/llama.cpp.git "$RUNTIME"
fi

cmake -S "$RUNTIME" -B "$BUILD" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=86
cmake --build "$BUILD" --target llama-server -j 2

printf 'Built local server: %s\n' "$BUILD/bin/llama-server"
