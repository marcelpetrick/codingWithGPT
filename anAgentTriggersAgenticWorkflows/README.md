# Agentic Workflows via Claude Code CLI

How to trigger Claude Code non-interactively from shell scripts, and a file-watcher that auto-reviews Git repositories.

---

## Non-Interactive Mode: the `-p` flag

```bash
claude -p "Your task description"
```

The `-p` / `--print` flag runs Claude Code in headless mode: it executes the prompt, completes the task, and exits. No interactive shell, no waiting for user input. This is the core primitive for scripting agentic workflows.

---

## Key Flags for Automation

| Flag | Purpose |
|------|---------|
| `-p "prompt"` | Non-interactive: run prompt and exit |
| `--dangerously-skip-permissions` | Auto-approve all tool calls (required for unattended runs) |
| `--model <model-id>` | Pin a specific model (e.g. `claude-opus-4-8`) |
| `--output-format text\|json\|stream-json` | Control output format |
| `--max-turns N` | Safety cap on agentic loop iterations |

---

## Full Agentic Capabilities Still Work

Running with `-p` does **not** restrict what Claude Code can do. The agent still has access to:

- All built-in tools: `Bash`, `Read`, `Write`, `Edit`, `WebSearch`, `WebFetch`, etc.
- The `Agent` tool — spawning subagents, running them in parallel, using specialized types (Explore, Plan, etc.)
- MCP servers (if configured)
- Multi-step reasoning across as many turns as needed

The only differences from interactive mode:
- No user input mid-task (prompt must be self-contained)
- `--dangerously-skip-permissions` auto-approves tool calls that would normally pause for confirmation
- Output streams to stdout

---

## What `--max-turns` Limits

One **turn** = one iteration of: Claude reasons → calls tools → receives results → reasons again.

`--max-turns 10` means Claude can go through at most 10 of those cycles before the process stops, even if the task is incomplete.

What it does **not** limit:
- Tool calls within a single turn (Claude can call many tools in parallel in one turn)
- Output length
- Number of subagents spawned

Subagents run their own turn counters independently — the parent's `--max-turns` does not cap them.

In practice, well-scoped tasks (clone → review → write file → exit) complete in 5–15 turns. Use `--max-turns` as a safety net against infinite loops.

---

## File-Watcher Pattern: `watcher.sh`

`watcher.sh` implements a simple queue-based automation loop:

1. Polls `tasks.md` every 10 seconds
2. Reads the first line (a Git repo URL)
3. Removes that line from `tasks.md`
4. Spawns `claude -p` to clone the repo, review it, and write findings
5. Cleans up the cloned repo
6. Loops back

### Backend

The watcher uses a local **Ollama** instance as the Claude API backend, running `qwen3.5:9b-ctx80k`. This mirrors the `claude-ol` shell alias:

```bash
ANTHROPIC_AUTH_TOKEN=ollama \
ANTHROPIC_BASE_URL=http://192.168.100.37:11434 \
ANTHROPIC_API_KEY="" \
claude --model qwen3.5:9b-ctx80k --dangerously-skip-permissions
```

Because shell aliases are not available inside scripts, `watcher.sh` sets these environment variables directly via `export`.

### Usage

```bash
# Add repos to review (one URL per line)
echo "https://github.com/some/repo" >> tasks.md
echo "https://github.com/another/repo" >> tasks.md

# Start the watcher
chmod +x watcher.sh
./watcher.sh
```

Results are written as `review_<timestamp>_<reponame>.md` in this directory.  
Logs are appended to `watcher.log`.

### tasks.md format

One Git repository URL per line. Lines are consumed top-to-bottom. You can append new URLs while the watcher is running.

```
https://github.com/foo/bar
https://github.com/baz/qux
```

---

## Cost Awareness

Each review invocation spins up a full Claude Code session. Subagents within it are billed as separate API calls. For large repos or many queued tasks, monitor usage. Use `--max-turns` and a focused prompt to keep costs predictable.
