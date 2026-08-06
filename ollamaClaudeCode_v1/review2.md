# Review round 2 — model matrix on `.67`, and the 16K trap

2026-08-06. Round 1 (server comparison) is in `review.md`. One-page summary:
`evaluation.pdf`.

---

## The headline: a silent 16K context cap that kills tool calling

This is the most consequential finding of the whole exercise, and it is
effectively invisible without testing for it.

A model whose Modelfile leaves `num_ctx` **unset** inherits the server default.
The Anthropic-compatible `/v1/messages` endpoint — the one Claude Code talks to —
has **no `num_ctx` parameter**, so nothing can override it per request.

Measured, same prompt, two models:

| input sent | `35b-a3b-q4_K_M` (`num_ctx` unset) | `qwen3.5:9b-ctx80k` (81920 baked in) |
|---|---|---|
| ~4k tokens | 4090 processed · tool call ✓ | 4090 · ✓ |
| ~16k tokens | 16090 processed · tool call ✓ | 16090 · ✓ |
| ~32k tokens | **16386 processed · tool call ✗** | 33290 · ✓ |
| ~50k tokens | **16386 processed · tool call ✗** | 53090 · ✓ |

The cap is **16384 tokens**. Past it the *tail* of the prompt is discarded — and
the tail is where the instruction lives — so the model stops emitting `tool_use`
blocks entirely. **No error is returned at any layer.**

What makes this nasty is how healthy the model looks by every other measure:

- it advertises 262144 context
- its weights + KV for 262144 **fit entirely in VRAM** at 33.09 GB
- it retrieves a needle buried mid-document at 60k prompt tokens through
  `/api/chat` with an explicit `num_ctx`
- it passes a simple one-tool probe

…and still hands Claude Code a 16K window that silently stops calling tools.

This also explains the `-ctx60k` variants that appeared on `.67` from Alex
during this work: the same wall, hit independently.

### The fix, verified

Bake `num_ctx` into a Modelfile variant:

```shell
curl -X POST http://192.168.100.67:11434/api/create \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6:35b-a3b-q4_K_M-ctx128k",
       "from":"qwen3.6:35b-a3b-q4_K_M",
       "parameters":{"num_ctx":131072},"stream":false}'
```

`qwen3.6:35b-a3b-q4_K_M-ctx128k` then processes all 53090 tokens with tool
calling intact. `ctx-cliff.sh` reproduces the measurement for any model.

**Rule for this server: never point Claude Code at a bare model tag.** Only use a
variant with `num_ctx` baked in.

---

## Why the "36B" model is fast — resolved

`qwen3.6:35b-a3b` is a **mixture-of-experts** (`archqwen35moe`): 36B total
parameters, **~3B active per token**. Generation is memory-bandwidth-bound on
*active* weights, so it streams less per token than an 8B dense model does.

| Model | Total | Active/token | tok/s |
|---|---|---|---|
| `qwen3.6:35b-a3b-q4_K_M-ctx128k` | 36B | 3B (MoE) | **86.1** (ours) |
| `qwen3.6:35b-a3b` q4_K_M | 36B | 3B (MoE) | 89.8 (Alex) |
| `llama3.1:8b` | 8B | 8B dense | 86.9 (Alex) |
| `qwen3.6:27b-q8_0` | 27.8B | 27.8B dense @ q8 | **18.1** (ours) |

Nothing is wrong with `.67`. The model that was installed on it was simply the
worst available combination for the hardware — dense *and* q8, streaming ~30 GB
per token where the MoE streams ~2 GB. **Model choice is worth ~4.8× here.**

---

## KV cache is far cheaper on the MoE than predicted

Round 1 measured ~0.08 GB per 1k tokens on a dense 27B at q8 and flagged that the
rate would not transfer to a different architecture. It did not — and the reality
is better than the estimate:

| Model | KV per 1k tokens | 262144 ctx total |
|---|---|---|
| `qwen3.6:27b-q8_0` (dense) | ~0.080 GB | would not fit |
| `qwen3.6:35b-a3b-q4_K_M` (MoE) | **~0.032 GB** | **33.09 GB — fits** |

Consequence: the MoE holds the **full 262144 context entirely in VRAM**. Round 1's
extrapolated estimate for this model was ~150k; the measured answer is 256k.
The flagged caveat was the right call.

---

## Tool calling at high context is probabilistic, not binary

During harness validation, the "tool call with ~53k tokens already in the window"
test returned **PASS and then FAIL on byte-identical input** at the same 53281
tokens for `qwen3.5:9b-ctx80k`.

A single trial would report a coin flip as a capability, so the gate is scored as
a rate over three trials and labelled **FLAKY** when mixed. For agentic coding
this distinction matters more than raw throughput: a model that drops tool calls
one time in three will stall an agent loop unpredictably rather than fail loudly.

---

## Schema drift is a distinct failure mode from no-call

Given a realistic patch tool (enums plus an array of objects), `qwen3.5:9b`
produced a **semantically correct** patch using **invented field names**:
`file_path` for the required `path`, `old_lines`/`new_lines` for `old`/`new`.

That still breaks a strict tool runtime, but it is a different defect from
emitting no call at all — which is what the MoE did on the same test at default
`max_tokens`. The harness reports the two separately.

---

## Method notes

- Only **ctx-baked variants** were benchmarked. Testing a bare tag would measure a
  configuration nobody should run.
- Two harness bugs were found and fixed during validation, both of which would
  have produced confidently wrong results:
  - the needle document cannot pass through `argv` (`jq: Argument list too long`);
    request bodies are built in Python and posted with `curl -d @file`
  - raw `/api/generate` with low-entropy filler made models echo the prompt and
    stop after 2 tokens; the needle test uses `/api/chat` framing with the
    question asked both before and after the document
- `/v1/messages` responses sometimes contain unescaped control characters and must
  be parsed with `strict=False`.
- Alex was working on `.67` in parallel during this run (`mtp-q8_0`, `ctx60k`
  variants appeared mid-session). His models are included in the matrix.

## Not obtainable

GPU temperature, utilisation, fan and power. The Ollama HTTP API reports only
model residency, and SSH to both hosts is refused (`publickey,password`).
`ollamaFarm.sh --ssh` implements the `nvidia-smi` path for when key access exists.
