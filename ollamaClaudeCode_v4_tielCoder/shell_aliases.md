# Shell aliases after v4

What changes in `~/.zshrc` as a result of the v4 measurements, and why. v2's document
([`../ollamaClaudeCode_v2/shell_aliases.md`](../ollamaClaudeCode_v2/shell_aliases.md)) still
explains every environment variable in detail and v3's records the four-model-slot fix; this
records only the delta.

> **Nothing here is installed automatically.** v3 wrote its aliases into `~/.zshrc`; v4 leaves
> that to you, because `claude-ol2` and friends are your shell and the change below is a
> recommendation, not a repair.

## The delta

| command | before (after v3) | after v4 |
|---|---|---|
| `claude-ol-north` — default | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | **superseded** — keep it, stop reaching for it first |
| *(new 09-25)* **`claude-ol-byte`** | — | **added to ~/.zshrc**: `byteshape-qwen3.6-35b:q4ks-ctx256k-agentic`, the fastest and top-scoring (see *Alias review*) |
| *(new 09-25)* **`claude-ol-kat`** | — | **the equal alternative** to qwen3.6 (README verdict 2026-09-25, same-version re-baseline): `kat-coder-v2.5:q5km-ctx256k-agentic` @ 262144 |
| *(new)* `claude-ol-tiel` | — | the 09-21 default, now the pick **when overflow safety matters**: `tiel-coder:35b-q5-ctx256k-agentic` @ 262144 |
| *(new)* `claude-ol-tiel-fast` | — | the same tag with `<\|think_off\|>` appended — **2.3× faster**, see below |
| `claude-ol-ornith` | Ornith-1.0, deep documents | **keep**. It was the fastest finisher on 09-17 (47 s). KAT (46 s) and ByteShape (35 s) are faster on 09-25, on a newer client |
| `claude-ol2`, `claude-ol-nemo`, `claude-ol-vision` | unchanged | unchanged |

## Why the default moved to Tiel on 09-17 (history: superseded by `claude-ol-kat`, provisionally, on 09-25)

Measured on 0.33.3, same harness, server idle before each, n=3 for the sessions:

| | `north-mini` *(v3 default)* | **`tiel-coder` (pp 0)** |
|---|---|---|
| generation @2k | **136.2** tok/s | 111.1 |
| cold prefill @35k | **4,592** tok/s | 3,483 |
| agent-turn cost (cached) | 1.08 s | **0.81 s** |
| resident @262144 | **21.3 GB** | 34.13 GB |
| deepest verified recall | 201,737 | **254,181** |
| hard fixture, held-out tests | 18/18, **14/18**, 17/18 | **18/18, 18/18, 18/18** |
| hard fixture, median | 126 s | **83 s** |
| past its context window | **silently halves** | **refuses (HTTP 400)** |
| vision | no | **yes** |

North-mini is faster per token and much lighter. It is not the model that fixed the code: on a
three-module bug with 18 held-out tests it left up to four of them failing, while turning the
visible tests green. Tiel passed all eighteen, three times from three.

**The two properties that decide it are not speed.** First, Tiel solves the specification rather
than the test file. Second, when a prompt overruns the window Tiel returns an error, where
north-mini silently keeps half the context and answers anyway — and Claude Code has no way to
send `num_ctx`, so nothing in the transcript would tell you it happened.

The cost is memory: 34.13 GB of a 35.56 GB box. **Nothing else can be resident beside it**, so
a background call to any other tag evicts it and pays a ~15 s reload.

## Never the tag as it shipped

`Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest` carries **`presence_penalty 1.5`**, added by
whoever created the tag on 2026-09-14 — the raw download has no parameters, and the publisher's
card recommends no penalty at all. It costs **41–52% of generation** (73.2 vs 111.1 tok/s at a
2,000-word prompt) and changes nothing else: prefill is flat within 2%, and tool reliability is
statistically identical (T5 re-runs, 13/16 with it against 15/16 without).

```shell
# the variant, once — shares the weight blob, so it costs zero disk
curl -s http://192.168.100.67:11434/api/create -d '{
  "model": "tiel-coder:35b-q5-ctx256k-agentic",
  "from":  "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest",
  "parameters": {"presence_penalty": 0},
  "stream": false}'
```

## Alias review, 2026-09-25: every `claude-ol*` in `~/.zshrc`

**Result, applied:** `~/.zshrc` now holds exactly four local launchers: **`claude-ol-qwen`** (default),
**`claude-ol-kat`** (equal alternative), **`claude-ol-byte`** (fastest, top score) and **`claude-ol-tiel`**
(overflow safety, vision). `claude-nvidia`, `claude-dmo` and `claude-vision` are unaffected.

Checked against the live servers (the tag must exist where the alias points) and this round's
measurements. The same-version re-baseline decides the ranking.

| alias | backend and tag | configured correctly? | problems found | recommendation |
|---|---|---|---|---|
| **`claude-ol-qwen`** (was `claude-ol2`) | .67 `qwen3.6:35b-a3b-q4_K_M-agentic` (greedy) | **yes**: pre-warm, all four slots, 200k cap, reminder off | only its comment is stale ("dual-GPU", figures from 08-06) | **KEEP: the default** (48 s, 18,18,18,17,17, TB 50%, T5 8/8) |
| **`claude-ol-byte`** *(new)* | .67 `byteshape-qwen3.6-35b:q4ks-ctx256k-agentic` | **yes**, same pattern as claude-ol2 | trade-off: held-out median 17 | **KEEP: fastest and top score** (41 s, TB 58%, 4 GB less VRAM) |
| **`claude-ol-kat`** *(added)* | .67 `kat-coder-v2.5:q5km-ctx256k-agentic` | **yes**, the claude-ol-qwen pattern, tag verified | | **KEEP**: the equal alternative (45 s, 18,18,17,18,17, T5 8/8). The recipe is in the next section |
| `claude-ol-tiel` | .67 `tiel-coder:35b-q5-ctx256k-agentic` | **yes** | the cap could be 230k (it refuses rather than halving). T5 6/8 | **KEEP for overflow safety** (the only model that errors instead of truncating) and vision |
| ~~`claude-ol-north`~~ | .67 `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | yes | its comment still says **"THE DEFAULT since 2026-08-27"**. 126 s sessions, held-out 14–18, TB 38%, no vision, silently halves | **REMOVED** 2026-09-25 |
| ~~`claude-ol-ornith`~~ | .67 `ornith:35b-ctx256k-agentic` (Ornith 1.0) | mostly | its cap of **220k** sits just under where the overflow probe saw it truncate (224,357 evaluated of ~275k sent). Held-out 16–18. Its successor 1.5 fails T5 | **REMOVED** 2026-09-25 |
| ~~`claude-ol-nemo`~~ | .67 `nemotron-3.5-lightning:30b-ctx256k-agentic` | **no** | its purpose is "the deep-context option", but it points at the **256k** tag, not the 512k one. Held-out 13–14/18, 44.9 tok/s | **REMOVED** 2026-09-25 |
| ~~`claude-ol`~~ | .37 `qwen3.5:9b-ctx80k` | **no** | **no `CLAUDE_CODE_MAX_CONTEXT_TOKENS`**: Claude Code assumes 200k against an 80k window and silently truncates. A 9B model is far below the field | **REMOVED** 2026-09-25 |
| ~~`claude-ol-mistral`~~ | .37 `mistral-nemo:12b-ctx20k` | **no** | a **20k** window cannot even hold Claude Code's system prompt plus tool schemas. No cap | **REMOVED** 2026-09-25 |
| ~~`claude-ol-local`~~ | localhost `qwen3.5:4b-ctx32k` | **broken** | **tag does not exist** on localhost (only `qwen3.5:4b`) | **REMOVED** 2026-09-25 |
| ~~`claude-locallama`~~ | localhost `qwen3.5:4b-ctx54k` | **broken** | **tag does not exist** on localhost. Outside the `claude-ol*` naming | **REMOVED** 2026-09-25 |
| `claude-ol-vision` | — | **does not exist** | referenced by claude-ol-north's comment only. Vision lives in `claude-vision` (the OCR shell) and in claude-ol-tiel (42/42) | remove the dangling reference |
| `claude-nvidia` | NVIDIA NIM via local proxy, qwen3-coder-480b | out of scope (cloud, not local) | sets no context cap | keep, unaffected |

**All `.67` functions share correct slot handling:** all four model slots on the resident tag, so no
eviction, pre-warm with `keep_alive 2h`, and `CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off`. That last one showed
no measurable effect on short sessions (R1), but it is the documented workaround for long ones
(ollama#18431). Keep it.

**Plan and state** (backups: `~/.zshrc.bak-byteshape-*`, `~/.zshrc.bak-aliasplan-*`):
1. ~~add `claude-ol-byte`~~ **done** 2026-09-25
2. ~~add `claude-ol-kat`~~ **done** 2026-09-25
3. ~~remove the broken `claude-ol-local`, `claude-locallama`~~ **done** 2026-09-25
4. ~~rename `claude-ol2` → `claude-ol-qwen`, header refreshed to the 09-25 figures~~ **done** 2026-09-25.
   Every reference in `~/.zshrc` renamed with it
5. ~~remove `claude-ol`, `claude-ol-mistral`, `claude-ol-nemo`, `claude-ol-north`, `claude-ol-ornith`~~
   **done** 2026-09-25 (backup `~/.zshrc.bak-abandon-*`), and with them the dangling `claude-ol-vision`
   reference (it lived in claude-ol-north's comment)
6. optional: raise `claude-ol-tiel`'s cap to 230000
7. ~~on `.67`, delete the tags only the removed aliases used~~ **done** 2026-09-25, on the owner's instruction
   ("keep qwen3.6 and ornith, used by another workflow"). Deleted: `nemotron-3.5-lightning:30b`,
   `:30b-ctx256k-agentic`, `:30b-ctx512k-agentic`, `north-mini-code-1.0:q4_K_M-ctx256k-agentic`. All
   `qwen3.6:*` and `ornith*` tags kept. Measured with `/api/tags` + `/api/show` (blobs deduplicated by their
   `FROM` digests):

   | | tags | sum of tag sizes | unique weights on disk |
   |---|---|---|---|
   | before | 29 | 615.66 GiB | 250.25 GiB (12 distinct) |
   | after | 25 | 527.29 GiB | **209.25 GiB** (10 distinct) |
   | **freed** | 4 | 88.37 GiB | **41.00 GiB** |

   Note: `north-mini-code-1.0` was one of the four standing-field comparators (BENCHMARK_HARNESS §9a).
   Its measurements stay in `results/`, but a future parity run must re-pull it or drop it from the field.

## `claude-ol-byte` (added 2026-09-25)

In `~/.zshrc`, identical in shape to `claude-ol2`. The tag carries everything: ByteShape Q4_K_S 4.22 bpw,
num_ctx 262144, presence_penalty 0, t 0.6 / top_p 0.95 / top_k 20 / min_p 0, and `RENDERER/PARSER qwen3.5`,
verified with `/api/show`. The client side sets `CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000`, because Qwen3.6 builds
silently halve past num_ctx.

## `claude-ol-kat` (ties the qwen3.6 default, 2026-09-25)

The tag, as the candidate screen baked it. The vendor sampler is t 1.0 / top_p 0.95, and Ollama's
own qwen3.5 renderer is set because the GGUF's Jinja template rejects Claude Code's
mid-conversation system messages (ROUND_2026-09-24.md, `2cb75e0`):

```shell
curl -s http://192.168.100.67:11434/api/create -d '{
  "model": "kat-coder-v2.5:q5km-ctx256k-agentic",
  "from":  "hf.co/bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF:Q5_K_M",
  "parameters": {"num_ctx": 262144, "presence_penalty": 0, "temperature": 1.0, "top_p": 0.95},
  "renderer": "qwen3.5", "parser": "qwen3.5",
  "stream": false}'
```

```shell
claude-ol-kat() {
  local H=http://192.168.100.67:11434
  local M=kat-coder-v2.5:q5km-ctx256k-agentic
  printf 'claude-ol-kat: warming %s ...' "${H#http://}" >&2
  if curl -sf --max-time 900 "$H/api/generate" -H 'Content-Type: application/json' \
       -d "{\"model\":\"$M\",\"prompt\":\"hi\",\"keep_alive\":\"2h\",\"stream\":false}" >/dev/null 2>&1
  then printf ' resident (2h)\n' >&2
  else printf ' FAILED\n' >&2
       echo "  - the servers are reachable only via the USB ethernet adapter, not wifi" >&2
       return 1
  fi
  ANTHROPIC_AUTH_TOKEN=ollama \
  ANTHROPIC_BASE_URL="$H" \
  ANTHROPIC_API_KEY="" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
  ANTHROPIC_DEFAULT_SONNET_MODEL="$M" \
  ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 \
    claude --model "$M" "$@"
}
```

**200,000, not Tiel's 230,000.** KAT's overflow behaviour has not been probed. It is a Qwen3.6
derivative, and Qwen3.6 **silently halves** an over-long prompt, so the cap keeps a wide margin under
the baked 262,144 until `overflow-probe.py` has been run on it. Everything else is as for Tiel below.

## `claude-ol-tiel`

```shell
claude-ol-tiel() {
  local H=http://192.168.100.67:11434
  local M=tiel-coder:35b-q5-ctx256k-agentic
  printf 'claude-ol-tiel: warming %s ...' "${H#http://}" >&2
  if curl -sf --max-time 900 "$H/api/generate" -H 'Content-Type: application/json' \
       -d "{\"model\":\"$M\",\"prompt\":\"hi\",\"keep_alive\":\"2h\",\"stream\":false}" >/dev/null 2>&1
  then printf ' resident (2h)\n' >&2
  else printf ' FAILED\n' >&2
       echo "  - the servers are reachable only via the USB ethernet adapter, not wifi" >&2
       echo "  - check: ip -br addr show enp0s13f0u1u4 && curl -s $H/api/version" >&2
       return 1
  fi
  ANTHROPIC_AUTH_TOKEN=ollama \
  ANTHROPIC_BASE_URL="$H" \
  ANTHROPIC_API_KEY="" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
  ANTHROPIC_DEFAULT_SONNET_MODEL="$M" \
  ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=230000 \
    claude --model "$M" "$@"
}
```

Four decisions, each measured rather than assumed — the first three are v2/v3's and unchanged:

1. **A function, not an alias**, because a 34 GB cold load otherwise stalls the first prompt
   silently. `keep_alive 2h` holds it.
2. **All four model slots on the same tag.** Subagents resolve the `opus` alias; unset, Claude
   Code sends the literal `claude-opus-5` to Ollama and gets HTTP 404. A slot pointing at a
   *different* local tag is worse: on a 35.56 GB box it evicts the resident model.
3. **`CLAUDE_CODE_MAX_CONTEXT_TOKENS` below the baked window.** Claude Code does not recognise
   the tag and would otherwise assume 200,000.
4. **230,000 rather than 200,000, and this one is specific to Tiel.** Retrieval is verified to
   **254,181 tokens**, and — unlike every other model on the box — overrunning the window
   returns HTTP 400 rather than silently discarding half of it. Both limits are therefore
   *visible*, so the cap can sit closer to them. 230,000 leaves ~32k of generation headroom
   under the baked 262,144.

## `claude-ol-tiel-fast` — the 2.3× switch

The largest operational finding of v4. Claude Code always asks for thinking
(`thinking:{type:"adaptive"}`) and never sends `disabled`, and `MAX_THINKING_TOKENS=0` only
*omits* the field — which Ollama reads as "think". The Sharp template built into Tiel takes a
`<|think_off|>` marker in the system prompt instead, and Claude Code can inject one:

```shell
claude-ol-tiel-fast() { claude-ol-tiel --append-system-prompt '<|think_off|>' "$@" }
```

| | thinking on | thinking off |
|---|---|---|
| hard fixture, 3 runs | 131 / 148 / 117 s | **74 / 53 / 56 s** |
| held-out tests | 18/18, **16/18**, 17/18 | **18/18, 18/18**, 17/18 |
| thinking characters | 15,650–24,994 | **0** |

**Equal or better correctness, in under half the time**, and the only session Tiel failed all
day was a thinking-on run. It transfers to CyberTiel (57 s → 37 s, both 18/18), because it is a
property of the shared Sharp template rather than of the weights.

Use the plain `claude-ol-tiel` when you want the model to reason at length about a design; use
`-fast` for ordinary tool-driven work, which is most of it.

## CyberTiel gets no alias, deliberately

`cyber-tiel:35b-q5-ctx256k-agentic` is on the box and is **not** wired into the shell.

It measures the same as Tiel on every axis — generation within 1%, recall one token apart,
identical memory and overflow behaviour, both 25/25 on vision — and on eight benign
defensive-security prompts **neither model refused anything**. So the uncensored build buys
nothing on legitimate work.

It is abliterated: its refusal behaviour has been removed, and its publisher's instruction is to
sandbox it at the OS level. v4 ran it only inside a container with no host mounts, a read-only
rootfs, dropped capabilities and an egress allowlist of exactly one address
(`cc-session-sandboxed.sh`). **An alias would invite running it against your real home
directory with `--permission-mode bypassPermissions`, which is precisely what not to do.** If
you need it, run it through that harness.

## What did not change

- `claude-ol-ornith` stays, and v4 improves its standing: on 0.33.3 it finished the hard fixture
  fastest of anything measured **on 09-17** (47 s median). KAT (46 s) and ByteShape (35 s) are faster
  on 09-25, on a newer Claude Code. v3's 308 s figure was measured before the
  runtime cached prompt prefixes; that penalty is gone.
- `claude-ol-nemo` stays for the 524,288-token window, the only thing that needs it.
- `claude-ol-vision` stays. gemma4 is still an excellent vision model — and Tiel now also reads
  images at the full 262,144 window, so the vision-only detour is often unnecessary.
- **The `num_ctx` rule is unchanged and still load-bearing**: never point Claude Code at a bare
  tag. Without a baked window `/v1/messages` caps at 16,384 tokens and tool calling stops with
  no error.
