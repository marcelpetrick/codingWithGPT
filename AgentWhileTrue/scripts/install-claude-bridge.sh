#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/claude-statusline-proxy.sh"
TARGET_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/agent-watch"
TARGET="$TARGET_DIR/claude-statusline-proxy.sh"
SETTINGS="${CLAUDE_SETTINGS_FILE:-$HOME/.claude/settings.json}"

if [ "$#" -ne 0 ]; then
    printf 'usage: %s\n' "$0" >&2
    exit 2
fi
if ! command -v jq > /dev/null 2>&1; then
    printf '%s\n' 'jq is required to update Claude settings safely.' >&2
    exit 1
fi
if [ ! -f "$SETTINGS" ]; then
    printf 'Claude settings not found: %s\n' "$SETTINGS" >&2
    exit 1
fi
if ! jq -e 'type == "object"' "$SETTINGS" > /dev/null; then
    printf 'Claude settings are not a valid JSON object: %s\n' "$SETTINGS" >&2
    exit 1
fi

install -d -m 700 -- "$TARGET_DIR"
install -m 755 -- "$SOURCE" "$TARGET"

current="$(jq -r '.statusLine.command // empty' "$SETTINGS")"
if [[ "$current" == *claude-statusline-proxy.sh* ]]; then
    printf 'Claude quota bridge is already configured: %s\n' "$TARGET"
    exit 0
fi

if [ -n "$current" ]; then
    printf -v quoted_current '%q' "$current"
    replacement="AGENT_WATCH_STATUSLINE_CHAIN=$quoted_current $TARGET"
else
    replacement="$TARGET"
fi

backup="$SETTINGS.agent-watch-backup.$(date +%Y%m%d-%H%M%S).$$"
cp -p -- "$SETTINGS" "$backup"
temporary="$(mktemp "$SETTINGS.tmp.XXXXXX")"
if ! jq --arg command "$replacement" \
    '.statusLine = {"type": "command", "command": $command}' \
    "$SETTINGS" > "$temporary"; then
    rm -f -- "$temporary"
    exit 1
fi
chmod --reference="$SETTINGS" "$temporary"
mv -f -- "$temporary" "$SETTINGS"

printf 'Installed bridge: %s\n' "$TARGET"
printf 'Updated settings: %s\n' "$SETTINGS"
printf 'Backup: %s\n' "$backup"
printf '%s\n' 'Restart Claude Code if quota remains UNKNOWN after its next render.'
