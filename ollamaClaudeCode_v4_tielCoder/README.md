# v4 — Tiel-Coder on the Ollama server, and the field re-measured on 0.33.3

> **Status: in progress.** The connection guide below is complete. Results land in
> [`measurements.md`](measurements.md) and the verdict is added here when the run finishes.
> [`plan.md`](plan.md) is what was set out to do, before any benchmark ran.

---

## How Claude Code talks to the Ollama server — what to do, and where

This setup has no proxy, gateway or plugin. **Ollama itself speaks the Anthropic Messages API**
(`POST /v1/messages`), so Claude Code is pointed straight at it with environment variables.
Every earlier round (`../ollamaClaudeCode_v0` … `_v3_qwen3.8`) used exactly this path.

### 1. The servers

| host | Ollama | what it is | use it for |
|---|---|---|---|
| **`192.168.100.67:11434`** | **0.33.3** (2026-09-17) | 35.56 GB usable VRAM, measured twice (v3 §19c). **Shared with a colleague** | everything in this repo |
| `192.168.100.37:11434` | 0.32.15 | ~12 GB, 1.4× slower on an identical model (v1) | small models only |
| `localhost:11434` | — | the laptop | ≤4B toy models |

No auth, plain HTTP. There is **no SSH** to either server (`publickey,password` refused), so
GPU temperature, utilisation and total VRAM are unobtainable. The Ollama API exposes only
per-model `size` / `size_vram` in `/api/ps`.

### 2. The network: USB ethernet, not wifi

`192.168.100.0/24` is reachable **only through the USB ethernet adapter**
(`enp0s13f0u1u4`, laptop address `192.168.100.54`). Wifi is on `10.x` and cannot see it. If
the server "is down", check the adapter first:

```shell
ip -br addr show enp0s13f0u1u4          # expect 192.168.100.x/24, state UP
curl -s http://192.168.100.67:11434/api/version
curl -s http://192.168.100.67:11434/api/tags | jq -r '.models[].name'
curl -s http://192.168.100.67:11434/api/ps   # what is resident right now, and whose
```

### 3. Pointing Claude Code at a model

```shell
H=http://192.168.100.67:11434
M=<a tag with num_ctx baked in>

ANTHROPIC_AUTH_TOKEN=ollama \
ANTHROPIC_BASE_URL="$H" \
ANTHROPIC_API_KEY="" \
ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
ANTHROPIC_DEFAULT_SONNET_MODEL="$M" \
ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \
CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 \
  claude --model "$M"
```

This is installed in `~/.zshrc` as the `claude-ol*` shell functions (`claude-ol2`,
`claude-ol-north`, `claude-ol-ornith`, `claude-ol-nemo`). Each line is there because
something broke without it:

| setting | why — measured, not assumed | where it was found |
|---|---|---|
| `ANTHROPIC_BASE_URL` = the server root | Claude Code appends `/v1/messages` itself | v0 |
| `ANTHROPIC_AUTH_TOKEN=ollama`, `ANTHROPIC_API_KEY=""` | Ollama ignores the token, but Claude Code needs one set and must not fall back to a real Anthropic key | v0 |
| **all four model slots → the same tag** | subagents resolve the `opus` alias and background work resolves `haiku`. An unset slot sends `claude-opus-5` to Ollama → **HTTP 404**. A slot pointing at a *different* local tag evicts the resident model, costing a ~70 s reload per call | v3 `shell_aliases.md`, v1 |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` **below** the baked `num_ctx` | overflowing `num_ctx` does not error. Ollama **silently keeps half the window and stops emitting tool calls**. 200,000 under a 262,144 window leaves ~62k for generation | v1 `review2.md`, v2, v3 §31 |
| a **function** that pre-warms with `keep_alive: 2h` | a 20–34 GB cold load otherwise stalls the first prompt silently | v2 `shell_aliases.md` |

### 4. The model tag: always bake `num_ctx`

**Never point Claude Code at a bare tag.** `/v1/messages` has no `num_ctx` parameter, so a tag
without one baked in caps at **16,384 tokens**, and past that **tool calling stops with no
error** (v1, re-confirmed on 0.32.9 and 0.32.15). Make an `-agentic` variant once. Tags share
weight blobs, so it costs zero disk:

```shell
curl -s http://192.168.100.67:11434/api/create -d '{
  "model": "<name>-ctx256k-agentic",
  "from":  "<source tag>",
  "parameters": {"num_ctx": 262144, "presence_penalty": 0},
  "stream": false}'
```

Two further settings have cost real throughput or correctness before:

- **`presence_penalty 1.5`**, a Qwen vendor default, cost **~35% of generation speed** (v1).
  The `Tiel-Coder…ctx262k` tag on the box ships with it. v4 measures what it costs there.
- **Residency.** `size_vram < size` in `/api/ps` means the model spilled to system RAM. A
  12.5% spill cost **5.3× throughput** (v1). Bake the largest window that stays at 100% GPU.

### 5. Sharing the box

`.67` belongs to a colleague. **Before any benchmark, check `/api/ps`.** If a model you did
not load is resident, someone is using it: wait, do not unload it. `idle.sh` in this directory
enforces that. It unloads only tags this project owns and polls read-only for anything else.

### 6. Talking to the API directly (for tests)

| endpoint | use | gotcha |
|---|---|---|
| `POST /v1/messages` | what Claude Code uses; tool-gate tests | disable thinking with `"thinking":{"type":"disabled"}`. Ollama's `think:false` is **ignored** here. Give tool tests ≥4,000 `max_tokens` or thinking eats the budget |
| `POST /api/chat` | throughput, needle, vision | `think:false` works here. `options.num_ctx` works here |
| `GET /api/ps` | residency, `context_length` | the only memory signal there is |
| `POST /api/show` | params, template, capabilities | the `template` field is what runs. The Modelfile's printed `TEMPLATE` can differ (Tiel, see `plan.md` §1) |

---

## Where everything is

| path | what |
|---|---|
| `../ollamaClaudeCode_v0/` | first contact: `LOCAL_OLLAMA_SERVER.md`, `LOCAL_OLLAMA_BACKEND.md`, which model families emit real `tool_use` blocks |
| `../ollamaClaudeCode_v1/` | round 1–2: `review2.md` (the four silent traps), `agentic-test.sh` (gates T1–T7) |
| `../ollamaClaudeCode_v2/` | Muse Glimmer + Nemotron: the two truncation bugs, `shell_aliases.md` |
| `../ollamaClaudeCode_v3_qwen3.8/` | Qwen3.8 + the 2026-08 field on 0.32.15: `README.md` verdict, `measurements.md` §1–33, `shell_aliases.md` |
| `../ollamaClaude_ImageProcessing/` | qwen3-vl OCR study; its fixtures are reused by v4's vision bench |
| **this directory** | v4: `plan.md`, `measurements.md`, harness scripts, `results/` |
