# Shell aliases after v3

What changes in `~/.zshrc` as a result of the 2026-08-25 measurements, and why. The v2
document ([`../ollamaClaudeCode_v2/shell_aliases.md`](../ollamaClaudeCode_v2/shell_aliases.md))
still explains every environment variable in detail; this records only the delta.

**Status: `claude-ol-north` is wired into `~/.zshrc`** as of 2026-08-25, immediately after
`claude-ol-nemo`, which is left in place rather than removed — deleting a colleague-visible
alias is not this project's call. `claude-ol2` needed no change: it already points at
`qwen3.6:35b-a3b-q4_K_M-agentic`, which v3 re-measured and re-confirmed as the default.

## The delta

| command | before (v2) | after (v3) |
|---|---|---|
| `claude-ol2` — default | `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 | **unchanged** |
| `claude-ol-nemo` — deep context | `nemotron-3.5-lightning:30b-ctx256k-agentic` | **replaced** by `claude-ol-north` |

**`claude-ol2` does not change.** Nothing in the 2026-08 field beat it: it is the fastest
generator measured (130.0 tok/s), clean on 10/10 gates, retrieves deepest (146,957 tokens),
and it is one of only two candidates with vision.

## The one change: `claude-ol-north` replaces `claude-ol-nemo`

```shell
claude-ol-north() {
  local H=http://192.168.100.67:11434
  local M=north-mini-code-1.0:q4_K_M-ctx256k-agentic
  # pre-warm with keep_alive 2h, then:
  ANTHROPIC_AUTH_TOKEN=ollama \
  ANTHROPIC_BASE_URL="$H" \
  ANTHROPIC_API_KEY="" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 \
    claude --model "$M" "$@"
}
```

Same four decisions as `claude-ol-nemo`, for the same measured reasons — a function rather
than an alias because of the cold load, the Haiku model pointed at the same tag so a
background call cannot evict it, `CLAUDE_CODE_MAX_CONTEXT_TOKENS` below the baked window
because overflowing `num_ctx` silently halves it and stops tool calling, and never a bare tag.

Why it replaces Nemotron, measured side by side on the same box:

| | `nemotron-3.5-lightning` (v2) | `north-mini-code-1.0` (v3) |
|---|---|---|
| generation | 44.9 tok/s | **83.6 tok/s** — 1.9× |
| resident @262144 | 31.21 GB | **21.34 GB** — 8 GB lighter |
| tool gates | 10/10 | 10/10 |
| tokeniser | +38% vs incumbent (worse) | **−21% (better)** |
| failure mode at depth | **invents a passphrase** | reports "not found" |

That last row is not a tiebreaker, it is the point. v2 recorded Nemotron confabulating a
plausible passphrase on a truncated prompt, with no error and no signal — "the worst failure
mode on this box". North-mini says it cannot find the thing.

## Why `-ctx256k` and not `-ctx500k`

The 500,000-token variant allocated that window at 100% GPU in 23.29 GB — and did not
retrieve across it. Measured: reliable to **201,737 tokens**, then a failure at 230,825 that
reproduced **5 times out of 5** across two baked windows, three request windows, three
generation budgets and both thinking modes, while 347,193 — deeper — passed 3/3
(`measurements.md` §8). Unexplained, and enough to disqualify the window.

**`CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000` therefore sits below a *measured* retrieval ceiling,
not merely below the allocation ceiling.** That is the useful property: a window that holds
your context but cannot answer from it is worse than a smaller one, because nothing in the
transcript tells you which regime you are in.

The `-ctx500k` variant has since been deleted from `.67`; re-create it with one `/api/create`
call if you want to probe further.

## When to use which

- **`claude-ol2`** — everything, by default. 130.0 tok/s, 262144, vision, retrieves at 146,957.
- **`claude-ol-north`** — when the working set is large *and* tool-heavy. Slower to generate
  (83.6) but faster to prefill (4,331 vs 3,911), 11 GB lighter, and its tokeniser fits ~21%
  more source into the same window. **No vision.**
- **`gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic`** — no alias, but worth knowing: the fastest
  prefill on the box (5,740 tok/s, +44%) with vision and 10/10 gates, at the cost of 47%
  slower generation. Reach for it on read-heavy, edit-light work.
- **`laguna-xs-2.1`** — no alias, deliberately, and **deleted from `.67`**. Fastest challenger
  (119.5 tok/s) and the only model that failed a gate: it serialises parallel tool calls and
  dropped one call in three at 53k tokens. Re-pullable in ~10 minutes if a new version ships.
