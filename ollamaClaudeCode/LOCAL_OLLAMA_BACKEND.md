# Claude Code with Local Ollama Backend

Run Claude Code against the Ollama instance on this machine — GPU-accelerated,
no network dependency.

## Local server info

| | |
|---|---|
| Address | `http://localhost:11434` |
| Ollama version | `0.23.2` |
| Inference | GPU (size_vram > 0 on all models) |

## Benchmark results (2026-05-28)

Same prompt as network server benchmark: Sieve of Eratosthenes in Python with
type hints, 300 tokens, 120s timeout. **All 11 models completed on GPU.**

| Rank | Model | Time | Speed | Load time | Notes |
|---|---|---|---|---|---|
| 1 | `qwen2.5:0.5b` | 3.9s | 138.2 tok/s | 1490ms | General, very small |
| 2 | `gemma3:270m` | 3.3s | 137.9 tok/s | 1146ms | Tiny, general |
| 3 | `deepseek-coder:1.3b` | 2.9s | 104.7 tok/s | **67ms** | Coding-specific, fastest load |
| 4 | `deepseek-r1:1.5b` | 7.8s | 99.0 tok/s | 4455ms | Reasoning model (thinks before answering) |
| 5 | `llama3.2:1b` | 5.0s | 94.1 tok/s | 1542ms | General |
| 6 | **`qwen2.5-coder:1.5b`** | 5.9s | **87.8 tok/s** | 2169ms | **Coding-specific, recommended** |
| 7 | `gemma2:2b` | 8.5s | 75.7 tok/s | 4098ms | General |
| 8 | `gemma3:1b` | 7.1s | 69.2 tok/s | 2507ms | General |
| 9 | `qwen2.5:1.5b` | 6.3s | 66.5 tok/s | 1505ms | General |
| 10 | `qwen3.5:0.8b` | 7.4s | 61.8 tok/s | 2365ms | General |
| 11 | **`qwen3.5:4b`** | 18.6s | **22.1 tok/s** | 4789ms | **Best quality, recommended** |

## Recommended models for coding

**Primary: `qwen3.5:4b`** — highest parameter count and most recent architecture
on this machine. Produces the most coherent, complete code. Slower (22 tok/s) but
still interactive at ~20s per 300-token response.

**Fast alternative: `qwen2.5-coder:1.5b`** — purpose-built for coding, nearly 4×
faster (88 tok/s), sub-6s responses. Use when you want quick turnaround for
simpler tasks or when iterating fast.

Avoid for coding: `qwen2.5:0.5b` and `gemma3:270m` are fastest but too small
to handle complex code reliably. `deepseek-r1:1.5b` uses chain-of-thought
reasoning (slow effective output for coding loops).

## Setup — claude-ol-local alias

Add to `~/.zshrc`:

```shell
alias claude-ol-local='ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY="" claude'
```

Reload:

```shell
source ~/.zshrc
```

You now have three commands:

| Command | Backend | Use when |
|---|---|---|
| `claude` | Anthropic API | Full capability, internet required |
| `claude-ol` | Network Ollama (192.168.100.37) | Network server (currently CPU-only, slow) |
| `claude-ol-local` | Local Ollama (localhost) | Local GPU, fast, offline |

## Usage

```shell
# Best quality
claude-ol-local --model qwen3.5:4b

# Fastest for coding
claude-ol-local --model qwen2.5-coder:1.5b

# Non-interactive / headless
claude-ol-local --model qwen3.5:4b -p "explain this function"

# Inline without alias
ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY="" claude --model qwen3.5:4b
```

## Verify local server

```shell
curl http://localhost:11434/api/version
# → {"version":"0.23.2"}

# Check GPU is being used (size_vram should be > 0 when a model is loaded)
curl http://localhost:11434/api/ps | python3 -c \
  'import json,sys; [print(m["name"], "vram:", m["size_vram"]) for m in json.load(sys.stdin)["models"]]'
```

## Context length note

These models use their default context windows (typically 8k–32k). Claude Code
recommends ≥64k but works fine for most tasks at smaller context. If you hit
limits, create a custom model on the server:

```shell
# Example: boost qwen3.5:4b to 32k context
cat > /tmp/Modelfile <<EOF
FROM qwen3.5:4b
PARAMETER num_ctx 32768
EOF
ollama create qwen3.5:4b-ctx32k -f /tmp/Modelfile
```
