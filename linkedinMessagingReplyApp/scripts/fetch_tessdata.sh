#!/usr/bin/env bash
# fetch_tessdata.sh: download Tesseract language data to the user data directory (no root needed).
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/fetch_tessdata.sh [lang ...]        default: eng deu
# Target: ${XDG_DATA_HOME:-~/.local/share}/linkedin-reply-assistant/tessdata
#         The app uses this directory when it exists (see paths.tessdata_dir()).
# Source: https://github.com/tesseract-ocr/tessdata_fast (Apache-2.0), main branch.
# Exit:   0 all files present; 1 a download failed.
set -euo pipefail
langs=("$@")
[ ${#langs[@]} -gt 0 ] || langs=(eng deu)
dir="${XDG_DATA_HOME:-$HOME/.local/share}/linkedin-reply-assistant/tessdata"
mkdir -p "$dir"
for lang in "${langs[@]}" osd; do
  file="$dir/$lang.traineddata"
  if [ -s "$file" ]; then echo "present: $file"; continue; fi
  curl -fsSL --retry 3 -o "$file.part" \
    "https://github.com/tesseract-ocr/tessdata_fast/raw/main/$lang.traineddata"
  mv "$file.part" "$file"
  echo "fetched: $file"
done
