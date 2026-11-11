#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Regenerate the overview and the step-by-step comparisons in README.md from the run manifests.
set -euo pipefail
cd "$(dirname "$0")"
cmp() { node recreate-101/scripts/compare.mjs --readme README.md --out comparison --step 10 "$@"; }
cmp --run "Wirth, Codex=pilot-niklaus-wirth" \
  --run "Wirth, ComfyUI=pilot-comfyui-niklaus-wirth" \
  --run "Limburg, Codex=pilot-limburg-cathedral" \
  --run "Limburg, ComfyUI=pilot-comfyui-limburg-cathedral"
cmp --block turing \
  --run "Turing, Codex, v2=pilot-turing-codex-v2" \
  --run "Turing, ComfyUI, v2=pilot-comfyui-turing-v2" \
  --run "Turing, ComfyUI, v1=pilot-comfyui-turing-v1"
subjects=(tabby-cat:Cat corgi-puppy:Corgi berlin-christmas-market:"Christmas market" dwayne-johnson:"Dwayne Johnson" mona-lisa:"Mona Lisa")
v2=(); v3=(); v3i=(); all=()
for s in "${subjects[@]}"; do
  v2+=(--run "${s#*:}=pilot-comfyui-${s%%:*}")
  v3+=(--run "${s#*:}, v3=pilot-comfyui-${s%%:*}-v3")
  v3i+=(--run "${s#*:}, v3 img2img=pilot-comfyui-${s%%:*}-v3i")
  all+=(--run "${s#*:}, ComfyUI, v2=pilot-comfyui-${s%%:*}" --run "${s#*:}, ComfyUI, v3=pilot-comfyui-${s%%:*}-v3" \
    --run "${s#*:}, ComfyUI img2img, v3=pilot-comfyui-${s%%:*}-v3i")
done
all+=(--run "Cat, ComfyUI img2img, v2 (control)=pilot-comfyui-tabby-cat-v2i")
cmp --block linkedin "${v2[@]}"
cmp --block steered "${v3[@]}"
cmp --block img2img "${v3i[@]}" --run "Cat, v2 img2img (control)=pilot-comfyui-tabby-cat-v2i"
node recreate-101/scripts/overview.mjs --readme README.md --out comparison \
  --prompt "v1=recreate-101/SKILL.md" \
  --prompt "prompt-v2=recreate-101/references/prompt-v2.txt" \
  --prompt "prompt-v3=recreate-101/references/prompt-v3.txt" \
  --run "Wirth, Codex, v1=pilot-niklaus-wirth" \
  --run "Wirth, ComfyUI, v1=pilot-comfyui-niklaus-wirth" \
  --run "Limburg, Codex, v1=pilot-limburg-cathedral" \
  --run "Limburg, ComfyUI, v1=pilot-comfyui-limburg-cathedral" \
  --run "Turing, Codex, v2=pilot-turing-codex-v2" \
  --run "Turing, ComfyUI, v2=pilot-comfyui-turing-v2" \
  --run "Turing, ComfyUI, v1=pilot-comfyui-turing-v1" \
  "${all[@]}"
