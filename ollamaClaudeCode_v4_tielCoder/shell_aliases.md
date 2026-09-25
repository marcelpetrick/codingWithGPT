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
| *(new 09-25)* **`claude-ol-kat`** | — | **the new default, provisional** (README verdict 2026-09-25): `kat-coder-v2.5:q5km-ctx256k-agentic` @ 262144 |
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

## `claude-ol-kat` (the default since 2026-09-25)

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
