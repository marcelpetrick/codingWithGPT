# Shell aliases after v3

What changes in `~/.zshrc` as a result of the v3 measurements, and why. The v2 document
([`../ollamaClaudeCode_v2/shell_aliases.md`](../ollamaClaudeCode_v2/shell_aliases.md)) still
explains every environment variable in detail; this records only the delta.

> **Revised 2026-08-27.** The 2026-08-25 version of this file said "`claude-ol2` needed no
> change: it already points at `qwen3.6:35b-a3b-q4_K_M-agentic`, which v3 re-measured and
> re-confirmed as the default." **That is no longer true.** `.67` was upgraded from Ollama
> 0.32.9 to 0.32.15, which changed generation throughput by 0% to +221% depending on the
> model and re-ranked the field without any model changing (`measurements.md` §13). The
> default moves.

## The delta

| command | before | after (2026-08-27) |
|---|---|---|
| `claude-ol2` — default | `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 | **repoint** to `north-mini-code-1.0:q4_K_M-ctx256k-agentic` @ 262144 |
| `claude-ol-north` | added 2026-08-25 as the *deep-context* alias | **now the default**; keep the name |
| `claude-ol-nemo` — deep context | `nemotron-3.5-lightning:30b-ctx256k-agentic` | **keep**, for the 524,288 window only |
| *(new)* `claude-ol-vision` | — | `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` @ 262144 |

**The least disruptive way to apply this: leave `claude-ol-north` exactly as it is and
repoint `claude-ol2` at the same tag.** `claude-ol-north` was already wired into `~/.zshrc`
on 2026-08-25 and is already correct — the only edit needed is the model string inside
`claude-ol2`.

## Why the default moves

Measured side by side on 0.32.15, same harness, same box, server idle before each:

| | `qwen3.6:35b-a3b` *(incumbent)* | `north-mini-code-1.0` |
|---|---|---|
| generation @2k | 130.0 tok/s | **132.9** |
| prefill @35k | 3,996 tok/s | **4,443** |
| resident @262144 | 32.54 GB | **21.34 GB** |
| deepest verified retrieval | 146,957 | **201,737** |
| tool gates T1–T7 | 10/10 | 10/10 |
| Claude Code session | 58 s | 57 s |
| tokeniser | baseline | **−21%** (fits ~21% more source in the same window) |
| vision | **yes** | no |

North-mini wins every axis except vision, and the one that matters operationally is the
**11.2 GB**: on a 35.56 GB box that is the difference between one resident model and one
resident model with room left over.

The incumbent did not get worse — it measured 130.04 tok/s on both runtimes, to two decimals.
Everything around it got faster.

## The one thing to know before switching: no vision

`claude-ol2` has had vision since v2. `north-mini-code-1.0` does not have it. If you paste
screenshots into Claude Code, that workflow breaks silently — the model will not error, it
will just not see the image.

That is what `claude-ol-vision` is for, and on 0.32.15 gemma4 is a better vision model for
this job than the incumbent was:

| | `qwen3.6:35b-a3b` | `gemma4:26b-a4b-it` |
|---|---|---|
| **prefill @35k** | 3,996 tok/s | **5,774** — fastest on the box |
| generation @2k | **130.0** | 104.1 |
| resident @262144 | 32.54 GB | **22.15 GB** |
| Claude Code session | 58 s | **54 s** — fastest measured |
| vision | yes | yes |

It loses 20% of generation and wins 44% of prefill — and prefill is what an agentic loop pays
on every turn, while generation only covers the few dozen tokens a tool-heavy turn emits. It
also finished the end-to-end fixture fastest of anything measured.

```shell
claude-ol-vision() {
  local H=http://192.168.100.67:11434
  local M=gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic
  # pre-warm with keep_alive 2h, then:
  ANTHROPIC_AUTH_TOKEN=ollama \
  ANTHROPIC_BASE_URL="$H" \
  ANTHROPIC_API_KEY="" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 \
    claude --model "$M" "$@"
}
```

Same four decisions as the other functions, for the same measured reasons: a function rather
than an alias because of the cold load, the Haiku model pointed at the same tag so a
background call cannot evict it, `CLAUDE_CODE_MAX_CONTEXT_TOKENS` **below** the baked window
because overflowing `num_ctx` silently halves it and stops tool calling, and never a bare tag.

## `claude-ol-nemo` stays, for one reason

Nemotron is now the **fastest generator on the box** — 138.1 tok/s, up from 43.9, a +221%
jump from the runtime upgrade alone. It is still not the default, for two measured reasons:
the **worst prefill of the four** (2,797 vs north-mini's 4,443), and it took **34 turns** to
do a job the others did in 16–19, finishing in 72 s against their 54–58.

Keep it for the one thing nothing else does: **524,288 tokens**, the only model on the box
that holds a half-million-token window.

And keep v2's warning attached to it. At depth on a truncated prompt Nemotron **invents a
plausible passphrase** rather than reporting it cannot find one — no error, no signal. That
is the worst failure mode measured on this box, and it is why it lost the deep-context
default to north-mini in the first place.

## Why `-ctx256k` and not `-ctx500k`

Unchanged from 2026-08-25, and re-confirmed: the 500,000-token variant allocated that window
at 100% GPU in 23.29 GB — and did not retrieve across it. Reliable to **201,737 tokens**,
then a failure at 230,825 reproducing **5 of 5** across two baked windows, three request
windows, three generation budgets and both thinking modes, while 347,193 — deeper — passed
3/3 (`measurements.md` §8).

**`CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000` therefore sits below a *measured* retrieval
ceiling, not merely below the allocation ceiling.** A window that holds your context but
cannot answer from it is worse than a smaller one, because nothing in the transcript tells
you which regime you are in.

## No alias for Qwen3.8, deliberately

Stage A measured all three rungs (`measurements.md` §12–21). `qwen3.8:27b-q4_K_M` at
`num_ctx 131072` is capable — 9/10 gates, vision, the best window-utilisation ratio in the
field at 90.8% — and **4.3× slower than the default**, finishing the end-to-end fixture in
111 s against 54–58 s.

If you do want it for a specific piece of work, the tag matters:

> **`qwen3.8:27b-q4_K_M`, never `qwen3.8:27b`.** The bare tag's params digest is
> byte-identical to the MTP build, so the obvious name silently enables speculative decoding:
> +20% generation for **−46% prefill**, which is the wrong trade for an agentic loop.

And bake a window first, as always — `qwen3.8` ships without `num_ctx`, so the bare tag caps
at 16,386 tokens and **stops calling tools entirely**, with no error. Confirmed still true on
0.32.15 (§17).

## The functions, as installed

| function | model | max context | why that cap |
|---|---|---|---|
| `claude-ol2` | `qwen3.6:35b-a3b-q4_K_M-agentic` | 200,000 | below the baked 262144 |
| `claude-ol-north` | `north-mini-code-1.0:q4_K_M-ctx256k-agentic` | 200,000 | below the baked 262144 **and** below the measured 201,737 retrieval ceiling |
| **`claude-ol-ornith`** | `ornith:35b-ctx256k-agentic` | **220,000** | below the baked 262144 **and** below the measured **254,061** ceiling — 20k more usable context than north-mini, which is the entire reason this alias exists |
| `claude-ol-nemo` | `nemotron-3.5-lightning:30b-ctx256k-agentic` | 200,000 | below the baked 262144 |

`claude-ol-ornith` is the only one that departs from 200,000, and it does so on measured
grounds rather than optimism: ornith is the only model whose retrieval was *verified* past
250k (§31), so it is the only one where a higher cap is defensible. 220,000 still leaves
~42k of generation headroom under the baked window, well clear of the truncation cliff.

## `claude-ol-ornith` — and the caveat that ships with it

Its comment block in `~/.zshrc` carries the warning in full, because this is the one alias
that can disappoint:

**One real session took 308 s against north-mini's 57 s** — the slowest measured in the
project. It was *not* thrashing: 15 turns, a clean `Bashx3,Readx3,Editx1` transcript, fewer
turns than north-mini needed. It did the right things and took five times as long.

**The suspected cause is unverified and the alias says so.** Ornith is a thinking model; the
128.5 tok/s figure was measured with `think:false`, while a real session does not disable
thinking. ~20.5 s/turn at 128 tok/s implies ~2,600 tokens emitted per turn — the right order
for heavy reasoning output. The measurement that would settle it was abandoned when a
colleague's session took the box. **If it feels slow, lower the reasoning effort before
blaming the model.**

So: reach for it when the working set is genuinely 200k+ and you need recall you can trust.
Do not make it the default.

## The subagent bug — every alias had it (fixed 2026-08-27)

Symptom, seen on a real `claude-ol-north` session: the main model works, but **every
subagent dies instantly.**

```
Agent "Explore game frameworks and patterns" failed: Agent terminated early due to an
API error: There's an issue with the selected model (claude-opus-5[1m]) ...
(error type model_not_found, HTTP 404, model sent to the API: claude-opus-5)
```

**Cause.** Claude Code resolves models through *four* slots, not one. `--model` sets the main
loop. The other three are aliases a subagent or a background task resolves through:

| variable | what resolves through it |
|---|---|
| `ANTHROPIC_MODEL` / `--model` | the main conversation |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | the `haiku` alias + background work (session titles, summaries) |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | the `sonnet` alias, and `opusplan` outside Plan Mode |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | the `opus` alias, and `opusplan` inside Plan Mode |

The Explore/Task subagents resolve the **`opus`** alias. With `ANTHROPIC_DEFAULT_OPUS_MODEL`
unset it falls through to the literal `claude-opus-5`, which Claude Code faithfully sends to
`.67` — a server that has never heard of it. Hence HTTP 404.

Note the documentation says `ANTHROPIC_DEFAULT_HAIKU_MODEL` is "also used for background
functionality", which is true and was the reason only that one was set. It is not sufficient:
**background work and subagents are different things**, and subagents go through `opus`.

**Every alias in `~/.zshrc` was affected**, in two severities:

| alias | before | failure |
|---|---|---|
| `claude-ol2`, `claude-ol-nemo`, `claude-ol-north`, `claude-ol-ornith` | HAIKU only | subagents 404 |
| `claude-ol`, `claude-ol-mistral`, `claude-ol-local`, `claude-locallama`, `claude-nvidia` | nothing set | subagents **and** background calls 404 |

**Fix: all four slots point at the same local tag**, for the same reason the Haiku slot always
did — this box holds one model at a time, so any slot resolving to a *different* tag either
404s (if the server lacks it) or evicts the resident model and costs a ~70 s reload.

```shell
ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
ANTHROPIC_DEFAULT_SONNET_MODEL="$M" \
ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \
  claude --model "$M" "$@"
```

Verified after the fix by running a real Explore subagent through `claude-ol-north`: it
completed and returned the right answer, with no `model_not_found`.

**One harmless message remains** and is not this bug:
`[claude-code:unrecognized_model] {"query_source":"generate_session_title"}` — Claude Code
does not recognise the custom tag name for its own session-title feature. It is cosmetic; the
title generation just falls back.

## When to use which

- **`claude-ol-north`** — everything, by default. 132.9 tok/s, 262144, 10/10 gates, retrieves
  to 201,737, 21.34 GB. **No vision.** (`claude-ol2` still points at the old default; repoint
  it or just use this name.)
- **`claude-ol-ornith`** — genuinely long documents. Deepest verified recall on the box
  (254,061) and 10/10 gates, at 220,000 usable context — but see the 308 s caveat above.
- **`claude-ol-vision`** — screenshots, and read-heavy/edit-light work generally. Fastest
  prefill and fastest session on the box.
- **`claude-ol-nemo`** — only when you genuinely need more than 262,144 tokens. Watch for
  confabulation at depth.
- **`laguna-xs-2.1`** — no alias, deliberately, and deleted from `.67`. The only model that
  failed a gate: it serialises parallel tool calls and dropped one call in three at 53k
  tokens. Its 119.5 tok/s is a 0.32.9 number and was never re-measured.
