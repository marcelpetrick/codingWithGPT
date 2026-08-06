# Review round 2 — model matrix on `.67`, and the 16K trap

2026-08-06. Round 1 (server comparison) is in `review.md`. One-page summary:
`evaluation.pdf`.

---

## The biggest single win: `presence_penalty 0` is worth +53% throughput

Every model on both hosts ships qwen's prose sampling defaults:

```
temperature 1   top_p 0.95   top_k 20   presence_penalty 1.5
```

Isolated on `qwen3.6:35b-a3b-q4_K_M`, `num_ctx` 262144, 33.08 GB resident in every
case — the only variable is sampling:

| config | tok/s S | tok/s L | vs default |
|---|---|---|---|
| vendor defaults (temp 1, pp 1.5) | 82.2 | 84.4 | — |
| `temperature 0` only | 77.7 | 83.2 | **no gain** |
| **`presence_penalty 0` only** | 124.9 | **129.5** | **+53%** |
| `temperature 0` + `presence_penalty 0` | **127.2** | **131.5** | **+56%** |

**`presence_penalty 1.5` costs about 35% of generation throughput.** It requires a
per-token pass over the vocabulary to penalise already-emitted tokens; at 0 that
pass is skipped. `temperature 0` contributes nothing to speed.

This is free performance hiding in a vendor default that nothing warns about, on
the model that was already the fastest on the box.

### `temperature 0` is a separate fix, for reliability

The default `temperature 1` makes structured tool calls a coin flip on the small
model. T5 (nested schema: enums plus an array of objects), 8 trials per config:

| model | vendor defaults | `temperature 0` |
|---|---|---|
| `qwen3.5:9b-ctx96k` (.37) | **5/8** | **8/8** |
| `qwen3.5:9b-ctx80k` (.37) | **4/8** | **8/8** |
| `qwen3.6:35b-a3b-q4_K_M-ctx256k` (.67) | 8/8 | 8/8 |

Failures were a mix of `no_tool_call`, `edits_not_an_array` and missing
`path`/`mode` keys — i.e. the same "schema drift" retracted earlier in this
document, now correctly attributed to **sampling temperature** rather than to the
model or to the token budget.

`presence_penalty` was tested for this too and is **not** the cause: at
`temperature 1` with `presence_penalty 0` the 9b scored 7/8 against 5/8 at the
default, which is well inside noise at n=8 (Fisher exact p ≈ 0.57). An earlier
draft of this document hypothesised that `presence_penalty 1.5` breaks nested JSON
by penalising repeated field names. That hypothesis is **wrong** and is withdrawn —
its real cost is throughput, not correctness.

The MoE is robust at either temperature (8/8 both ways), which is one more reason to
prefer it; but `temperature 0` remains correct for agent loops, where reproducibility
matters independently of pass rate.

### This invalidates the single-trial gate results

Gates T1–T6 were run **once** per model. T5 on the 9b is now known to pass about
half the time at default sampling, so:

- the matrix's `T5 PASS` for `qwen3.5:9b-ctx80k` was a coin landing heads
- the `T5 FAIL` for `qwen3.5:9b-ctx96k` was the same coin landing tails

Neither measured a capability. The earlier claim in this document that "every model
passed every capability gate" is therefore **too strong** and is corrected: every
model passed on the trial that was run, and only T7 (3 trials) carries a replication
count. Sampling-sensitive gates need repetition; the pass/fail of a single call on a
temperature-1 model is not a property of the model.

### Recommended deployment variant, built and verified

```shell
curl -X POST http://192.168.100.67:11434/api/create \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6:35b-a3b-q4_K_M-agentic",
       "from":"qwen3.6:35b-a3b-q4_K_M",
       "parameters":{"num_ctx":262144,"temperature":0,"presence_penalty":0},
       "stream":false}'
```

Measured: **127.2 / 131.5 tok/s**, 33.08 GB fully in VRAM, 262144 context resident,
**all ten gates PASS**, needle recalled at **146957 prompt tokens**.

That is **7.2×** the throughput of the `qwen3.6:27b-q8_0` that was installed on the
box at the start of this exercise, on the same hardware.

## Results — full matrix on `.67` (36.1 GB, two GPUs)

All seven ctx-baked variants, thinking disabled, sorted by long-profile throughput:

| model | VRAM | placement | tok/s S | tok/s L | ctx fully in VRAM |
|---|---|---|---|---|---|
| **`qwen3.6:35b-a3b-q4_K_M-ctx256k`** | 33.08 | full | **82.2** | **84.4** | **262144** |
| `qwen3.6:35b-a3b-q4_K_M-ctx128k` | 28.25 | full | 80.0 | 86.2 | 262144 |
| `qwen3.5:9b-ctx80k` | 8.79 | full | 65.1 | 67.3 | 262144 |
| `qwen3.6:35b-a3b-mtp-q4_K_M-ctx128k` | 26.14 | full | 51.4 | 64.8 | 262144 |
| `qwen3.6:27b-mtp-q8_0-ctx60k` | 31.82 | full | 48.8 | 29.6 | 32768 |
| `qwen3.6:27b-q4_K_M-ctx128k` | 30.43 | full | 27.8 | 28.0 | 131072 |
| `qwen3.6:27b-q8_0-ctx60k` | 32.87 | full | 18.1 | 18.2 | 65536 |
| `qwen3.6:27b-mtp-q8_0-ctx128k` | 36.65 | **SPLIT** | 11.1 | 5.6 | 32768 |

Every model passed every capability gate **on the single trial that was run** (T7
excepted, which is 3/3 across three trials for every model). As the sampling section
above establishes, a single trial at `temperature 1` is not a capability measurement
— the 9b passes T5 only about half the time at default sampling. Read this table as
"no model showed a systematic capability gap", not as "all capabilities verified".

Once thinking is disabled and the budget is adequate, capability is not the
differentiator on this hardware. **Throughput, usable context, and sampling
configuration are.**

Recall depth tracks the configured window exactly, as the overflow rule predicts:

| model | deepest verified recall |
|---|---|
| **`35b-a3b-q4_K_M-ctx256k`** | **146957 tokens** |
| `35b-a3b-q4_K_M-ctx128k`, `35b-a3b-mtp-q4_K_M-ctx128k`, `27b-mtp-q8_0-ctx128k`, `9b-ctx80k` | 72419 tokens (window-limited) |
| `27b-q8_0-ctx60k`, `27b-mtp-q8_0-ctx60k` | 17861 tokens (window-limited) |

Only the 256k build was ever shown a document deeper than ~72k tokens; for every
other model the deeper needle overflowed the window and was discarded before the
model saw it. These are configuration ceilings, not model ceilings.

### The 256k config, measured rather than inferred

The 128k run's ceiling sweep showed 262144 *fitting* in VRAM, but allocation is not
performance, so the config being recommended was built and measured:

| `qwen3.6:35b-a3b-q4_K_M` | VRAM | tok/s S | tok/s L | deepest verified recall |
|---|---|---|---|---|
| `-ctx128k` | 28.25 | 80.0 | 86.2 | 72419 (window-limited) |
| **`-ctx256k`** | **33.08** | **82.2** | **84.4** | **146957** |

The full 256k window costs 4.8 GB and about 2% on the long profile — inside
run-to-run noise, and the short profile came out marginally *higher* — while
doubling verified usable recall. **Throughput does not degrade with a 256k window
on this model**, which is the fact the sweep could not establish on its own.

### Verdict

**`qwen3.6:35b-a3b-q4_K_M-agentic`** — `num_ctx` 262144, `temperature` 0,
`presence_penalty` 0.

Measured at **127.2 / 131.5 tok/s**, 33.08 GB fully resident, full 262144 context in
VRAM, all ten gates PASS, needle recalled at **146957 prompt tokens**.

| against | factor |
|---|---|
| `qwen3.6:27b-q8_0` — what was installed on the box | **7.2×** |
| `qwen3.6:27b-q4_K_M` — dense, same quantisation | **4.7×** |
| the same MoE at vendor sampling defaults | **1.56×** |

Three independent decisions produced that, in descending order of value: choosing the
**MoE** architecture (3.1× over dense q4), clearing **`presence_penalty`** (1.53×),
and baking a `num_ctx` that fits **entirely in VRAM** (avoids a 5.3× loss).

Second choice is `qwen3.5:9b-ctx80k` — 8.79 GB and 67.3 tok/s. Not as capable per
token, but it leaves ~27 GB free for a second model, which is what makes running an
agent and a reviewer side by side possible.

Avoid `-mtp-` builds on the MoE (slower, see below) and any `num_ctx` that does not
fit in VRAM (5.3× penalty, see below).

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

## Schema drift was a budget artifact, not a model trait — corrected

An earlier version of this document reported that `qwen3.5:9b`, given a realistic
patch tool (enums plus an array of objects), produced a semantically correct patch
using **invented field names** (`file_path` for `path`, `old_lines`/`new_lines` for
`old`/`new`), and presented that as a property of the model.

That was measured before the harness was corrected — under `max_tokens=1200` with
thinking left on. Re-measured with `thinking:{"type":"disabled"}` and a 4000-token
budget, the same model on the same test returns `nested_schema_exact_2_edits`: the
exact schema, correct field names. **Every model in the matrix passes this gate.**

So schema drift here was a symptom of budget pressure, not a capability limit. It
belongs with the other budget artifacts:

| symptom under a squeezed budget | what it actually was |
|---|---|
| MoE emitted no tool call at all | 4487 chars of thinking, then `stop_reason=max_tokens` |
| `9b` invented field names | degraded output under the same pressure |

The general lesson is the one worth keeping: **a thinking model under a tight token
budget fails in ways that look like incapability** — no call, wrong schema, wrong
tool — and those failures disappear when the budget is adequate and thinking is
disabled. Any tool-use evaluation that does not control for both is measuring its
own configuration. Disabling thinking also cut the same call from 166 output tokens
to 40, so it is the cheaper configuration as well as the more capable one.

---

## MTP helps the dense model and *hurts* the MoE

The single most surprising result. MTP is not a free speed-up — its sign depends on
what the model was bottlenecked by:

| MTP applied to | tok/s S | tok/s L | effect |
|---|---|---|---|
| dense `qwen3.6:27b-q8_0` | 18.1 → **48.8** | 18.2 → **29.6** | **+170% / +63%** |
| MoE `qwen3.6:35b-a3b-q4_K_M` | 80.0 → **51.4** | 86.2 → **64.8** | **−36% / −25%** |

The mechanism is consistent with the MoE result earlier in this document.
Multi-token prediction trades *extra compute* (drafting several tokens, then
verifying them) for *fewer weight passes*. That is a winning trade only when
decoding is starved on memory bandwidth:

- the dense q8 streams ~30 GB of weights per token — badly bandwidth-bound, so
  eliminating weight passes is worth a great deal
- the MoE streams only ~2 GB of *active* experts per token — it was never
  bandwidth-starved, so the draft-and-verify overhead costs more compute than the
  saved bandwidth is worth, and throughput drops

**Do not treat MTP as a generic optimisation.** It is a targeted fix for
bandwidth-bound dense models. Applied to an already-efficient MoE it is a
regression — and, being a separate model tag, it looks like a strict upgrade.

This resolves the tension flagged earlier between MTP's speed and its context cost:
on the architecture that actually wins here, MTP is not a trade-off to balance, it
is simply the wrong choice.

One genuine advantage, which does not rescue it: MoE+MTP is smaller
(26.14 GB vs 28.25) and holds 262144 in VRAM at **27.57 GB** against the plain
MoE's 33.09 GB. Its ceiling-sweep increments are non-monotonic
(23.33 → 25.72 → 26.15 → 27.57 GB), which points at allocator granularity rather
than clean KV growth, so no per-1k KV rate is quoted for it. Cheaper, but 25% slower.

## Multi-token prediction is worth 1.6–2.7× on a dense model, and it inverts the profiles

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

Measured with the corrected prose haystack, across two different window sizes:

| model | `num_ctx` | approx. prompt tokens | server reported |
|---|---|---|---|
| `qwen3.6:27b-q8_0-ctx60k` | 60000 | ~66k | **30002** |
| `qwen3.6:27b-q8_0-ctx60k` | 60000 | ~132k | **30002** |
| `qwen3.6:27b-mtp-q8_0-ctx60k` | 60000 | ~66k | **30002** |
| `qwen3.6:27b-mtp-q8_0-ctx60k` | 60000 | ~132k | **30002** |
| `qwen3.6:27b-mtp-q8_0-ctx128k` | 131072 | ~132k | **65538** |
| `qwen3.5:9b-ctx80k` | 81920 | ~132k | **40962** |

Prompts differing by a factor of two come back identical, and the retained amount
is exactly **`num_ctx / 2 + 2`** at 60000, 81920 and 131072 — three window sizes
across four models. That makes it a rule rather than an artifact of one number.

### …and it is a regression in Ollama 0.32.5, not general behaviour

The cross-version check settles it. Same model, same ctx-baked variant, same
document, same `num_ctx` — only the server version differs:

| host | Ollama | `num_ctx` | document | retained | formula |
|---|---|---|---|---|---|
| `.67` | **0.32.5** | 81920 | ~132k tok | **40962** | `n/2 + 2` |
| `.37` | **0.30.6** | 81920 | ~132k tok | **81919** | `n − 1` |

`qwen3.5:9b-ctx80k` is byte-identical on both hosts and the needle document is
generated deterministically, so the Ollama version is the only variable.

**0.30.6 fills the window; 0.32.5 discards half of it.** The half-window rule is
therefore a *regression in the newer Ollama*, not a property of llama.cpp context
handling or of these models. On this axis the newer server is the worse one, and
`.67` is the box that has it.

This does not change the deployment rule — sizing `num_ctx` at twice the intended
usage is still correct on `.67`, and is harmless on `.37` — but it does mean the
cost is a fixable software regression rather than an inherent limit. Worth
re-testing when `.67` is next upgraded, and worth checking before assuming a newer
Ollama is strictly better.

Overflow does **not** fill the context and truncate the remainder: it discards down
to half. No error is returned.

(The same model recalled a needle at 72419 tokens when `num_ctx` was 131072 and the
document fit — so this is the overflow path specifically, not a ceiling on what the
model can use.)

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

## A 12.5% VRAM spill costs 5.3× throughput

The cleanest single-variable result in the matrix. Identical weights, identical
quantisation, identical MTP — the *only* difference is the baked `num_ctx`:

| model | tok/s S | tok/s L | placement |
|---|---|---|---|
| `qwen3.6:27b-mtp-q8_0-ctx60k` | 48.8 | 29.6 | 31.82 GB, fully in VRAM |
| `qwen3.6:27b-mtp-q8_0-ctx128k` | 11.1 | **5.6** | 32.07 / 36.65 GB — **4.58 GB on CPU** |

Pushing 12.5% of the model into system RAM costs **5.3× on the long profile** and
4.4× on the short one. The penalty is wildly disproportionate to the fraction
displaced, because every token must now cross the PCIe boundary for that slice.

So over-provisioning `num_ctx` is not merely wasteful — it is the single most
expensive misconfiguration available on this box, and it looks completely healthy
from the outside: the model loads, answers correctly, and passes every capability
gate. It is simply five times slower. (This model still recalled a needle at 72419
prompt tokens — correct, and unusable, at 5.6 tok/s.)

### The resulting deployment rule

Two findings pull in opposite directions — the `num_ctx/2` overflow cliff rewards a
*large* window, while spilling punishes one that is *too* large. They resolve
cleanly:

> Bake `num_ctx` as large as fits **entirely in VRAM**, and not one token larger.
> Then plan real usage at **half** that number.

Check placement, never assume it: `size_vram < size` in `/api/ps` is the spill
signal, and `ollamaFarm.sh` surfaces it per model. A split model is a
five-times-slower model that reports no error.

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
