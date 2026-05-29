# Claude Code with Local Ollama Server

Use Claude Code against the local network Ollama server without touching your regular Claude Code setup.

## Server info

| | |
|---|---|
| Address | `http://192.168.100.37:11434` |
| Ollama version | `0.24.0` |
| Inference | GPU-accelerated (fixed with Ollama 0.24.0 upgrade) |

---

## Benchmark — run 2 (2026-05-29, GPU enabled)

Ollama 0.24.0 — GPU now active. 16 models, 3 skipped (vision/embedding).
Prompt: Sieve of Eratosthenes in Python, 300 tokens, 180s timeout.

| Rank | Model | Time | Speed | VRAM | Load | Notes |
|---|---|---|---|---|---|---|
| 1 | `qwen3.5:0.8b` | 5.5s | **156.4 tok/s** | 2.35/2.35 GB | 3223ms | Tiny; limited quality |
| 2 | **`qwen2.5-coder:7b-ctx32k`** | **11.5s** | **68.4 tok/s** | **8.12/8.12 GB** | **6476ms** | **Best: speed + quality + 32k ctx** |
| 3 | `qwen2.5-coder:7b` | 14.9s | 68.4 tok/s | 4.92/4.92 GB | 9829ms | Same speed but 4k ctx — needs ctx32k fix |
| 4 | `qwen3.5:9b-ctx64k` | 17.1s | 45.3 tok/s | 11.48/11.48 GB | 9942ms | 64k ctx baked in; good runner-up |
| 5 | `qwen3.5:9b` | 18.9s | 45.6 tok/s | 8.8/8.8 GB | 11846ms | Solid; needs ctx32k for Claude Code |
| 6 | `qwen3.5-ctx32k:9b` | 21.1s | 45.9 tok/s | 9.97/9.97 GB | 14071ms | 32k ctx baked in |
| 7 | `mrthp/omnicoder2:latest` | 18.8s | 43.0 tok/s | 8.37/8.37 GB | 10454ms | Verbose prose style |
| 8 | `qwen3:8b-q8_0` | 17.2s | 38.1 tok/s | 9.63/9.63 GB | 9012ms | q8 quantization, not coding-specific |
| 9 | `qwen3-coder:30b` | 36.9s | 26.2 tok/s | 11.84/19.27 GB | 23841ms | Split VRAM (~7.4 GB to CPU RAM) |
| 10 | `qwen3:14b-q8_0` | 47.6s | 7.8 tok/s | 11.51/16.9 GB | 7904ms | Split VRAM; q8 too heavy |
| 11 | `qwen2.5-coder:32b` | 119.2s | 3.6 tok/s | 11.5/21.44 GB | 33181ms | Severe VRAM split; too slow |
| — | `qwen3.5:27b` | 9.3s | **0 tok/s** | 11.63/23.73 GB | — | Thinking mode — consumes all tokens |
| — | `qwen3.6:27b-q4_K_M` | 19.1s | **0 tok/s** | 11.63/23.73 GB | — | Thinking mode — consumes all tokens |
| — | `qwen3-vl:4b` | — | — | — | — | SKIP (vision) |
| — | `qwen3-vl:8b` | — | — | — | — | SKIP (vision) |
| — | `qwen3-embedding:4b` | — | — | — | — | SKIP (embedding) |

### Notes

- **Thinking-mode models** (`qwen3.5:27b`, `qwen3.6:27b-q4_K_M`): generate 0 visible tokens because the
  entire 300-token budget is spent on internal `<think>` reasoning blocks. Cannot be disabled
  through Ollama's Anthropic-compatible API. Unusable for interactive sessions.
- **Split-VRAM models** (`qwen3-coder:30b`, `qwen3:14b-q8_0`, `qwen2.5-coder:32b`): part of the model
  runs in system RAM on CPU. Speed drops proportionally to the overflow.
- **Context window**: models without a `ctx32k`/`ctx64k` suffix default to 4096 tokens — too small
  for Claude Code's system prompt. Use the ctx-prefixed variants or create a custom Modelfile.

---

## Benchmark — run 1 (2026-05-28, CPU-only, Ollama 0.22.0)

Historical. Server was running CPU-only (`size_vram: 0`) — all models ran in system RAM.

| Rank | Model | Time | Speed | Completes? |
|---|---|---|---|---|
| 1 | `qwen3-coder:30b` | 81s | 4.5 tok/s | ✓ |
| 2 | `qwen2.5-coder:7b` | 83s | 3.9 tok/s | ✓ |
| 3 | `qwen3.5:9b` | 104s | 3.2 tok/s | ✓ |
| — | all others | — | — | TIMEOUT |

Only 3 of 10 models finished within 180s. GPU fix in `debugging.md`.

---

## Recommended models for coding (current)

**Primary: `qwen2.5-coder:7b-ctx32k`** — 68.4 tok/s, fully in VRAM (8.12 GB), 32k context
baked in. Coding-specific architecture (Alibaba Qwen2.5-Coder series). Produces clean,
correct code immediately without prose preamble. Fastest meaningful model on this server.

**Runner-up: `qwen3.5:9b-ctx64k`** — 45.3 tok/s, fully in VRAM (11.48 GB), 64k context
baked in. Larger general model; useful for tasks beyond pure code generation. Approximately
33% slower than the primary but gives a broader knowledge base.

Both models have the context window already set large enough for Claude Code to function
correctly — no additional setup required beyond the alias below.

## Setup — keep both modes working

Add this alias to your `~/.zshrc` (or `~/.bashrc`):

```shell
alias claude-ol='ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.37:11434 ANTHROPIC_API_KEY="" claude --model qwen2.5-coder:7b-ctx32k'
```

Then reload:

```shell
source ~/.zshrc
```

That's it. Now you have two commands:

| Command | Backend |
|---|---|
| `claude` | Regular Anthropic API (unchanged) |
| `claude-ol` | Network Ollama server (GPU-accelerated) |

## Usage

```shell
# Default — uses qwen2.5-coder:7b-ctx32k
claude-ol

# Override to the 9b runner-up for non-code tasks
claude-ol --model qwen3.5:9b-ctx64k

# Or explicitly inline (no alias needed)
ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.37:11434 ANTHROPIC_API_KEY="" claude --model qwen2.5-coder:7b-ctx32k

# Non-interactive / headless mode
claude-ol -p "how does this repository work?"
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
