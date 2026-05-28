# Claude Code with Local Ollama Server

Use Claude Code against the local network Ollama server without touching your regular Claude Code setup.

## Server info

| | |
|---|---|
| Address | `http://192.168.100.37:11434` |
| Ollama version | `0.22.0` |

## Available models

| Model | Context | Notes |
|---|---|---|
| `qwen3-coder:30b` | check below | Best coding model on this server — largest, coding-specific |
| `qwen3.5:27b` | default | Best general model on this server |
| **`qwen3.5:9b-ctx64k`** | **64k** | **Recommended** — Claude Code needs ≥64k tokens; this is explicitly configured for it |
| `qwen3.5:9b` | default | Smaller context, fast |
| `qwen3.5-ctx32k:9b` | 32k | Below recommended minimum for Claude Code |
| `qwen2.5-coder:32b` | default | Large coder alternative |
| `qwen2.5-coder:7b-ctx32k` | 32k | Below recommended minimum |
| `qwen2.5-coder:7b` | default | |

**Best pick for Claude Code: `qwen3.5:9b-ctx64k`**
Claude Code needs at least 64k context. This model is explicitly configured to that window. If you want raw coding power and context isn't an issue, try `qwen3-coder:30b` (verify its default context first).

## Setup — keep both modes working

Add this alias to your `~/.zshrc` (or `~/.bashrc`):

```shell
alias claude-ol='ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.37:11434 ANTHROPIC_API_KEY="" claude'
```

Then reload:

```shell
source ~/.zshrc
```

That's it. Now you have two commands:

| Command | Backend |
|---|---|
| `claude` | Regular Anthropic API (unchanged) |
| `claude-ol` | Local Ollama server |

## Usage

```shell
# Start Claude Code on the local Ollama server with the recommended model
claude-ol --model qwen3.5:9b-ctx64k

# Or explicitly inline (no alias needed)
ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.37:11434 ANTHROPIC_API_KEY="" claude --model qwen3.5:9b-ctx64k

# Try the big coder model
claude-ol --model qwen3-coder:30b

# Non-interactive / headless mode
claude-ol --model qwen3.5:9b-ctx64k -p "how does this repository work?"
```

## Verify the server is reachable

```shell
curl http://192.168.100.37:11434/api/version
# → {"version":"0.22.0"}

# List available models
curl http://192.168.100.37:11434/api/tags | jq '.models[].name'
```

## How it works

Claude Code connects to any Anthropic-compatible API. Ollama exposes one at `http://<host>:11434`. Three env vars redirect the traffic:

- `ANTHROPIC_BASE_URL` — points to the Ollama server instead of Anthropic's API
- `ANTHROPIC_AUTH_TOKEN=ollama` — placeholder value; Ollama doesn't validate tokens
- `ANTHROPIC_API_KEY=""` — clears the real key so it isn't accidentally sent

Your normal `claude` command is untouched because it reads your real `ANTHROPIC_API_KEY` from the environment as usual.

## Context length (if responses get truncated)

Ollama's default context may be too short. You can increase it globally:

```shell
# Set num_ctx to 65536 for a running model
curl http://192.168.100.37:11434/api/generate -d '{
  "model": "qwen3.5:9b-ctx64k",
  "options": { "num_ctx": 65536 }
}'
```

Or create a custom Modelfile on the server and use `ollama create`. The `qwen3.5:9b-ctx64k` model is already configured for 64k, so this is only needed for other models.
