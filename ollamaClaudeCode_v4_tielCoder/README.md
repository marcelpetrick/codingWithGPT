# v4 — Tiel-Coder on the Ollama server, and the field re-measured on 0.33.3

Measured on **`192.168.100.67`, Ollama 0.33.3**, 2026-09-17, ≈35.56 GB usable VRAM, server idle
before every stage, one model resident at a time.

| | |
|---|---|
| **the verdict** | below |
| every number, and how it was taken | [`measurements.md`](measurements.md) |
| the twelve harness defects found *in this round's own tooling* | [`review.md`](review.md) |
| what to put in `~/.zshrc` | [`shell_aliases.md`](shell_aliases.md) |
| one-page summary, offline | [`report.html`](report.html) · [`report.pdf`](report.pdf) |
| what was planned, before any of it ran | [`plan.md`](plan.md) |
| exact digests, versions, sampling settings | [`results/provenance.txt`](results/provenance.txt) |

---

## The verdict

**Use `tiel-coder:35b-q5-ctx256k-agentic` — the variant, never the tag as it shipped. Append
`<|think_off|>` for ordinary work.**

It displaces `north-mini-code-1.0` as the default, and it does so on correctness rather than
speed — north-mini is 23% faster per token and 13 GB lighter.

| | `north-mini` *(v3 default)* | **`tiel-coder` (pp 0)** |
|---|---|---|
| hard fixture, **held-out tests** | 18/18, **14/18**, 17/18 | **18/18, 18/18, 18/18** |
| hard fixture, median | 126 s | **83 s** *(53 s with thinking off)* |
| generation @2k | **136.2** tok/s | 111.1 |
| deepest verified recall | 201,737 | **254,181** |
| resident @262,144 | **21.3 GB** | 34.13 GB |
| past its context window | **silently halves** | **refuses (HTTP 400)** |
| vision | no | **yes** |

Two properties decide it, and neither is a speed:

1. **It fixes the specification, not the test file.** On a three-module fixture with **18
   held-out tests the model never sees**, Tiel passed all eighteen in three runs from three.
   Only `gemma4:26b-a4b` matched that. Everything else — including the v3 default and the
   long-running control — turned the *visible* tests green while leaving up to five held-out
   tests failing.
2. **It fails loudly.** Overrun its context window and it returns HTTP 400. Seven of the ten
   models measured silently keep `num_ctx/2 + 2` tokens and answer anyway. Claude Code cannot
   send `num_ctx`, so with those models you can get an answer computed from half your
   repository with nothing in the transcript to say so.

The cost is memory: **34.13 GB of a 35.56 GB box**, the tightest fit in the project. Nothing
else can be resident beside it.

### Three settings that matter more than the model choice

| | |
|---|---|
| **`presence_penalty 0`** | the shipped tag carries `1.5`, added by whoever created it — the raw download has none and the publisher recommends none. It costs **41–52% of generation** and nothing else changes |
| **`<|think_off|>`** | **2.3× faster** on the hard fixture with equal or better correctness. `MAX_THINKING_TOKENS=0` does *not* work — it only omits the field, which Ollama reads as "think" |
| **`CLAUDE_CODE_MAX_CONTEXT_TOKENS=230000`** | below the verified 254,181 retrieval ceiling, and Tiel's overflow is a visible error rather than a silent truncation |

### CyberTiel: measured, and not recommended for daily use

The abliterated sibling matches Tiel to within noise on **every** axis — generation within 1%,
recall one token apart (254,182 vs 254,181), identical memory, identical overflow behaviour,
both 25/25 on vision, both 18/18 on the hard fixture. On eight benign defensive-security prompts
**neither model refused anything**, so the uncensored build buys nothing on legitimate work — and
it has to be sandboxed to be run responsibly. Run Tiel; keep CyberTiel for a refusal that
actually blocks you, and keep it in [`cc-session-sandboxed.sh`](cc-session-sandboxed.sh) when you
do.

### What changed under everything else

**Ollama 0.33.3 caches prompt prefixes; 0.32.15 did not.** An agent turn now prefills only its
new tail — 520 tokens instead of 30,042 — so **v3's ranking rule "prefill beats generation,
because the loop re-reads its context every turn" no longer holds here.** The control
(`qwen3.6:35b-a3b`) moved +1.2%, so raw throughput is otherwise unchanged between the runtimes;
session wall-clocks are not comparable across them at all.

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
