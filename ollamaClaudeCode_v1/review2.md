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

## Multi-token prediction is worth 1.6–2.7×, and it inverts the profiles

Same weights, same q8 quantisation, same baked context — MTP is the only variable:

| model | tok/s **S** (short, 300-cap) | tok/s **L** (long, uncapped) | ctx fully in VRAM | weights VRAM |
|---|---|---|---|---|
| `qwen3.6:27b-q8_0-ctx60k` | 18.1 | 18.2 | 65536 | 32.87 GB |
| `qwen3.6:27b-mtp-q8_0-ctx60k` | **48.8** | **29.6** | 32768 | 31.82 GB |

Two things stand out.

**The gain decays with generation length** — 2.7× on the short profile, 1.6× on the
long one. This is the expected speculative-decoding signature: draft tokens are
accepted at a high rate early and the acceptance rate falls as the generation goes
on. Every non-MTP model in the matrix has L slightly *above* S (longer runs
amortise warm-up); MTP is the only one where **S > L**, and by a wide margin.

Consequence: a single tok/s figure for an MTP model is close to meaningless — it
encodes the benchmark's output length, not the model's speed. This is the concrete
justification for the two-profile design; averaging them would have buried a 1.6×
spread that depends entirely on how long the answer is.

**MTP costs context headroom.** The ceiling halves from 65536 to 32768 fully in
VRAM even though the weights are slightly *smaller* (31.82 vs 32.87 GB) — the
draft machinery needs its own buffers. For agentic coding that trade is poor: 32768
is below a useful working set, and the `num_ctx/2` overflow rule below means the
real safe working set is ~16k.

## Overflowing `num_ctx` silently costs you *half* the window

Measured on `qwen3.6:27b-q8_0-ctx60k` (baked `num_ctx` 60000), with the corrected
prose haystack:

| needle document | approx. prompt tokens | `num_ctx` | server reported |
|---|---|---|---|
| 40007 words / 248788 chars | ~66k | 60000 | **30002** |
| 80003 words / 499672 chars | ~132k | 60000 | **30002** |

Two prompts differing by a factor of two both come back at exactly 30002 — half
the window plus two. Overflow does **not** fill the context and truncate the
remainder: it discards down to `num_ctx/2`. No error is returned.

Consequences for agentic coding:

- the usable working set of a `-ctx60k` model is **30k tokens**, not 60k, once
  anything overfills it
- because the discarded part includes the document middle (and, per the 16K
  finding, the prompt *tail*), the failure is silent and content-dependent
- so a `-ctx60k` variant is not "60k of headroom"; it is 60k of allocation with a
  30k cliff behind it

This also means the two deep-needle FAILs on this model are **window-limited, not
recall failures** — the model was never shown the needle. The reports distinguish
these cases; a FAIL whose reported prompt size is ≈ `num_ctx/2` is an overflow,
not an inability to retrieve.

Practical rule: size `num_ctx` at **twice** the largest context you actually
intend to use.

## Token accounting, resolved

The corrected prose filler measures **1.63–1.67 tokens per word** (4411 tokens
from 2706 words; 17861 from 10703), which is the normal range for English prose
and confirms the `ThTh` diagnosis below rather than merely correlating with it.
Recall depths are now reported in verified tokens.

## A one-character harness bug that faked a capability

Worth writing down because it produced *confident, plausible, entirely void*
results, and only an arithmetic smell exposed it.

The needle test built its haystack from two sentence templates:

```python
sent=("The service {0} handles inbound requests and logs to shard {1}. "
      "Retention for bucket {0} is {1} days under the standard policy. ")
```

There is no comma between them. Python implicitly concatenates adjacent string
literals, so `sent` was a single 128-character **string**, not a 2-tuple —
and `sent[i%2]` therefore indexed a *character*, returning `'T'` or `'h'`.
The haystack was `ThThThThTh…`.

The tell was in the reported prompt sizes:

| gate | reported `prompt_eval_count` |
|---|---|
| `needle_4k` | 2081 |
| `needle_16k` | 8081 |
| `needle_60k` | 30081 |
| `needle_120k` | 60081 |

Every one is exactly `words/2 + 81` — because `ThTh` packs at about two
characters per token, and 81 is the question framing. Real prose runs ~1.5
tokens per *word*, i.e. three times higher. No plausible tokeniser produces
0.5 tokens/word, and the smallest level could not have been truncation (its
`num_ctx` was 16192, far above the prompt).

So the gate was asking whether a model can spot one sentence inside a wall of
repeating bigrams. Everything passes that. It says nothing about usable context —
and it is the *same* low-entropy failure mode already fixed once in this harness
for `/api/generate`, reintroduced through a different door.

Fixes: add the comma, `assert isinstance(sent, tuple)` so it cannot regress
silently, retarget the word counts so each label names a token level rather than
a word count, and log realised words/chars/`num_ctx` per needle so the document
shape is auditable from the log alone. All first-pass T6 results are void;
`needle-retest.sh` re-runs the needle gates alone and splices corrected rows in,
preserving the unaffected speed and T1–T5/T7 measurements.

**Process lesson:** all the safeguards in this harness are about the *server*
answering wrongly. Nothing checked that the harness built the input it claimed
to. The realised-shape logging is now the check.

## What is benchmarked, and what is deliberately not

`.67` holds 13 model tags, which are **6 distinct weight sets** plus ctx-baked
variants of each. The matrix covers all six:

| weight set | variant benchmarked | axis it contributes |
|---|---|---|
| `qwen3.6:35b-a3b-q4_K_M` | `-ctx128k`, `-ctx256k` | MoE, and the recommended deploy config |
| `qwen3.6:35b-a3b-mtp-q4_K_M` | `-ctx128k` | MoE + MTP combined |
| `qwen3.6:27b-q4_K_M` | `-ctx128k` | dense q4 — architecture control vs the MoE |
| `qwen3.6:27b-q8_0` | `-ctx60k` | dense q8 — quantisation axis (Alex's build) |
| `qwen3.6:27b-mtp-q8_0` | `-ctx60k`, `-ctx128k` | MTP axis, and MTP past its VRAM ceiling |
| `qwen3.5:9b` | `-ctx80k` | small-model baseline, shared with `.37` |

The **6 bare tags are excluded on purpose.** They carry no `num_ctx`, so through
`/v1/messages` they are all capped at 16384 with tool calling silently dead past
that (see the headline finding). Benchmarking them would produce rows describing a
configuration nobody should deploy, and their throughput would be identical to
their variants anyway. `ctx-cliff.sh` documents that behaviour instead.

`qwen3.6:35b-a3b-q4_K_M-ctx256k` was created and measured rather than inferred from
the 128k row: the 128k run showed 262144 fitting in VRAM during the ceiling sweep,
but a sweep only proves allocation, not that the model performs there.

### The old server, same harness

`.37` (12.2 GB) is re-measured with `qwen3.5:9b-ctx80k` and `-ctx96k` through the
*corrected* harness, so the cross-server comparison covers the agentic gates rather
than throughput alone. It also runs **Ollama 0.30.6** against `.67`'s 0.32.5, which
makes it an independent check on whether the `num_ctx/2` overflow behaviour is a
general property or a version-specific quirk.

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
- Do not edit a shell script while an instance of it is running. `agentic-test.sh`
  was patched mid-matrix; bash reads scripts incrementally, so shifting byte
  offsets can drop a running interpreter mid-statement. Function bodies already
  parsed survive, top-level lines may not. The affected model's row set was
  checked for completeness afterwards rather than assumed intact.
- Alex was working on `.67` in parallel during this run (`mtp-q8_0`, `ctx60k`
  variants appeared mid-session). His models are included in the matrix.

## Not obtainable

GPU temperature, utilisation, fan and power. The Ollama HTTP API reports only
model residency, and SSH to both hosts is refused (`publickey,password`).
`ollamaFarm.sh --ssh` implements the `nvidia-smi` path for when key access exists.
