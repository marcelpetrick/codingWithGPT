# Codex and Claude Code Mini Trigger

Author: Marcel Petrick <mail@marcelpetrick.it>

License: GPLv3

## Purpose

This directory contains a small shell-based trigger for running minimal non-interactive checks with Claude Code and Codex in the repository working directory.

The script asks each tool to answer `1+1`, prints the selected models, captures the tool output, measures wall-clock execution time, reports each exit code, prints a one-line token and cost total, and extracts any token, usage, cost, duration, or elapsed-time fields exposed in JSON output.

Both calls are configured for the smallest practical footprint, since the point of the check is to confirm the tools respond at all rather than to do any work.

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

- `CLAUDE_TRIGGER_MODEL`: Claude Code model passed via `--model`. Defaults to `claude-haiku-4-5`.
- `CLAUDE_TRIGGER_SESSION_PERSISTENCE`: write a Claude Code session record to disk, `0` or `1`. Defaults to `1`. See "Minimising cost" below for the trade-off.
- `CODEX_TRIGGER_MODEL`: Codex model passed via `--model`. Defaults to `gpt-5.4-mini`.
- `CODEX_TRIGGER_REASONING_EFFORT`: Codex reasoning effort passed through config. Defaults to `low`.
- `TRIGGER_TIMEOUT_SECONDS`: per-command timeout in seconds. Defaults to `300`.

Example:

```sh
CLAUDE_TRIGGER_MODEL=claude-haiku-4-5 \
CLAUDE_TRIGGER_SESSION_PERSISTENCE=1 \
CODEX_TRIGGER_MODEL=gpt-5.4-mini \
CODEX_TRIGGER_REASONING_EFFORT=low \
TRIGGER_TIMEOUT_SECONDS=180 \
./codex_and_claude_code_mini_trigger.sh --verbose
```

## Minimising cost

The Claude Code call is the expensive half, because by default the CLI sends its full system prompt, every built-in tool schema, discovered `CLAUDE.md` files, the skills listing, and all configured MCP servers. For a one-line arithmetic prompt, none of that is needed. The script therefore passes:

| Flag | Effect |
| --- | --- |
| `--model claude-haiku-4-5` | cheapest current Claude model, $1/$5 per million tokens |
| `--system-prompt` | replaces the large default system prompt with one line |
| `--tools ""` | drops every built-in tool definition |
| `--disable-slash-commands` | skips the skills listing |
| `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` | ignores configured MCP servers |

Together these cut a run from roughly 24 700 tokens and $0.0515 to roughly 550 tokens and $0.0014, a 35-fold reduction.

`--mcp-config` needs the `{"mcpServers":{}}` wrapper; a bare `{}` is rejected. `--tools` and `--mcp-config` are both variadic, so the prompt is passed after a `--` separator to stop it being consumed as another flag value.

### Session persistence trade-off

Keeping session persistence on costs one extra orchestration call, used to generate a session title. Turning it off saves that call but leaves nothing on disk for external monitors to read:

| `CLAUDE_TRIGGER_SESSION_PERSISTENCE` | API calls | Cost per run | Session record written |
| --- | --- | --- | --- |
| `1` (default) | 2 | $0.00147 | yes |
| `0` | 1 | $0.00119 | no |

The default favours observability, because the $0.0003 difference is small next to the 35-fold saving already achieved by the flags above.

### Codex is already at its floor

`gpt-5.4-mini` at reasoning effort `low` is the cheapest configuration the installed Codex CLI offers. The model cache (`~/.codex/models_cache.json`, CLI 0.145.0) lists only `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini` and `codex-auto-review`; there is no nano or lite tier, and `gpt-5.4-mini` supports `low`, `medium`, `high` and `xhigh`, so `low` is the minimum. No change is available here.

Codex still reports around 10 700 input tokens for the same prompt, most of it its own built-in instructions, and exposes no equivalent of Claude Code's context-stripping flags.

## Monitoring with abtop

[`abtop`](https://github.com/graykode/abtop) reads local session records rather than talking to either API, which shapes what it can and cannot show for this script.

- **Claude Code** is visible only when `CLAUDE_TRIGGER_SESSION_PERSISTENCE=1`, which writes a record under `~/.claude/projects/<slug>/<session-id>.jsonl`. With persistence off, the trigger leaves no trace and abtop's token, project and session panels stay empty.
- **Codex** writes a rollout to `~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-*.jsonl` on every run regardless of settings, and abtop caches the rate limits it finds there to `~/.cache/abtop/codex-rate-limits.json`.
- **Codex quota can still look untriggered.** The `turn.completed` event carries a `rate_limits` object whose `primary` window is weekly (`window_minutes: 10080`) with `secondary: null`, so abtop's cached file records `"five_hour": null`. A five-hour Codex gauge therefore has no data to draw and reads as though nothing ran, even directly after a successful check. This comes from the Codex API response and cannot be fixed from this script.
- **Neither tool appears in the live sessions panel.** That panel maps running processes to sessions, and both checks exit after roughly three seconds, so they are gone before a refresh can catch them. This is inherent to a one-shot trigger.

## Requirements

- `sh`
- `claude`
- `codex`
- `timeout` for command timeouts, when available
- `jq` for extracting token and usage fields from JSON output

If `jq` is missing, the script still runs and prints raw tool output, but usage extraction and the totals line are skipped.

## Sample Run

Run on 2026-07-30 with default settings (`claude-haiku-4-5` / `gpt-5.4-mini`, reasoning effort `low`), workdir `~/repos/codingWithGPT`.

```
Using sh: /usr/bin/sh
Using claude: /home/mpetrick/.local/bin/claude
Using codex: /run/user/1000/fnm_multishells/8678_1785403456074/bin/codex
Trigger workdir: /home/mpetrick/repos/codingWithGPT
Claude Code model: claude-haiku-4-5
Codex model: gpt-5.4-mini
Codex reasoning effort: low
Prompt: Return only the result of 1+1.

=== Claude Code ===
Started at: Thu Jul 30 11:37:03 AM CEST 2026
Working directory: /home/mpetrick/repos/codingWithGPT
Timeout: 300s
--- Claude Code output ---
{"type":"result","subtype":"success","is_error":false,...,"result":"2","num_turns":1,
 "total_cost_usd":0.0014099999999999998,
 "usage":{"input_tokens":474,"cache_creation_input_tokens":0,
          "cache_read_input_tokens":0,"output_tokens":70,...}}
--- Claude Code summary ---
Exit code: 0
Wall clock: 2s
Claude Code totals: input=474 output=70 cache_read=0 cache_write=0 total=544 cost_usd=0.0014099999999999998
Claude Code check completed.

=== Codex ===
Started at: Thu Jul 30 11:37:05 AM CEST 2026
Working directory: /home/mpetrick/repos/codingWithGPT
Timeout: 300s
--- Codex output ---
{"type":"thread.started","thread_id":"<id>"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"2"}}
{"type":"turn.completed","usage":{"input_tokens":10668,"cached_input_tokens":8576,
                                  "output_tokens":16,"reasoning_output_tokens":9}}
--- Codex summary ---
Exit code: 0
Wall clock: 4s
Codex totals: input=10668 (cached=8576) output=16 reasoning=9 total=10684
Codex check completed.
```

Both tools answered `2`. Claude Code used 544 tokens for $0.0014; Codex used 10 684 tokens, 8 576 of them cached, and reports no cost.

### Previous behaviour, for comparison

Run on 2026-07-10, before the context-stripping flags, with the `sonnet` alias.

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

The 21 755 cache tokens in that run are the default system prompt, tool schemas and project context that the current flags no longer send.
