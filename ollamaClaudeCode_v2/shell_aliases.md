# Shell aliases for the local Ollama servers

What is wired into `~/.zshrc`, why each one is a **function** rather than a plain alias,
and the measured reasons behind every environment variable. Measurements live in
[`muse_ollama.md`](muse_ollama.md) (§7c, §11) and `../ollamaClaudeCode_v1/review2.md`.

## The aliases

| command | server | model | window | speed |
|---|---|---|---|---|
| `claude-ol2` | `.67` | `qwen3.6:35b-a3b-q4_K_M-agentic` | 262144 | **131.4 tok/s** |
| **`claude-ol-nemo`** | `.67` | `nemotron-3.5-lightning:30b-ctx256k-agentic` | 262144 | 44.9 tok/s |
| `claude-ol` | `.37` | `qwen3.5:9b-ctx80k` | 81920 | — |
| `claude-ol-mistral` | `.37` | `mistral-nemo:12b-ctx20k` | 20k | — |
| `claude-ol-local` | laptop | `qwen3.5:4b-ctx32k` | 32k | — |
| `claude-locallama` | laptop | `qwen3.5:4b-ctx54k` | 54k | — |

**Use `claude-ol2` by default.** `claude-ol-nemo` is the deep-context option and is
**2.9× slower**; reach for it only when the working set genuinely exceeds 262144 tokens.

## `claude-ol-nemo` — what it does and why

```shell
claude-ol-nemo() {
  local H=http://192.168.100.67:11434
  local M=nemotron-3.5-lightning:30b-ctx256k-agentic
  # pre-warm with keep_alive 2h, then:
  ANTHROPIC_AUTH_TOKEN=ollama \
  ANTHROPIC_BASE_URL="$H" \
  ANTHROPIC_API_KEY="" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 \
    claude --model "$M" "$@"
}
```

Four decisions, each forced by something that was measured rather than assumed:

**1. A function, not an alias — because of the cold load.** The model is 31.21 GB and
Ollama's `keep_alive` defaults to about five minutes. Without pre-warming, the first
prompt of a session blocks on an 18-second load with no feedback, and any pause longer
than the keep-alive pays it again. The function warms the model with `keep_alive: 2h`
and prints whether it succeeded, so a network failure is visible immediately instead of
surfacing as a mysteriously slow first turn.

**2. `ANTHROPIC_DEFAULT_HAIKU_MODEL` points at the same model, deliberately.** Claude
Code issues background calls against a Haiku tag that `.67` does not have. Worse, the
usable VRAM ceiling is ≈35.5 GB (`muse_ollama.md` §11.4) and this model alone holds
31.21 GB, so **any** second model evicts it — v1 measured exactly this: one call to
`qwen3.5:9b-ctx80k` unloaded the MoE and the next real turn paid a 70-second reload.
Background calls are cheap; a 70-second stall per call is not.

**3. `CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000`, below the baked 262144.** Claude Code does
not recognise this model tag and would otherwise assume a 200k window by default. The
number matters because the prompt *plus everything Claude Code generates* must stay
under `num_ctx`: overflowing it does not error, it **silently discards down to
`num_ctx/2` and stops tool calling** (§4, re-measured on 0.32.9 — still unfixed).
200000 leaves ~62k of generation headroom clear of that cliff.

**4. Never a bare model tag.** Without `num_ctx` baked into the variant, `/v1/messages`
caps the context at 16,384 tokens and tool calling silently stops past it. Every alias
here points at a variant with a baked window.

## When to use which

- **`claude-ol2`** — everything, by default. 131.4 tok/s, full 262144 window, reads
  screenshots, retrieves at 146,957 tokens.
- **`claude-ol-nemo`** — only when the working set exceeds 262144 tokens. It is the
  sole model on the farm that stays 100% GPU-resident beyond that. **No vision.**
- Neither co-resides with the other; switching costs an eviction and an ~18 s reload.
