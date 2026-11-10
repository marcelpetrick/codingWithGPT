#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Run the local checks for Recreate 101. Requires Node.js, ImageMagick and FFmpeg.
set -euo pipefail
cd "$(dirname "$0")"
shellcheck localPipeline.sh recreate-101/scripts/codex-chain.sh
node --check recreate-101/scripts/comfy-chain.mjs
node --check recreate-101/scripts/recreate.mjs
node --check recreate-101/scripts/host.mjs
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-include="**/recreate-101/scripts/*.mjs" recreate-101/tests/*.test.mjs
node -e "const fs=require('fs');const s=fs.readFileSync('recreate-101/SKILL.md','utf8');if(!/^---\\nname: recreate-101\\ndescription: .+\\n---/m.test(s))process.exit(1);JSON.parse(fs.readFileSync('recreate-101/references/pricing.json'));"
