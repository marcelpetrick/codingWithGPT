#!/usr/bin/env bash
# bump_version.sh: raise the version in src/mvo/version.py (semver).
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/bump_version.sh [patch|minor|major]   (default: patch)
#         Every commit bumps patch; a major feature bumps minor.
# Prints: the new version.
# Exit:   0 done; 1 bad argument or no version found.
set -euo pipefail
cd "$(dirname "$0")/.."
file=src/mvo/version.py
part=${1:-patch}
current=$(sed -n 's/^__version__ = "\([0-9]*\.[0-9]*\.[0-9]*\)"$/\1/p' "$file")
[ -n "$current" ] || { echo "no version in $file" >&2; exit 1; }
IFS=. read -r major minor patch <<<"$current"
case $part in
  patch) patch=$((patch + 1)) ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  major) major=$((major + 1)); minor=0; patch=0 ;;
  *) echo "usage: $0 [patch|minor|major]" >&2; exit 1 ;;
esac
new="$major.$minor.$patch"
sed -i "s/^__version__ = \"$current\"$/__version__ = \"$new\"/" "$file"
echo "$new"
