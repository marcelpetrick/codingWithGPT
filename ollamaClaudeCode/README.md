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

Not all models work with Claude Code. Claude Code relies on structured `tool_use`
API response blocks. Tested results:

| Model | Tool use | Notes |
|---|---|---|
| `qwen3.5` family | **✓ works** | Proper `tool_use` blocks, stop_reason=tool_use |
| `mistral-nemo:12b` | **✓ works** | Confirmed — both base and ctx20k variant |
| `qwen2.5-coder` family | **✗ broken** | Returns raw JSON text, stop_reason=end_turn |
| `codestral:22b` | **✗ broken** | Returns nothing — stop_reason=None, empty content |

**Use qwen3.5 or mistral-nemo.** Tool-use compatibility is a training-level
property that cannot be fixed by changing context windows or quantization.

---

## Benchmark — run 4 (2026-05-29, clean server, all models)

Ollama 0.24.0 — 20 models (including mistral-nemo:12b, codestral:22b and ctx
variants). Server restarted for clean VRAM state before run.

| Rank | Model | Time | Speed | VRAM | Load | Tool use | Notes |
|---|---|---|---|---|---|---|---|
| — | `qwen3.5:0.8b` | 5.5s | 157.5 tok/s | 2.35/2.35 GB | 3188ms | ✓ | Too small for complex tasks |
| — | `qwen2.5-coder:7b` | 8.8s | 68.5 tok/s | 4.92/4.92 GB | 3770ms | ✗ | Fast but tool use broken |
| — | `qwen2.5-coder:7b-ctx32k` | 11.5s | 68.4 tok/s | 8.12/8.12 GB | 6478ms | ✗ | Fast but tool use broken |
| **1** | **`qwen3.5:9b-ctx64k`** | **17.1s** | **46.0 tok/s** | **11.48/11.48 GB** | **10210ms** | **✓** | **Best all-round: 64k ctx, fully GPU** |
| 2 | `mistral-nemo:12b` | 11.5s | 46.5 tok/s | 7.68/7.68 GB | 5195ms | ✓ | Fast + tool use; needs ctx20k for Claude Code |
| 3 | `qwen3.5-ctx32k:9b` | 17.6s | 45.7 tok/s | 9.97/9.97 GB | 10563ms | ✓ | 32k ctx baked in |
| 4 | `qwen3.5:9b` | 12.8s | 45.5 tok/s | 8.8/8.8 GB | 5793ms | ✓ | Good; default ctx too small |
| — | `mrthp/omnicoder2` | 12.8s | 43.6 tok/s | 8.37/8.37 GB | 4493ms | ? | Verbose style; tool use untested |
| — | `qwen3:8b-q8_0` | 17.4s | 38.2 tok/s | 9.63/9.63 GB | 9285ms | ? | q8 quant; tool use untested |
| — | `qwen3-coder:30b` | 22.8s | 23.5 tok/s | 11.84/19.27 GB | 8651ms | ? | Split VRAM (~7.4 GB on CPU) |
| — | `mistral-nemo:12b-ctx32k` | 31.7s | 14.0 tok/s | 11.62/14.47 GB | 9426ms | ✓ | Split VRAM at ctx32k; use ctx20k instead |
| — | `codestral:22b` | 35.7s | 10.1 tok/s | 11.58/13.87 GB | 5320ms | ✗ | Always split; tool use broken |
| — | `qwen3:14b-q8_0` | 46.4s | 8.1 tok/s | 11.51/16.9 GB | 7902ms | ? | Split VRAM; q8 too heavy |
| — | `codestral:22b-ctx32k` | 93.0s | 4.2 tok/s | 11.6/23.44 GB | 20188ms | ✗ | Severe split; tool use broken |
| — | `qwen2.5-coder:32b` | 90.3s | 3.6 tok/s | 11.5/21.44 GB | 5236ms | ✗ | Severe split; tool use broken |
| — | `qwen3.5:27b` | — | 0 tok/s | 11.63/23.73 GB | — | — | Thinking mode — 0 visible tokens |
| — | `qwen3.6:27b-q4_K_M` | — | 0 tok/s | 11.63/23.73 GB | — | — | Thinking mode — 0 visible tokens |
| — | `qwen3-vl:4b/8b` | — | — | — | — | — | SKIP (vision) |
| — | `qwen3-embedding:4b` | — | — | — | — | — | SKIP (embedding) |

### mistral-nemo findings

`mistral-nemo:12b` at default 4096 context: 7.68 GB VRAM, 46.5 tok/s, tool use ✓.
At ctx32k: overflows to 14.47 GB (CPU split), drops to 14 tok/s.
**Optimal variant: `mistral-nemo:12b-ctx20k`** — 11.47 GB, fully in VRAM, 20k
context, tool use confirmed ✓.

### codestral findings

`codestral:22b` model weights alone are ~13.5 GB — permanently split on this 12 GB
GPU regardless of context. Speed is 10 tok/s at ctx4096 and 4.2 tok/s at ctx32k.
Tool use is broken (stop_reason=None, empty response). Not recommended.

---

## Benchmark — run 3 (2026-05-29, +mistral-nemo + codestral)

Ollama 0.24.0 — 20 models (added `mistral-nemo:12b`, `codestral:22b` and their
ctx32k variants). Only 1 model completed — all others chained-timeout.

**Root cause:** the 4 new models (codestral:22b-ctx32k, mistral-nemo:12b-ctx32k,
codestral:22b, mistral-nemo:12b) each triggered a model-swap from the previously
loaded `qwen3.5:9b-ctx64k`. Each swap took >180s (cold load from disk into VRAM),
each timeout left Ollama mid-swap, and every subsequent model queued behind the
stuck swap. Once the queue cleared, `qwen3.5:9b-ctx64k` — already resident in
VRAM — completed at 45.6 tok/s. Everything after it joined a new queue backlog.

| Model | Result | Notes |
|---|---|---|
| `codestral:22b-ctx32k` | TIMEOUT | First load, cold disk read, triggered model swap |
| `mistral-nemo:12b-ctx32k` | TIMEOUT | Queued behind stuck swap |
| `codestral:22b` | TIMEOUT | Same queue |
| `mistral-nemo:12b` | TIMEOUT | Same queue |
| `qwen3.5:9b-ctx64k` | **OK — 45.6 tok/s** | Already in VRAM — no swap needed |
| all others | TIMEOUT | Queued after qwen3.5 exhausted its slot |

After the run, `qwen3.5:9b-ctx64k` remained locked in VRAM (11.48 GB) with
`keep_alive` not expiring. Subsequent isolated tests of mistral-nemo and
codestral timed out at 240s. Server requires Ollama service restart to recover.
See `OLLAMA_PULL.md` for recovery procedure and retest instructions.

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

**Primary: `qwen3.5:9b-ctx64k`** — 46 tok/s, fully in VRAM (11.48 GB), 64k context,
verified tool use. Best choice for long sessions and large files.

**Runner-up: `mistral-nemo:12b-ctx20k`** — 46.5 tok/s, fully in VRAM (11.47 GB),
20k context, verified tool use. Comparable speed to the primary; strong alternative
if qwen3.5 gives unsatisfactory answers. 128k native context means a larger ctx
variant is possible once a bigger GPU is available.

**Avoid: `codestral:22b`** — tool use broken, always runs split-VRAM, slow.

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
