# Codex and Claude Code Mini Trigger

Author: Marcel Petrick <mail@marcelpetrick.it>

License: GPLv3

## Purpose

This directory contains a small shell-based trigger for running minimal non-interactive checks with Claude Code and Codex in the repository working directory.

The script asks each tool to answer `1+1`, prints the selected models, captures the tool output, measures wall-clock execution time, reports each exit code, and extracts any token, usage, cost, duration, or elapsed-time fields exposed in JSON output.

The desktop launcher starts the script in a terminal with verbose output and waits for Enter before closing, so double-click runs remain inspectable.

## Files

- `codex_and_claude_code_mini_trigger.sh`: regular POSIX-style shell script and main entry point.
- `codex_and_claude_code_mini_trigger.desktop`: desktop launcher for double-click terminal use.

## Usage

```sh
./codex_and_claude_code_mini_trigger.sh
./codex_and_claude_code_mini_trigger.sh --verbose
./codex_and_claude_code_mini_trigger.sh --verbose --wait
./codex_and_claude_code_mini_trigger.sh --workdir "$HOME/projects/example"
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
./codex_and_claude_code_mini_trigger.sh --verbose
```

## Requirements

- `sh`
- `claude`
- `codex`
- `timeout` for command timeouts, when available
- `jq` for extracting token and usage fields from JSON output

If `jq` is missing, the script still runs and prints raw tool output, but usage extraction is skipped.

## Sample Run

Run on 2026-07-10 with default models (`sonnet` / `gpt-5.4-mini`, reasoning effort `low`), workdir `~/repos/codingWithGPT`.

```
Using sh: /usr/bin/sh
Using claude: /home/mpetrick/.local/bin/claude
Using codex: /run/user/1000/fnm_multishells/15890_1783674350151/bin/codex
Trigger workdir: /home/mpetrick/repos/codingWithGPT
Claude Code model: sonnet
Codex model: gpt-5.4-mini
Codex reasoning effort: low
Prompt: Return only the result of 1+1.

=== Claude Code ===
Started at: Fri Jul 10 11:05:50 AM CEST 2026
Working directory: /home/mpetrick/repos/codingWithGPT
Timeout: 300s
Command: claude -p --model sonnet --output-format json --no-session-persistence Return only the result of 1+1.
--- Claude Code output ---
{"type":"result","subtype":"success","is_error":false,...,"result":"2","num_turns":1,
 "total_cost_usd":0.051544900000000005,
 "usage":{"input_tokens":2974,"cache_creation_input_tokens":6222,
          "cache_read_input_tokens":15533,"output_tokens":3,...}}
--- Claude Code summary ---
Exit code: 0
Wall clock: 3s
Claude Code reported usage/statistics:
  duration_api_ms=3890
  duration_ms=2494
  modelUsage.claude-haiku-4-5-20251001.costUSD=0.000586
  modelUsage.claude-haiku-4-5-20251001.inputTokens=526
  modelUsage.claude-haiku-4-5-20251001.outputTokens=12
  modelUsage.claude-sonnet-5.cacheCreationInputTokens=6222
  modelUsage.claude-sonnet-5.cacheReadInputTokens=15533
  modelUsage.claude-sonnet-5.costUSD=0.0509589
  modelUsage.claude-sonnet-5.inputTokens=2974
  modelUsage.claude-sonnet-5.outputTokens=3
  total_cost_usd=0.051544900000000005
  usage.cache_creation_input_tokens=6222
  usage.cache_read_input_tokens=15533
  usage.input_tokens=2974
  usage.output_tokens=3
Claude Code check completed.

=== Codex ===
Started at: Fri Jul 10 11:05:53 AM CEST 2026
Working directory: /home/mpetrick/repos/codingWithGPT
Timeout: 300s
Command: codex exec -m gpt-5.4-mini -c model_reasoning_effort="low" --json -C /home/mpetrick/repos/codingWithGPT Return only the result of 1+1.
--- Codex output ---
{"type":"thread.started","thread_id":"019f4b46-b7d5-78f1-b21b-599f566a6ab0"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"2"}}
{"type":"turn.completed","usage":{"input_tokens":9572,"cached_input_tokens":4480,"output_tokens":16,"reasoning_output_tokens":9}}
--- Codex summary ---
Exit code: 0
Wall clock: 3s
Codex reported usage/statistics:
  usage.cached_input_tokens=4480
  usage.input_tokens=9572
  usage.output_tokens=16
  usage.reasoning_output_tokens=9
Codex check completed.
```

Both tools answered `2`. Claude Code used `claude-sonnet-5` (via the `sonnet` alias) for the actual inference and `claude-haiku-4-5-20251001` for orchestration. Total cost: ~$0.052 USD. Codex consumed 9 572 input tokens (4 480 cached) with 9 reasoning tokens.
