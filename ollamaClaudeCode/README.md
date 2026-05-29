# Claude Code with Local Ollama Server

Use Claude Code against the local network Ollama server without touching your regular Claude Code setup.

## Server info

| | |
|---|---|
| Address | `http://192.168.100.37:11434` |
| Ollama version | `0.24.0` |
| Inference | GPU-accelerated (fixed with Ollama 0.24.0 upgrade) |

---

## Tool-use compatibility — critical

Not all models work with Claude Code. Claude Code relies on structured tool calls
(`tool_use` API response blocks). Two model families behave very differently:

| Model family | Tool use | Why |
|---|---|---|
| `qwen2.5-coder` | **broken** | Outputs raw JSON text; not trained on Anthropic's protocol |
| `qwen3.5` | **works** | Returns proper `tool_use` blocks via Ollama's Anthropic API layer |

Verified by direct API test:

```shell
# qwen2.5-coder:7b-ctx32k → stop_reason: end_turn, content: TEXT (raw JSON string)
# qwen3.5:9b-ctx64k       → stop_reason: tool_use, content: TOOL_USE block  ✓
```

**Use only `qwen3.5` models.** Speed and context window can be tuned; tool-use
compatibility cannot — it is a training-level property of the model.

---

## Benchmark — run 2 (2026-05-29, GPU enabled)

Ollama 0.24.0 — GPU now active. 16 models, 3 skipped (vision/embedding).
Prompt: Sieve of Eratosthenes in Python, 300 tokens, 180s timeout.

| Rank | Model | Time | Speed | VRAM | Load | Tool use | Notes |
|---|---|---|---|---|---|---|---|
| — | `qwen3.5:0.8b` | 5.5s | 156.4 tok/s | 2.35/2.35 GB | 3223ms | ✓ | Too small for complex tasks |
| — | `qwen2.5-coder:7b-ctx32k` | 11.5s | 68.4 tok/s | 8.12/8.12 GB | 6476ms | **✗** | Fast but tool use broken |
| — | `qwen2.5-coder:7b` | 14.9s | 68.4 tok/s | 4.92/4.92 GB | 9829ms | **✗** | Fast but tool use broken |
| **1** | **`qwen3.5:9b-ctx64k`** | **17.1s** | **45.3 tok/s** | **11.48/11.48 GB** | **9942ms** | **✓** | **Best: tool use + ctx64k + fully GPU** |
| 2 | `qwen3.5:9b` | 18.9s | 45.6 tok/s | 8.8/8.8 GB | 11846ms | ✓ | Good; needs ctx32k custom model |
| 3 | `qwen3.5-ctx32k:9b` | 21.1s | 45.9 tok/s | 9.97/9.97 GB | 14071ms | ✓ | 32k ctx baked in |
| — | `mrthp/omnicoder2:latest` | 18.8s | 43.0 tok/s | 8.37/8.37 GB | 10454ms | ? | Verbose prose; untested for tool use |
| — | `qwen3:8b-q8_0` | 17.2s | 38.1 tok/s | 9.63/9.63 GB | 9012ms | ? | q8 quantization; untested |
| — | `qwen3-coder:30b` | 36.9s | 26.2 tok/s | 11.84/19.27 GB | 23841ms | ? | Split VRAM (~7.4 GB to CPU) |
| — | `qwen3:14b-q8_0` | 47.6s | 7.8 tok/s | 11.51/16.9 GB | 7904ms | ? | Split VRAM; q8 too heavy |
| — | `qwen2.5-coder:32b` | 119.2s | 3.6 tok/s | 11.5/21.44 GB | 33181ms | **✗** | Severe VRAM split + tool use broken |
| — | `qwen3.5:27b` | — | 0 tok/s | 11.63/23.73 GB | — | — | Thinking consumes all tokens |
| — | `qwen3.6:27b-q4_K_M` | — | 0 tok/s | 11.63/23.73 GB | — | — | Thinking consumes all tokens |
| — | `qwen3-vl:4b/8b` | — | — | — | — | — | SKIP (vision) |
| — | `qwen3-embedding:4b` | — | — | — | — | — | SKIP (embedding) |

---

## Benchmark — run 1 (2026-05-28, CPU-only, Ollama 0.22.0)

Historical. Server was running CPU-only (`size_vram: 0`) — all models ran in system RAM.

| Rank | Model | Time | Speed | Completes? |
|---|---|---|---|---|
| 1 | `qwen3-coder:30b` | 81s | 4.5 tok/s | ✓ |
| 2 | `qwen2.5-coder:7b` | 83s | 3.9 tok/s | ✓ |
| 3 | `qwen3.5:9b` | 104s | 3.2 tok/s | ✓ |
| — | all others | — | — | TIMEOUT |

GPU fix details in `debugging.md`.

---

## Recommended models for coding (current)

**Primary: `qwen3.5:9b-ctx64k`** — 45.3 tok/s, fully in VRAM (11.48 GB), 64k context
baked in, verified tool-use support. Default for the `claude-ol` alias.

**Runner-up: `qwen3.5:9b`** — identical architecture and speed, but only 4096 token
default context. Needs a custom Modelfile to be useful with Claude Code.

---

## Setup — keep both modes working

Add this alias to your `~/.zshrc`:

```shell
alias claude-ol='ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.37:11434 ANTHROPIC_API_KEY="" claude --model qwen3.5:9b-ctx64k'
```

Reload:

```shell
source ~/.zshrc
```

You now have three commands:

| Command | Backend | Model |
|---|---|---|
| `claude` | Anthropic API | Claude (real) |
| `claude-ol` | Network Ollama (192.168.100.37) | `qwen3.5:9b-ctx64k` |
| `claude-ol-local` | Local Ollama (localhost) | `qwen3.5:4b-ctx32k` |

## Usage

```shell
# Default
claude-ol

# Override to the 9b runner-up (same family, already the default)
claude-ol --model qwen3.5:9b

# Inline without alias
ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.37:11434 ANTHROPIC_API_KEY="" claude --model qwen3.5:9b-ctx64k

# Headless
claude-ol -p "how does this repository work?"
```

## Verify the server is reachable

```shell
curl http://192.168.100.37:11434/api/version
# → {"version":"0.24.0"}

# List available models
curl http://192.168.100.37:11434/api/tags | jq '.models[].name'

# Check GPU usage
curl http://192.168.100.37:11434/api/ps | python3 -c \
  'import json,sys
for m in json.load(sys.stdin)["models"]:
    total = round(m["size"]/1e9, 1)
    vram  = round(m["size_vram"]/1e9, 1)
    print(f"{m[\"name\"]:30s}  {vram}/{total} GB in VRAM")'
```

## How it works

Claude Code connects to any Anthropic-compatible API. Ollama exposes one at
`http://<host>:11434`. Three env vars redirect the traffic:

- `ANTHROPIC_BASE_URL` — points to the Ollama server instead of Anthropic's API
- `ANTHROPIC_AUTH_TOKEN=ollama` — placeholder; Ollama doesn't validate tokens
- `ANTHROPIC_API_KEY=""` — clears the real key so it isn't sent accidentally

Your normal `claude` command is untouched because it reads the real
`ANTHROPIC_API_KEY` from the environment as usual.
