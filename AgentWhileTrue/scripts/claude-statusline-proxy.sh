#!/usr/bin/env bash
#
# Claude Code status-line proxy.
#
# Claude Code pipes a JSON document to its configured status-line command on
# every render. That document carries the usage numbers agent-watch wants:
# five-hour and seven-day utilisation and their reset timestamps. This script
# captures those into a small file that agent-watch reads passively, then hands
# the untouched JSON to whatever status-line command the user already had, so
# an existing status line keeps working exactly as before.
#
# Install:
#   1. Note your current statusLine command from ~/.claude/settings.json.
#   2. Point statusLine at this script.
#   3. Set AGENT_WATCH_STATUSLINE_CHAIN to your original command.
#
# Example ~/.claude/settings.json fragment:
#
#   "statusLine": {
#     "type": "command",
#     "command": "AGENT_WATCH_STATUSLINE_CHAIN=~/.claude/my-statusline.sh \
#                 ~/.local/share/agent-watch/claude-statusline-proxy.sh"
#   }
#
# The proxy must never be the reason a status line stops rendering, so every
# failure here is swallowed and the original command still runs.

set -uo pipefail
umask 077

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/agent-watch"
OUTPUT="$STATE_DIR/quota/claude.json"
CHAIN="${AGENT_WATCH_STATUSLINE_CHAIN:-}"

payload="$(cat)"

capture() {
    mkdir -p -- "$(dirname -- "$OUTPUT")" 2> /dev/null || return 0
    chmod 700 -- "$STATE_DIR" 2> /dev/null || true
    local temporary
    temporary="$(mktemp "$OUTPUT.tmp.XXXXXX")" || return 0

    # jq is optional everywhere else in this project, so the proxy falls back to
    # Python. One of the two is always present on a machine running Claude Code.
    if command -v jq > /dev/null 2>&1; then
        printf '%s' "$payload" | jq -c '
            {
              source: "claude",
              updated_at: (now | floor),
              five_hour: (.usage.five_hour // .rate_limits.five_hour // null),
              seven_day: (.usage.seven_day // .rate_limits.seven_day // null),
              seven_day_opus: (.usage.seven_day_opus // .rate_limits.seven_day_opus // null),
              seven_day_sonnet: (.usage.seven_day_sonnet // .rate_limits.seven_day_sonnet // null)
            } | with_entries(select(.value != null))
        ' > "$temporary" 2> /dev/null || {
            rm -f -- "$temporary"
            return 0
        }
    elif command -v python3 > /dev/null 2>&1; then
        printf '%s' "$payload" | python3 -c '
import json, sys, time

try:
    document = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)

source = document.get("usage") or document.get("rate_limits") or {}
captured = {"source": "claude", "updated_at": int(time.time())}
for key in ("five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet"):
    value = source.get(key)
    if isinstance(value, dict):
        captured[key] = value
json.dump(captured, sys.stdout)
' > "$temporary" 2> /dev/null || {
            rm -f -- "$temporary"
            return 0
        }
    else
        rm -f -- "$temporary"
        return 0
    fi

    # Atomic replace: agent-watch may read this at any moment, and a truncated
    # file would be parsed as "no usable windows".
    if [ -s "$temporary" ]; then
        chmod 600 -- "$temporary" 2> /dev/null || true
        mv -f -- "$temporary" "$OUTPUT" 2> /dev/null || rm -f -- "$temporary"
    else
        rm -f -- "$temporary"
    fi
}

capture

if [ -n "$CHAIN" ]; then
    # Hand the original document, unmodified, to the user's own status line.
    printf '%s' "$payload" | eval "$CHAIN"
fi
