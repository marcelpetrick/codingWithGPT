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

## Tool-use compatibility — critical

Not all models work with Claude Code. Claude Code relies on structured `tool_use`
API response blocks. Two model families behave differently:

| Model family | Tool use | Notes |
|---|---|---|
| `qwen2.5-coder` | **broken** | Outputs raw JSON text instead of `tool_use` blocks |
| `qwen3.5` | **works** | Returns proper `tool_use` blocks via Ollama's Anthropic API |

Verified by direct `/v1/messages` API test:

```shell
# qwen2.5-coder:7b-ctx32k → stop_reason: end_turn, text: raw JSON  ✗
# qwen3.5:4b              → stop_reason: tool_use, TOOL_USE block   ✓
```

**Use only `qwen3.5` models.** Tool-use compatibility is a training-level property —
it cannot be fixed by changing context windows or quantization.

---

## Benchmark — run 4 (2026-05-28, +qwen2.5-coder:7b)

Ollama 0.24.0 — 5 models. Speed reference only — tool-use compatibility was
not yet verified at this point.

| Rank | Model | Time | Speed | VRAM | Load | Notes |
|---|---|---|---|---|---|---|
| 1 | `deepseek-coder:1.3b` | 7.4s | 104.3 tok/s | 4.92 GB fully | 4366ms | Fast but tool use untested |
| 2 | `qwen2.5-coder:7b` | 11.9s | 29.7 tok/s | 4.92 GB fully | 1447ms | Tool use broken (see above) |
| 3 | `qwen3.5:4b` | 16.9s | 22.1 tok/s | fully | 2981ms | Tool use works ✓ |
| 4 | `mrthp/omnicoder2:latest` | 17.6s | 18.7 tok/s | 6.95 / 8.37 GB | 133ms | Tool use untested |
| 5 | `qwen3.6:27b-q4_K_M` | 121s | 2.8 tok/s | 7.6 / 23.7 GB | 11788ms | Too slow, VRAM overflow |

---

## Benchmark — run 3 (2026-05-28, +omnicoder2)

| Rank | Model | Time | Speed | VRAM | Load | Notes |
|---|---|---|---|---|---|---|
| 1 | `deepseek-coder:1.3b` | 7.4s | 104.3 tok/s | fully | 4366ms | |
| 2 | `qwen3.5:4b` | 16.9s | 22.1 tok/s | fully | 2981ms | |
| 3 | `mrthp/omnicoder2:latest` | 17.6s | 18.7 tok/s | 6.95 / 8.37 GB | 133ms | Verbose style |
| 4 | `qwen3.6:27b-q4_K_M` | 121s | 2.8 tok/s | 7.6 / 23.7 GB | 11788ms | Too slow |

---

## Benchmark — run 2 (2026-05-28, 3 models)

| Rank | Model | Time | Speed | VRAM | Load |
|---|---|---|---|---|---|
| 1 | `deepseek-coder:1.3b` | 7.4s | 104.3 tok/s | fully | 4366ms |
| 2 | `qwen3.5:4b` | 16.9s | 22.1 tok/s | fully | 2981ms |
| 3 | `qwen3.6:27b-q4_K_M` | 121s | 2.8 tok/s | 7.6 / 23.7 GB | 11788ms |

---

## Benchmark — run 1 (2026-05-28, earlier model set, Ollama 0.23.2)

11 models, all fully on GPU.

| Rank | Model | Time | Speed | Load |
|---|---|---|---|---|
| 1 | `qwen2.5:0.5b` | 3.9s | 138.2 tok/s | 1490ms |
| 2 | `gemma3:270m` | 3.3s | 137.9 tok/s | 1146ms |
| 3 | `deepseek-coder:1.3b` | 2.9s | 104.7 tok/s | 67ms |
| 4 | `deepseek-r1:1.5b` | 7.8s | 99.0 tok/s | 4455ms |
| 5 | `llama3.2:1b` | 5.0s | 94.1 tok/s | 1542ms |
| 6 | `qwen2.5-coder:1.5b` | 5.9s | 87.8 tok/s | 2169ms |
| 7 | `gemma2:2b` | 8.5s | 75.7 tok/s | 4098ms |
| 8 | `gemma3:1b` | 7.1s | 69.2 tok/s | 2507ms |
| 9 | `qwen2.5:1.5b` | 6.3s | 66.5 tok/s | 1505ms |
| 10 | `qwen3.5:0.8b` | 7.4s | 61.8 tok/s | 2365ms |
| 11 | `qwen3.5:4b` | 18.6s | 22.1 tok/s | 4789ms |

---

## Recommended models for coding (current)

**Primary: `qwen3.5:4b-ctx32k`** — verified tool-use support, fully in VRAM (~3.5 GB),
22 tok/s. 32k context baked in via custom Modelfile. Best choice for interactive
Claude Code sessions on this machine.

**Fast fallback: `deepseek-coder:1.3b`** — 104 tok/s but tool-use compatibility
not verified. Use only if you need raw text completions or quick non-tool tasks.

**Avoid: `qwen2.5-coder:7b-ctx32k`** — fast but tool use is broken. The model
outputs tool calls as raw JSON text rather than structured API response blocks.

---

## Setup — claude-ol-local alias

Add to `~/.zshrc`:

```shell
alias claude-ol-local='ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY="" claude --model qwen3.5:4b-ctx32k'
```

Reload:

```shell
source ~/.zshrc
```

You now have three commands:

| Command | Backend | Use when |
|---|---|---|
| `claude` | Anthropic API | Full capability, internet required |
| `claude-ol` | Network Ollama (192.168.100.37) | Network server, 9b model |
| `claude-ol-local` | Local Ollama (localhost) | Local GPU, offline |

## Usage

```shell
# Start a session — uses qwen3.5:4b-ctx32k
claude-ol-local

# Headless
claude-ol-local -p "explain this function"

# Inline without alias
ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY="" claude --model qwen3.5:4b-ctx32k
```

## Verify local server

```shell
curl http://localhost:11434/api/version
# → {"version":"0.24.0"}

# Check GPU usage
curl http://localhost:11434/api/ps | python3 -c \
  'import json,sys
for m in json.load(sys.stdin)["models"]:
    total = round(m["size"]/1e9, 1)
    vram  = round(m["size_vram"]/1e9, 1)
    print(f"{m[\"name\"]:30s}  {vram}/{total} GB in VRAM")'
```

## Context window — why it matters

Ollama defaults all models to **4096 tokens**. Claude Code's own system prompt
(tool definitions, instructions, permissions) is ~2–3k tokens. At 4096 total,
almost no room remains for actual conversation.

The `qwen3.5:4b-ctx32k` custom model raises this to 32k.

How it was created:

```shell
cat > /tmp/Modelfile-qwen35-4b <<'EOF'
FROM qwen3.5:4b
PARAMETER num_ctx 32768
EOF
ollama create qwen3.5:4b-ctx32k -f /tmp/Modelfile-qwen35-4b
```

## Known limitations

### qwen2.5-coder family — tool use broken

`qwen2.5-coder:7b` (and all variants including the ctx32k custom model) outputs
tool calls as raw JSON text strings instead of structured `tool_use` API blocks.
This is a training-level limitation — no context window change fixes it. Claude
Code shows the JSON in the terminal and stalls.

### qwen3.5 thinking mode — not a problem via Anthropic API

The qwen3.5 series uses internal reasoning (`<think>` blocks). When accessed via
Ollama's Anthropic-compatible API (`/v1/messages`), thinking tokens appear as a
separate `thinking` content block and do not interfere with the `tool_use` response.
This is only a problem when using the raw `/api/generate` endpoint (where thinking
tokens and visible output share the same token budget).

### qwen3.6:27b-q4_K_M — VRAM overflow + very slow

Exceeds available VRAM. Runs split GPU+CPU at 2.8 tok/s. Not usable for
interactive sessions until a larger VRAM GPU is available.
