#!/usr/bin/env bash
# Reset Claude Code's DMO sandbox configuration after it becomes empty or invalid.
# Usage: ./reset_claude_dmo.sh

set -euo pipefail

config_dir="${HOME:?HOME is not set}/.claude-dmo"
config_file="${config_dir}/.config.json"

if [[ ! -d "${config_dir}" ]]; then
  printf 'Error: Claude DMO configuration directory does not exist: %s\n' "${config_dir}" >&2
  exit 1
fi

if [[ -L "${config_file}" || ( -e "${config_file}" && ! -f "${config_file}" ) ]]; then
  printf 'Error: refusing to replace a non-regular file: %s\n' "${config_file}" >&2
  exit 1
fi

if [[ -f "${config_file}" ]]; then
  timestamp="$(date '+%Y%m%d-%H%M%S')"
  backup_file="${config_file}.before-reset-${timestamp}"
  mv -- "${config_file}" "${backup_file}"
  printf 'Backed up the previous configuration to %s\n' "${backup_file}"
fi

umask 077
printf '{}\n' >"${config_file}"
chmod 600 "${config_file}"

printf 'Reset %s to valid default JSON.\n' "${config_file}"
printf 'Start Claude with: claude-dmo --dangerously-skip-permissions\n'
