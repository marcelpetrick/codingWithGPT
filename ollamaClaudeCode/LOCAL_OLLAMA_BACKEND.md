# Claude Code with Local Ollama Backend

Run Claude Code against the Ollama instance on this machine — GPU-accelerated,
no network dependency.

## Local server info

| | |
|---|---|
| Address | `http://localhost:11434` |
| Ollama version | `0.24.0` |
| Inference | GPU (fully for small models; split GPU/CPU for 27b) |

---

## Benchmark — run 4 (2026-05-28, +qwen2.5-coder:7b)

Ollama 0.24.0 — 5 models. New: `qwen2.5-coder:7b` (Alibaba coding model,
Q4_K_M, 4.7 GB on disk).

| Rank | Model | Time | Speed | VRAM | Load | Notes |
|---|---|---|---|---|---|---|
| 1 | `deepseek-coder:1.3b` | 7.4s | 104.3 tok/s | 4.92 GB fully | 4366ms | Fastest, basic output |
| 2 | **`qwen2.5-coder:7b`** | **11.9s** | **29.7 tok/s** | **4.92 GB fully** | **1447ms** | **New best: speed + quality** |
| 3 | `qwen3.5:4b` | 16.9s | 22.1 tok/s | fully | 2981ms | Good general model |
| 4 | `mrthp/omnicoder2:latest` | 17.6s | 18.7 tok/s | 6.95 / 8.37 GB | 133ms | Verbose, split VRAM |
| 5 | `qwen3.6:27b-q4_K_M` | 121s | 2.8 tok/s | 7.6 / 23.7 GB | 11788ms | Too slow, VRAM overflow |

### qwen2.5-coder:7b evaluation

- **Speed:** 29.7 tok/s — faster than `qwen3.5:4b` (22.1) despite having more parameters
- **VRAM:** 4.92 / 4.92 GB — fully in VRAM with ~3 GB headroom remaining
- **Load time:** 1447ms
- **Output style:** direct — opened immediately with a code block, no prose preamble
- **Output quality:** correct sieve implementation, proper `List[int]` type hint,
  clean docstring, efficient loop structure, and included a self-test function

**Verdict: new primary recommendation.** Best quality-per-second of all tested
models. Coding-specific architecture, fully in VRAM, faster and better output
than `qwen3.5:4b`.

---

## Benchmark — run 3 (2026-05-28, +omnicoder2)

Ollama 0.24.0 — 4 models. New: `mrthp/omnicoder2:latest` (9B Qwen3.5-based
coding model, Q4_K_M, 5.7 GB).

| Rank | Model | Time | Speed | VRAM | Load | Notes |
|---|---|---|---|---|---|---|
| 1 | **`deepseek-coder:1.3b`** | 7.4s | **104.3 tok/s** | fully | 4366ms | Coding-specific, fastest |
| 2 | **`qwen3.5:4b`** | 16.9s | **22.1 tok/s** | fully | 2981ms | Best balance, direct output |
| 3 | `mrthp/omnicoder2:latest` | 17.6s | 18.7 tok/s | 6.95 / 8.37 GB | 133ms | 9B coding model, verbose style |
| 4 | `qwen3.6:27b-q4_K_M` | 121s | 2.8 tok/s | 7.6 / 23.7 GB | 11788ms | Too slow — heavy VRAM overflow |

### omnicoder2 evaluation

- **Speed:** 18.7 tok/s — similar to `qwen3.5:4b`, slightly slower despite being 9B
- **VRAM:** 6.95 / 8.37 GB — mostly GPU-bound, minimal spillover (~1.4 GB to CPU RAM)
- **Load time:** 133ms
- **Output style:** verbose — used all 300 tokens writing a prose explanation
  before reaching any code. Drawback for Claude Code tool-call loops.

**Verdict:** not recommended over `qwen3.5:4b`.

---

## Benchmark — run 2 (2026-05-28, 3 models)

Ollama 0.24.0 — 3 models available. Same prompt: Sieve of Eratosthenes in
Python with type hints, 300 tokens.

| Rank | Model | Time | Speed | VRAM used | Load | Notes |
|---|---|---|---|---|---|---|
| 1 | **`deepseek-coder:1.3b`** | 7.4s | **104.3 tok/s** | fully in VRAM | 4366ms | Coding-specific, fastest |
| 2 | **`qwen3.5:4b`** | 16.9s | **22.1 tok/s** | fully in VRAM | 2981ms | Best quality of fast models |
| 3 | `qwen3.6:27b-q4_K_M` | 121s | 2.8 tok/s | 7.6 / 23.7 GB | 11788ms | Split GPU+CPU — too slow for interactive use |

`qwen3.6:27b` exceeds available VRAM: only 7.6 GB of its 23.7 GB fits on GPU,
the rest runs from system RAM on CPU. That's why it drops to 2.8 tok/s despite
being locally present.

---

## Benchmark — run 1 (2026-05-28, earlier model set)

Ollama 0.23.2 — 11 models, all completed fully on GPU.

| Rank | Model | Time | Speed | Load | Notes |
|---|---|---|---|---|---|
| 1 | `qwen2.5:0.5b` | 3.9s | 138.2 tok/s | 1490ms | General, very small |
| 2 | `gemma3:270m` | 3.3s | 137.9 tok/s | 1146ms | Tiny, general |
| 3 | `deepseek-coder:1.3b` | 2.9s | 104.7 tok/s | 67ms | Coding-specific |
| 4 | `deepseek-r1:1.5b` | 7.8s | 99.0 tok/s | 4455ms | Reasoning model |
| 5 | `llama3.2:1b` | 5.0s | 94.1 tok/s | 1542ms | General |
| 6 | `qwen2.5-coder:1.5b` | 5.9s | 87.8 tok/s | 2169ms | Coding-specific |
| 7 | `gemma2:2b` | 8.5s | 75.7 tok/s | 4098ms | General |
| 8 | `gemma3:1b` | 7.1s | 69.2 tok/s | 2507ms | General |
| 9 | `qwen2.5:1.5b` | 6.3s | 66.5 tok/s | 1505ms | General |
| 10 | `qwen3.5:0.8b` | 7.4s | 61.8 tok/s | 2365ms | General |
| 11 | `qwen3.5:4b` | 18.6s | 22.1 tok/s | 4789ms | Best quality |

---

## Recommended models for coding (current)

**Primary: `qwen2.5-coder:7b`** — best overall. Fully in VRAM (4.92 GB), 29.7 tok/s,
~12s per 300-token response. Coding-specific architecture produces clean, correct
code with proper type hints — no prose preamble wasting context.

**Fast fallback: `deepseek-coder:1.3b`** — 104 tok/s, sub-8s. Use when you need
near-instant turnaround for simple completions or quick edits.

**`qwen3.5:4b`** — solid general model, slower than `qwen2.5-coder:7b` at 22 tok/s.
Useful if a task is not purely code-focused.

**Avoid: `qwen3.6:27b-q4_K_M`** — exceeds VRAM. Runs split GPU+CPU at 2.8 tok/s.
Not usable for interactive sessions until a larger VRAM GPU is available.

---

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
# Best quality — recommended primary
claude-ol-local --model qwen2.5-coder:7b

# Fastest for simple tasks
claude-ol-local --model deepseek-coder:1.3b

# Non-interactive / headless
claude-ol-local --model qwen2.5-coder:7b -p "explain this function"

# Inline without alias
ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY="" claude --model qwen2.5-coder:7b
```

## Verify local server

```shell
curl http://localhost:11434/api/version
# → {"version":"0.24.0"}

# Check GPU usage — size_vram should equal (or be close to) size for small models
curl http://localhost:11434/api/ps | python3 -c \
  'import json,sys
for m in json.load(sys.stdin)["models"]:
    total = round(m["size"]/1e9, 1)
    vram  = round(m["size_vram"]/1e9, 1)
    print(f"{m[\"name\"]:30s}  {vram}/{total} GB in VRAM")'
```

## Context length note

These models use their default context windows (typically 8k–32k). Claude Code
recommends ≥64k but works fine for most tasks at smaller context. If you hit
limits, create a custom model on the server:

```shell
# Example: boost qwen3.5:4b to 32k context
cat > /tmp/Modelfile <<'EOF'
FROM qwen3.5:4b
PARAMETER num_ctx 32768
EOF
ollama create qwen3.5:4b-ctx32k -f /tmp/Modelfile
```
