#!/usr/bin/env bash
# build_carousel.sh: render the LinkedIn carousels (HTML) to PDF and PNG previews.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>. License: GPL-3.0-or-later.
#
# Usage:   scripts/build_carousel.sh [name ...]     (default: all carousel/*.html)
#          scripts/build_carousel.sh v1_timeline
# Output:  carousel/<name>.pdf          one 1080x1350 page per slide (upload this to LinkedIn)
#          carousel/preview/<name>-N.png 540 px wide previews (to check the phone view)
# Needs:   chromium, pdfinfo, pdffonts, pdftoppm (poppler). Network for Google Fonts.
# Exit:    0 ok; 1 missing tool; 2 page size wrong or a web font missing (fallback font used).
set -euo pipefail
cd "$(dirname "$0")/../carousel"

for tool in chromium pdfinfo pdffonts pdftoppm; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 1; }
done

names=("$@")
[ ${#names[@]} -eq 0 ] && names=($(ls *.html | sed 's/\.html$//'))
mkdir -p preview

for n in "${names[@]}"; do
  # virtual-time-budget gives the web fonts time to load before the print.
  chromium --headless --no-pdf-header-footer --virtual-time-budget=15000 \
    --run-all-compositor-stages-before-draw --print-to-pdf="$n.pdf" "$n.html" 2>/dev/null
  size=$(pdfinfo "$n.pdf" | awk '/Page size/{print $3"x"$5}')
  pages=$(pdfinfo "$n.pdf" | awk '/Pages/{print $2}')
  slides=$(grep -c '<section class="slide' "$n.html")
  # 1080x1350 CSS px = 810x1012.5 pt; chromium rounds the height to ~1013 pt.
  [[ "$size" =~ ^810x101[23] ]] || { echo "$n: page size $size, want ~810x1012.5 pt" >&2; exit 2; }
  [ "$pages" = "$slides" ] || { echo "$n: $pages pages but $slides slides (overflow?)" >&2; exit 2; }
  for f in BarlowCondensed IBMPlexSans IBMPlexMono; do
    pdffonts "$n.pdf" | grep -q "$f" || { echo "$n: font $f not embedded (fallback used)" >&2; exit 2; }
  done
  rm -f preview/"$n"-*.png
  pdftoppm -png -scale-to-x 540 -scale-to-y -1 "$n.pdf" preview/"$n"
  echo "$n: $pages pages, $size pt, fonts ok"
done
