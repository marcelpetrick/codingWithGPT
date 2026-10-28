#!/usr/bin/env bash
# install_native_host.sh: register lra-native-host for the browser extension (user level, no root).
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  scripts/install_native_host.sh [path/to/lra-native-host] [--target DIR]...
#         Default host: lra-native-host from PATH, else .venv/bin/lra-native-host.
#         Default targets: Chromium, Google Chrome, Firefox user directories.
#         --target DIR writes only into DIR (used by the e2e test for a temporary browser profile).
# Writes: <target>/io.github.marcelpetrick.lra.json
# Exit:   0 written; 1 host executable not found.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=io.github.marcelpetrick.lra
CHROME_ID=halpmmpcpefihaehddccolenemgembam
FIREFOX_ID=lra@marcelpetrick.it
host="" targets=()
while [ $# -gt 0 ]; do
  case $1 in
    --target) targets+=("$2"); shift 2 ;;
    *) host=$1; shift ;;
  esac
done
[ -n "$host" ] || host=$(command -v lra-native-host || echo "$PWD/.venv/bin/lra-native-host")
host=$(realpath "$host")
[ -x "$host" ] || { echo "native host not found: $host" >&2; exit 1; }
if [ ${#targets[@]} -eq 0 ]; then
  targets=("$HOME/.config/chromium/NativeMessagingHosts"
           "$HOME/.config/google-chrome/NativeMessagingHosts"
           "$HOME/.mozilla/native-messaging-hosts")
fi
for dir in "${targets[@]}"; do
  mkdir -p "$dir"
  if [[ $dir == *mozilla* ]]; then
    allowed="\"allowed_extensions\": [\"$FIREFOX_ID\"]"
  else
    allowed="\"allowed_origins\": [\"chrome-extension://$CHROME_ID/\"]"
  fi
  cat > "$dir/$NAME.json" <<JSON
{
  "name": "$NAME",
  "description": "LinkedIn Reply Assistant bridge (relays to the desktop app, never sends)",
  "path": "$host",
  "type": "stdio",
  $allowed
}
JSON
  echo "wrote $dir/$NAME.json"
done
