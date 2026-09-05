#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname -- "$SCRIPT_DIR")"
UNIT_SOURCE="$PROJECT_ROOT/systemd/agent-watch.service"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_TARGET="$UNIT_DIR/agent-watch.service"

if [ "${1:-}" = "--uninstall" ]; then
    systemctl --user disable --now agent-watch.service 2> /dev/null || true
    rm -f -- "$UNIT_TARGET"
    systemctl --user daemon-reload
    printf 'Removed %s\n' "$UNIT_TARGET"
    exit 0
fi
if [ "$#" -ne 0 ]; then
    printf 'usage: %s [--uninstall]\n' "$0" >&2
    exit 2
fi
if [ ! -x "$HOME/.local/bin/agent-watch" ]; then
    printf '%s\n' 'agent-watch is not installed at ~/.local/bin/agent-watch.' >&2
    printf '%s\n' 'Install it first: python3 -m pip install --user .' >&2
    exit 1
fi

install -d -m 700 -- "$UNIT_DIR"
install -m 644 -- "$UNIT_SOURCE" "$UNIT_TARGET"
systemctl --user daemon-reload
printf 'Installed %s\n' "$UNIT_TARGET"
printf '%s\n' 'Start the safe observe-only service with:'
printf '%s\n' '  systemctl --user enable --now agent-watch.service'
