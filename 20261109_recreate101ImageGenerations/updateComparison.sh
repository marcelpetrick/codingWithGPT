#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Regenerate the step-by-step comparison in README.md from the four run manifests.
set -euo pipefail
cd "$(dirname "$0")"
node recreate-101/scripts/compare.mjs --readme README.md --out comparison --step 10 \
  --run "Wirth, Codex=pilot-niklaus-wirth" \
  --run "Wirth, ComfyUI=pilot-comfyui-niklaus-wirth" \
  --run "Limburg, Codex=pilot-limburg-cathedral" \
  --run "Limburg, ComfyUI=pilot-comfyui-limburg-cathedral"
