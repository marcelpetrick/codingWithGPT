# Claude Code with Local Ollama Server

Use Claude Code against the local network Ollama server without touching your regular Claude Code setup.

## Server info

| | |
|---|---|
| Address | `http://192.168.100.37:11434` |
| Ollama version | `0.22.0` |

## Benchmark results (CPU inference, 2026-05-28)

Tested with a real coding prompt (Sieve of Eratosthenes, 300 tokens, 180s timeout).
Server is currently running **CPU-only** — `size_vram: 0` on all models.

| Rank | Model | Time | Speed | Completes? | Notes |
|---|---|---|---|---|---|
| 1 | **`qwen3-coder:30b`** | 81s | 4.5 tok/s | ✓ | Fastest + coding-specific |
| 2 | **`qwen2.5-coder:7b`** | 83s | 3.9 tok/s | ✓ | Smallest that works |
| 3 | `qwen3.5:9b` | 104s | 3.2 tok/s | ✓ | General model |
| — | `qwen3.5:27b` | — | — | TIMEOUT | Too slow on CPU |
| — | `qwen2.5-coder:32b` | — | — | TIMEOUT | Too slow on CPU |
| — | `qwen3:14b-q8_0` | — | — | TIMEOUT | q8 quantization too heavy |
| — | `qwen3:8b-q8_0` | — | — | TIMEOUT | q8 quantization too heavy |
| — | `qwen3.5:9b-ctx64k` | — | — | TIMEOUT | Large context overhead on CPU |
| — | `qwen3.5-ctx32k:9b` | — | — | TIMEOUT | Large context overhead on CPU |
| — | `qwen2.5-coder:7b-ctx32k` | — | — | TIMEOUT | Large context overhead on CPU |
| — | `qwen3.5:0.8b` | — | — | TIMEOUT | Stuck behind queue |

> Note: the ctx-prefixed variants of working models time out because the larger
> context window significantly increases memory and CPU load. Use the plain
> variants until GPU inference is available.

## Recommended models for coding (current state)

**Primary: `qwen3-coder:30b`** — fastest on this server despite its size (4.5 tok/s),
purpose-built for code generation. Gives the best output quality of the three
models that complete requests.

**Fallback: `qwen2.5-coder:7b`** — nearly as fast (3.9 tok/s), much smaller
footprint. Use this if `qwen3-coder:30b` stops responding or the server is
under load.

Both are coding-specific models and produce correct, well-structured code output.
`qwen3.5:9b` is a general model and ranked lower for coding tasks.

**Caveat:** 80–100s per response is workable but slow for interactive sessions.
Once GPU inference is enabled on the server, expect 15–40 tok/s on these models,
making sessions genuinely interactive. See `debugging.md` for how to fix the GPU issue.

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
# Primary recommendation
claude-ol --model qwen3-coder:30b

# Fallback
claude-ol --model qwen2.5-coder:7b

# Or explicitly inline (no alias needed)
ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.37:11434 ANTHROPIC_API_KEY="" claude --model qwen3-coder:30b

# Non-interactive / headless mode
claude-ol --model qwen3-coder:30b -p "how does this repository work?"
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
