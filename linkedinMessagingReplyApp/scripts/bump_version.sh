#!/usr/bin/env bash
# bump_version.sh: bump the semver in src/linkedin_reply_assistant/version.py and print the new version.
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/bump_version.sh patch|minor|major
# Rule:   every commit bumps patch; a gate or a major feature bumps minor (AGENTS.md).
# Exit:   0 bumped; 2 bad argument; 1 version line not found.
set -euo pipefail
cd "$(dirname "$0")/.."
FILE=src/linkedin_reply_assistant/version.py
part=${1:-}
current=$(sed -nE 's/^__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"$/\1/p' "$FILE")
[ -n "$current" ] || { echo "no version line in $FILE" >&2; exit 1; }
IFS=. read -r major minor patch <<<"$current"
case $part in
  patch) patch=$((patch + 1)) ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  major) major=$((major + 1)); minor=0; patch=0 ;;
  *) echo "usage: $0 patch|minor|major" >&2; exit 2 ;;
esac
new="$major.$minor.$patch"
sed -i -E "s/^__version__ = \"$current\"$/__version__ = \"$new\"/" "$FILE"
echo "$new"
