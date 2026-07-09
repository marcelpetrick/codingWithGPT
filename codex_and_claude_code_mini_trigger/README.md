# Codex and Claude Code Mini Trigger

Author: Marcel Petrick <mail@marcelpetrick.it>

License: GPLv3

## Purpose

This directory contains a small shell-based trigger for running minimal non-interactive checks with Claude Code and Codex in the repository working directory.

The script asks each tool to answer `1+1`, prints the selected models, captures the tool output, measures wall-clock execution time, reports each exit code, and extracts any token, usage, cost, duration, or elapsed-time fields exposed in JSON output.

The desktop launcher starts the script in a terminal with verbose output and waits for Enter before closing, so double-click runs remain inspectable.

## Files

- `trigger_tools.sh`: regular POSIX-style shell script and main entry point.
- `trigger_tools.desktop`: desktop launcher for double-click terminal use.

## Usage

```sh
./trigger_tools.sh
./trigger_tools.sh --verbose
./trigger_tools.sh --verbose --wait
./trigger_tools.sh --workdir "$HOME/projects/example"
```

## Options

- `-h`, `--help`: show usage information.
- `-v`, `--verbose`: print commands, resolved paths, and progress details.
- `--wait`: wait for Enter before exiting.
- `--workdir DIR`: enter `DIR` before running both checks. Defaults to the parent directory of this trigger directory.

## Environment Parameters

- `CLAUDE_TRIGGER_MODEL`: Claude Code model passed via `--model`. Defaults to `sonnet`, which the installed Claude Code CLI documents as an alias.
- `CODEX_TRIGGER_MODEL`: Codex model passed via `--model`. Defaults to `gpt-5.4-mini`.
- `CODEX_TRIGGER_REASONING_EFFORT`: Codex reasoning effort passed through config. Defaults to `low`.
- `TRIGGER_TIMEOUT_SECONDS`: per-command timeout in seconds. Defaults to `300`.

Example:

```sh
CLAUDE_TRIGGER_MODEL=sonnet \
CODEX_TRIGGER_MODEL=gpt-5.4-mini \
CODEX_TRIGGER_REASONING_EFFORT=low \
TRIGGER_TIMEOUT_SECONDS=180 \
./trigger_tools.sh --verbose
```

## Requirements

- `sh`
- `claude`
- `codex`
- `timeout` for command timeouts, when available
- `jq` for extracting token and usage fields from JSON output

If `jq` is missing, the script still runs and prints raw tool output, but usage extraction is skipped.
