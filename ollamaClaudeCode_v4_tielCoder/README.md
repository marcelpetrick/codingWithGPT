# v4 — Tiel-Coder on the Ollama server, and the field re-measured on 0.33.3

Measured on **`192.168.100.67`, Ollama 0.33.3**, 2026-09-17/18, ≈35.56 GB usable VRAM, server
idle before every stage, one model resident at a time. **Verdict revised 2026-09-25**: the
parity round, four candidates and a same-version re-baseline are in. The 2026-09-21 verdict is kept below it as history.

| | |
|---|---|
| **the verdict** | below. The round that produced it: [`ROUND_2026-09-24.md`](ROUND_2026-09-24.md) · dashboard: [`dashboard.html`](dashboard.html) |
| every model found, and what was decided about it | [`CANDIDATE_REGISTER.md`](CANDIDATE_REGISTER.md) |
| every number, and how it was taken | [`measurements.md`](measurements.md) |
| the twelve harness defects found *in this round's own tooling* | [`review.md`](review.md) |
| how to evaluate a new model at all — rules, traps, the standing field | [`BENCHMARK_HARNESS.md`](BENCHMARK_HARNESS.md) |
| the official Terminal-Bench round, and why its ranking is void | [`terminalbench/official/OFFICIAL_TB_PLAN.md`](terminalbench/official/OFFICIAL_TB_PLAN.md) |
| candidates for the next round, and what fits this box | [`toTest.md`](toTest.md) |
| what to put in `~/.zshrc` | [`shell_aliases.md`](shell_aliases.md) |
| one-page summary, offline | [`report.html`](report.html) · [`report.pdf`](report.pdf) |
| what was planned, before any of it ran | [`plan.md`](plan.md) |
| exact digests, versions, sampling settings | [`results/provenance.txt`](results/provenance.txt) |

---

## The verdict (2026-09-25, after the same-version re-baseline)

**Keep `qwen3.6:35b-a3b-q4_K_M-agentic` (greedy) for agentic coding with Claude Code. `kat-coder-v2.5:q5km-ctx256k-agentic`
(Kwaipilot KAT-Coder-V2.5-Dev) ties it on every axis and is the equal alternative. qwen3.6 is not replaced.**

Earlier today KAT looked faster at better quality. [`review_20260925.md`](review_20260925.md) found why: the
reference sessions had run on an older Claude Code (2.1.274) than the candidates (2.1.282). Re-run
on **one client version**, ledger ×5 each, against a rule fixed before the runs (quality = median
18/18 and no run below 16; "clearly faster" = median ≥ 25% lower and non-overlapping ranges):

| model | session median (range) | held-out ×5 | quality | T5 gate ×8 | Terminal-Bench, 8 tasks × 3 |
|---|---|---|---|---|---|
| **qwen3.6 35B-A3B greedy** | **48 s** (46–49) | 18,18,18,17,17 | PASS | in the overnight round | **50% [31, 69]** |
| **KAT-Coder-V2.5-Dev** | **45 s** (37–58) | 18,18,17,18,17 | PASS | 8/8 | 38% [21, 57] |
| Tiel-Coder 35B-A3B | 79 s (51–126) | 18 ×5 | PASS | 6/8 | 42% [24, 61] |
| gemma4 26B-A4B | 90 s (69–100) | 18 ×5 | PASS | | 50% [31, 69] |
| qwen3.6 at vendor sampler (t 0.6) | 43 s | median 17 | fail | | 46% [28, 65] |
| ByteShape Qwen3.6 Q4_K_S (t 0.6) | 41 s | median 17 | fail | 8/8 | 58% [39, 76] |

- **qwen3.6 vs KAT is a tie**: both pass quality, speed is 6% apart, Terminal-Bench overlaps. The
  incumbent stays. The overnight extended Terminal-Bench round (≈38 tasks, qwen3.6 vs KAT) can still
  separate them on correctness.
- **Both are clearly faster than Tiel and gemma4.** Tiel also fails the nested-schema gate at 6/8.
- **Run qwen3.6 greedy, not at its vendor sampler**: t 0.6 drops held-out quality to a median of 17.
- **Use Tiel** when context-overflow safety matters most (it refuses with HTTP 400; qwen3.6 silently
  halves). **Use gemma4** for vision.
- Terminal-Bench counts 8 tasks since 09-25: polyglot-c-py contradicts its own tests and joins nginx as
  defective (the round document has the failure analysis).

Details: [`ROUND_2026-09-24.md`](ROUND_2026-09-24.md) · every model decided: [`CANDIDATE_REGISTER.md`](CANDIDATE_REGISTER.md) ·
dashboard: [`dashboard.html`](dashboard.html).

---

## The verdict as of 2026-09-21 (history)

*Revised 2026-09-21.* This round produced **two** cross-model capability results, from two
different harnesses, and **only one of them is valid**. That is the first thing to know before
quoting either.

**For daily Claude Code work, use `tiel-coder:35b-q5-ctx256k-agentic` — the variant, never the
tag as it shipped — and append `<|think_off|>`.**

That rests on the **ledger fixture**, which was run at **thinking parity**: every model reasoned,
verified per run from `think_chars` in [`results/cc-session.tsv`](results/cc-session.tsv), not
from the config. It is the only cross-model comparison in this round that survived review.

| | `north-mini` *(v3 default)* | `qwen3.6` *(control)* | **`tiel-coder` (pp 0)** |
|---|---|---|---|
| ledger fixture, **held-out tests**, n=3 | 18/18, **14/18**, 17/18 | 17/18, **15/18**, 16/18 | **18/18, 18/18, 18/18** |
| ledger fixture, median | 126 s | 60 s | **83 s** *(53 s with thinking off)* |
| generation @2k | **136.2** tok/s | 131.6 | 111.1 |
| deepest verified recall | 201,737 | — | **254,181** |
| resident @262,144 | **21.3 GB** | 32.68 GB | 34.13 GB |
| past its context window | **silently halves** | **silently halves** | **refuses (HTTP 400)** |
| vision | **no — none at all** | 40/42 | **42/42** |

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

### What is *not* settled — and why the Terminal-Bench numbers are not quoted as a ranking

The official Terminal-Bench round (120 trials, upstream harness, upstream dataset —
[`terminalbench/official/OFFICIAL_TB_PLAN.md`](terminalbench/official/OFFICIAL_TB_PLAN.md))
put `qwen3.6` first at 53% and Tiel third at 37%. **That comparison is void.** `<|think_off|>`
is a *Sharp-template* token: the adapter appended it to every model, so Tiel and CyberTiel ran
with **0 reasoning blocks across 30 trials each** while qwen3.6 (287 blocks), north-mini (373),
ornith (95) and gemma4 (83) reasoned normally. The subjects were handicapped and the
comparators were not.

Void is not disproven — qwen3.6 may still lead. It is simply **not evidence yet**, and the
re-run at parity is the next thing this project does (`plan.md` §8). Until it lands, **every
model-vs-model capability claim in this repo is provisional**, including the verdict above and
slot 1 of the standing field below.

What survives the defect, because none of it compares one model to another: the `nginx`
task defect, the `fibonacci-server` scaffold-persistence effect, the `oom` workaround-vs-root-
cause behaviour, and the n=1-vs-n=3 jitter measurements.

### The standing comparison field — four models, four axes

Fixed 2026-09-18; the authority is [`BENCHMARK_HARNESS.md`](BENCHMARK_HARNESS.md) §9a, and a new
contender is measured against these four and nothing else:

| # | tag | axis | status |
|---|---|---|---|
| 1 | `qwen3.6:35b-a3b-q4_K_M-agentic` | capability + reproducibility | **the default, confirmed 2026-09-25** on one client version (verdict above) |
| 2 | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | the speed ceiling (136.2 tok/s) | held on speed, which is measured and stable |
| 3 | `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` | the footprint floor (22.34 GB @262k) | settled |
| 4 | `tiel-coder:35b-q5-ctx256k-agentic` | context safety (the only family that refuses) | settled |

### CyberTiel: measured, and not recommended for daily use

### Three settings that matter more than the model choice

| | |
|---|---|
| **`presence_penalty 0`** | the shipped tag carries `1.5`, added by whoever created it — the raw download has none and the publisher recommends none. It costs **41–52% of generation** and nothing else changes |
| **`<|think_off|>`** | **2.3× faster** on the hard fixture with equal or better correctness. `MAX_THINKING_TOKENS=0` does *not* work — it only omits the field, which Ollama reads as "think" |
| **`CLAUDE_CODE_MAX_CONTEXT_TOKENS=230000`** | below the verified 254,181 retrieval ceiling, and Tiel's overflow is a visible error rather than a silent truncation |

### CyberTiel: measured, and not recommended for daily use

The abliterated sibling matches Tiel to within noise on **every** axis — generation within 1%,
recall one token apart (254,182 vs 254,181), identical memory, identical overflow behaviour,
both perfect on the (since-retired) v1 vision check, both 18/18 on the hard fixture. On eight benign defensive-security prompts
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
| `terminalbench/official/` | the upstream Terminal-Bench harness, its adapter, the frozen subset and the run transcripts |
