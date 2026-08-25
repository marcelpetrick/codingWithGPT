# Model cards — the v3 benchmark field

One card per model, written **2026-08-25, before measurement**. Everything under *What it
is* comes from a vendor card or a registry manifest. Everything under *The catch* is either
a measurement from v1/v2 on this exact box, or is labelled as a prediction. Nothing here is
a v3 result — those land in `README.md` and `qwen38_eval.md`.

The box: `192.168.100.67`, **≈35.5 GB usable** (measured, v2 §11.4), Ollama **0.32.9**.
The bar: `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 — **131.4 tok/s**, 3,988 tok/s prefill.

**Vendor benchmark numbers are vendor benchmark numbers.** They are quoted because they are
the reason each model is in the field, not because they are evidence about this hardware.
Every one is self-reported, and several are in-house or modified harnesses.

---

## A1–A3 · `qwen3.8:27b` — the model you asked about

**What it is.** Dense **27B** (27.3B), Apache-2.0, weights published **2026-08-14** by
Alibaba's Qwen team. 256K native context, vision encoder, thinking on by default and
disableable per request, with `reasoning_effort` and `preserve_thinking` knobs. Registry
family `qwen35`, renderer `qwen3.8`, parser `qwen3.5`.

Vendor gains over Qwen3.6-27B:

| benchmark | Qwen3.6-27B | Qwen3.8-27B |
|---|---|---|
| Terminal-Bench 2.1 (Terminus) | 63.4 | **73.0** |
| SWE-bench Pro | 53.5 | **61.7** |
| LiveCodeBench v6 | 83.9 | **90.3** |
| OSWorld-Verified | 63.9 | **84.3** |
| DeepSWE 1.1 | 13.3 | **42.2** |

**The catch — two of them.**

*It cannot be pulled today.* Every tag carries `"requires":"0.32.12"`; `.67` runs 0.32.9 and
the registry answers **HTTP 412** before a byte moves. Blocked on the upgrade you have
requested.

*It is dense, and this box punishes dense.* The incumbent activates 3B parameters per token
and reaches 131.4 tok/s. v2 measured the *dense* 27B q8_0 on this same hardware at
**18.1 tok/s** — token generation here is memory-bandwidth-bound, so every parameter is
read for every token. Dense q4 should land somewhere near 35–40 tok/s; that is an
extrapolation from bandwidth, **not a measurement**, and v1's dense-q4 rows cannot settle it
because that run spilled to CPU (`9.60/17.37 SPLIT`).

**And there is no MoE escape hatch.** Qwen has published exactly two Qwen3.8 shapes:
`Qwen3.8-27B` (this one) and `Qwen3.8-2.4T-A95B` — Qwen3.8-Max, ~1.2 TB even at FP8, about
34× this box. The `Qwen3.8-35B-A3B` the community is asking for is **a leak, not a
release**: it appears as a commit in Alibaba's ModelScope `ms-swift` repo and an open
request thread on Hugging Face, with no weights anywhere. So on `.67`, dense is the only
Qwen3.8 there will ever be.

| tag | weights | plan |
|---|---|---|
| `27b-q4_K_M` | 17.74 GB | **A1** — the working candidate |
| `27b-mtp-q4_K_M` | 17.74 GB | **A2** — re-tests v2's finding that MTP is a net loss here |
| `27b-q8_0` | 29.98 GB | **A3** — quality rung; expected to be window-limited, runs only if A1 earns it |

Shipped params: `presence_penalty 0` (v2's 31–35% throughput tax is fixed upstream),
`draft_num_predict 4` (still exactly the setting v2 measured at 100.6 tok/s against 129.2 at
0 — so an `-agentic` variant is still needed, for one knob instead of two).

**What v3 measures:** whether 73.0 on Terminal-Bench survives being three to four times
slower than the model it would replace.

---

## B1 · `laguna-xs-2.1:q4_K_M` — the shape-matched challenger

**What it is.** **Poolside**. 33B total, **3B active**, 256 experts + 1 shared, 40 layers
(10 global attention, 30 sliding-window). 262,144 context. OpenMDW-1.1. **20.27 GB** at q4.
Requires Ollama 0.32.3 — **runs on `.67` today**.

Vendor: SWE-bench Verified **70.9%**, SWE-bench Multilingual 63.1%, SWE-Bench Pro (public)
47.6%, Terminal-Bench 2.0 **37.5%**.

**The catch.** This is the only new model in the field shaped like the incumbent — 3B active,
262144 window, ~20 GB — which makes it the only one that can plausibly *beat* it rather
than trade speed for smarts. That also means it has nowhere to hide: if it does not reach
roughly 130 tok/s, it is strictly worse than what is already installed. Its Terminal-Bench
2.0 number is not comparable to Qwen3.8's Terminal-Bench **2.1** number; different harness
version, and neither was run by us.

**On arrival, 2026-08-25** (`/api/show` + a smoke load; *not* the benchmark):

- capabilities `completion, tools, thinking` — no vision
- **bakes no parameters at all.** No `presence_penalty`, so v2's 31–35% vendor tax is
  absent; but also no `num_ctx`, so it is a **bare tag** and inherits the default window
- 40 blocks, 256 experts, 8 used per token, 1 shared, 8 KV heads
- **its 262144 is YaRN, not native.** `rope.scaling.original_context_length = 8192`,
  `type = yarn`, `factor = 32` → 8192 × 32 = 262144. Extended windows are exactly where
  retrieval quietly degrades, which makes the needle test load-bearing for this model
- loads at **21.25 GB, 100% GPU**, 18.8 s cold; a 16-token smoke generation ran at
  105.6 tok/s (too short to be a throughput measurement — it is here to show it runs)

**MEASURED, 2026-08-25 — fastest challenger, and the only model that failed a gate.**

| | |
|---|---|
| generation @2k / @20k words | **119.5** / 93.5 tok/s |
| prefill @20k words | **4,882 tok/s** (+22% vs incumbent) |
| resident @262144 | 25.01 GB, 100% GPU |
| tool gates | **8/10** — T4 PARTIAL, T7 FLAKY |
| needle @160k | PASS @ 143,353 tok |
| Claude Code session | PASS, 42 s, 18 turns |

It is 9% off the incumbent's generation and beats it on prefill — and it still is not
recommended, because of the two gates. **T4:** it emits one tool call where two independent
ones were available; Claude Code batches by design, so every serialised call costs a full
round trip and eats the prefill win. **T7:** tool calling at 53,145 tokens passed twice and
failed once. A flaky gate fails on turn three of a long session, once the context is
expensive to rebuild — worse to live with than an outright failure, and invisible to every
speed benchmark.

The YaRN risk this card flagged did **not** materialise: it retrieved cleanly at 143k despite
the window being extended from a native 8192.

---

## B2 · `north-mini-code-1.0:q4_K_M` — the one built for this job

**What it is.** **Cohere**. 30B total, **3B active**, sparse MoE with 128 experts, 8
activated per token; sliding-window and global attention interleaved 3:1. **256K context,
up to 64K output tokens.** Apache-2.0 plus Cohere Lab's Acceptable Use Policy.
**18.59 GB** at q4. Requires Ollama 0.30.10 — **runs on `.67` today**.

Explicitly trained for agentic software engineering across SWE-Agent, OpenCode and
Terminus 2. Native tool use with interleaved thinking; Cohere say it works best with
thinking enabled. Vendor cites one figure: **33.4 on Artificial Analysis' Coding Index**.

**The catch.** Trained-for-agents is a claim about *frameworks Claude Code is not*. A model
tuned on SWE-Agent and Terminus transcripts may or may not emit the tool-call shape Ollama's
`/v1/messages` renderer expects, and that is a pass/fail gate, not a gradient — v2's T1–T5
exist because Ollama's `tools` capability label is a manifest field rather than a test.
Note also the mismatch worth resolving: Cohere's card says 256K, the Ollama library listing
says 488K. One of them is wrong, and the KV ladder will say which.

**On arrival, 2026-08-25** — and the context contradiction is **resolved**:

The GGUF says `cohere2moe.context_length = **500000**`. Ollama's library page shows "488K"
because 500000 ÷ 1024 = 488.28 — a display artifact, not a second number. So Ollama and the
weights agree at 500,000 tokens, and it is **Cohere's own card understating it at 256K**.
Whether 500,000 *fits on this box* is a different question, and the KV ladder answers it.

- capabilities `completion, tools, thinking` — no vision
- bakes `temperature 1`, `top_p 0.95`. No `presence_penalty` (good), no `num_ctx` — **bare
  tag**, same 16,384 trap as the others
- 49 blocks, 128 experts, 8 used per token, 4 KV heads, rope scaling `none` — so unlike
  Laguna its long window is native rather than YaRN-extended
- loads at **20.04 GB, 100% GPU**, 23.1 s cold; 81.7 tok/s on a 16-token smoke generation

**MEASURED, 2026-08-25 — takes the deep-context slot, but not at the window it advertises.**

| | |
|---|---|
| generation @2k / @20k words | 83.6 / 78.2 tok/s |
| prefill @20k words | 4,331 tok/s (+11% vs incumbent) |
| resident @262144 / @500000 | **21.34 GB** / 23.29 GB, 100% GPU |
| tool gates | **10/10** |
| needle @160k | PASS @ 114,457 tok |
| retrieval at depth | reliable to **201,737**; unexplained failure at 230,825 |
| Claude Code session | PASS, 60 s, 22 turns |

Against the deep-context option v2 recommended (`nemotron-3.5-lightning`, 44.9 tok/s,
31.21 GB at 262144), this is **8 GB lighter, 1.9× faster and equal on gates**. It takes the
slot.

**But not at 500,000.** It *allocates* the full window in 23.29 GB; it does not retrieve
across it. Measured: FAIL at 230,825 tokens (3/3, including with `num_ctx` pinned to 500000
and a 2048-token budget — both candidate harness explanations tested and dead), **PASS at
347,193 (3/3)**, FAIL at 398,089 and 456,281. Non-monotonic, reproducible in both directions,
and unexplained. Deploy the **`-ctx256k`** variant.

One thing in its favour when it does fail: at 456,281 tokens it answered *"the document does
not contain any information about a deploy…"*. It reports not finding the needle. v2's
Nemotron, truncated, invented `deploy-passphrase-2024` instead.

---

## B3 · `gemma4:26b-a4b-it-q4_K_M` — the other vendor's template

**What it is.** **Google DeepMind**. 25.8B total, **~4B active** MoE, 256K context, text and
image input, configurable thinking modes, native function calling. **17.99 GB** at q4.
Requires Ollama 0.20.0 — **runs on `.67` today**.

Vendor: MMLU Pro **82.6%**, LiveCodeBench v6 **77.1%** (the dense 31B sibling: 85.2% and
80.0%).

**The catch.** It is here as a *diversity* control rather than a favourite. Every other model
in this field is a Qwen derivative or a Qwen-shaped MoE, so all of them share a family of
chat templates and failure modes; Gemma's is genuinely different, and a tool-calling bug
that hits everything except Gemma would be indistinguishable from "these models are bad"
without it. Its LiveCodeBench is well under Qwen3.8's 90.3. Also unclear whether it is new
at all — its manifests require Ollama 0.20.0, which suggests the family predates v2 and only
the tags were refreshed.

**On arrival, 2026-08-25:**

- capabilities `completion, vision, tools, thinking` — the only candidate here with vision
- bakes `temperature 1`, `top_k 64`, `top_p 0.95`; no `presence_penalty`, no `num_ctx` —
  **bare tag** like the other two
- 30 blocks, 128 experts, 8 used per token, plus a 27-block vision tower
- loads at **18.39 GB, 100% GPU**, 12.9 s cold — the lightest and fastest-loading of the
  three; 73.5 tok/s on a 64-token smoke generation
- **observed once, not yet reproduced:** one `/api/chat` response carried a raw control
  character inside a JSON string, which a strict JSON parser rejects (`Invalid control
  character at line 1 column 186`). The retry parsed cleanly. Recorded because a malformed
  response body is a client-breaking failure rather than a quality one, but one occurrence
  is not a finding — it needs reproducing before it is claimed

**MEASURED, 2026-08-25 — slowest to generate, fastest to read, and clean on every gate.**

| | |
|---|---|
| generation @2k / @20k words | 70.0 / 65.4 tok/s |
| prefill @20k words | **5,740 tok/s** — the fastest measured on this box, +44% vs incumbent |
| resident @262144 | 22.15 GB, 100% GPU |
| tool gates | **10/10** |
| needle @160k | PASS @ 143,324 tok |
| Claude Code session | PASS, 60 s, 16 turns |

The diversity control earned its place: a non-Qwen tool-calling template passed all seven
gates, which retires the worry that a template bug was hiding behind a field of Qwen
derivatives. Its 47% generation deficit is real and rules it out as a default driver, but the
prefill number is the highest on the box and it is one of only two candidates with vision.

---

## C1 · `qwen3.6:35b-a3b-q4_K_M-agentic` — the incumbent, and the control

**What it is.** Already on `.67`, already the recommendation. 36.0B total, **3B active**,
23.94 GB of weights, `num_ctx 262144` baked, `presence_penalty` cleared. Vision.

**Measured on this box** (v2, 2026-08-13, not vendor claims):

| | |
|---|---|
| generation | **131.4 tok/s** |
| prefill @ 35k | **3,988 tok/s** |
| resident @ 262144 | 32.54 GB, 100% GPU |
| tool gates T1–T5 | 5/5 |
| needle | PASS at 146,957 tokens |

**The catch — why it must be re-run rather than quoted.** Those numbers were taken on Ollama
**0.32.9**. The moment `.67` moves to 0.32.15 for Qwen3.8, every v2 figure becomes
cross-version and the comparison is no longer apples to apples — 0.32.15's release notes
claim caching that cuts time-to-first-token roughly in half, which would land squarely on
the prefill column. So the incumbent is measured again, in the same session as whatever it
is being compared against. A control is not a formality here; without it, v3 would be
comparing new models on a new runtime against old models on an old one and calling the
difference a model difference.

**RE-MEASURED, 2026-08-25 — reproduces v2 to within 2%, and still wins.**

| | v2 (08-13) | v3 (08-25) |
|---|---|---|
| generation @2k | 131.4 | **130.0** |
| prefill @20k | 3,988 | 3,911 |
| resident @262144 | 32.54 GB | 32.54 GB |
| gates | 10/10 | **10/10** |
| needle @160k | PASS @ 146,957 | PASS @ **146,957** |
| Claude Code session | — | PASS, 46 s, 16 turns |

The 160k needle landed on the *same token count* twelve days apart, and throughput drifted
under 2%. So v2's numbers are valid comparators while `.67` stays on 0.32.9 — and the
incumbent remains the fastest generator, is clean on every gate, and retrieves deepest of
anything measured. Nothing in the 2026-08 field displaced it.

---

## The reference models — measured for contrast, mostly not recommended

Added so that "dense is slow on this box" is a measurement rather than an assertion.

### `qwen3.6:27b-q4_K_M-ctx128k-agentic` — the Qwen3.8 stand-in · **KEEP**

Same vendor, same 27B dense shape, same Q4_K_M as the blocked `qwen3.8:27b-q4_K_M`
(17.42 GB against 17.74 GB). Never cleanly measured before — v1's run spilled to CPU
(`9.60/17.37 SPLIT`) and the `-ctx128k` tag on the box bakes `presence_penalty 1.5`, the
vendor default worth 31–35%. A clean variant was baked for this report.

**31.0 tok/s · 1,307 prefill · 131,072 max window · 30.17 GB · 9/10 gates · 140 s session.**
Against the incumbent that is **4.2× slower to generate, 3.0× slower to prefill, half the
window, 3.0× slower end to end**. Its KV costs **64,784 bytes/token** against an MoE's
~16,384. Keep it until Stage A: it is the baseline Qwen3.8 gets compared against.

### `nemotron-3.5-lightning:30b-ctx256k-agentic` — the outgoing deep-context pick · **KEEP**

Mamba-2 + MoE hybrid, 32.9 B total / 3 B active. **43.9 tok/s · 3,050 prefill · 524,288 max
window · 31.21 GB · 10/10 gates · needle to 161,516 · 113 s session.** Still the only model
on the box that holds more than 500k tokens, and it retrieves deeper than anything else
measured. Superseded for everyday deep-context work by north-mini — 8 GB lighter and 1.9×
faster for the same job — but kept, because its window ceiling is genuinely unmatched.

Its documented failure mode remains the worst on this hardware: on a truncated prompt it
**invented** a plausible passphrase (`deploy-passphrase-2024`), with no error and no signal.

### `muse-glimmer:30b-ctx128k-agentic` — dense, and it shows · **DELETED**

**28.5 tok/s · 1,963 prefill · 131,072 window · 19.45 GB · 10/10 gates\* · needle to 114,487 ·
160 s session** — 4.6× slower than the incumbent end to end. The lightest resident footprint
measured (19.45 GB), which is its one real advantage, and not enough of one.

\* Its raw `agentic-test.sh` T6 rows read FAIL; that is v1's `num_predict 64` artifact —
Muse needs ~70 tokens to answer and the log shows `eval=70–84`. Under a 512-token budget it
passes all four depths.

### `qwen3.6:27b-q8_0-agentic` — the quality rung nobody should climb · **KEPT, unused**

**19.5 tok/s · 1,464 prefill · 81,920 window · 34.03 GB · 9/10 gates · 179 s session.** The
slowest model measured on this box in every dimension, with the smallest window and the
largest footprint. Past its window it fabricates: the 160k needle returned `'5276'` at
`prompt_eval=40962`, exactly half of 81,920.

---

## What they all have in common, and it is a trap

**None of the three bakes a `num_ctx`.** Every one is a bare tag in v2's sense, and v2
measured what that costs: on `/v1/messages` a bare tag inherits a **16,384** window, past
which the prompt tail is discarded and **tool calling stops entirely, with no error**. The
models are not at fault and neither is the vendor — it is how Ollama's endpoint behaves — but
it means *not one of these models can be used with Claude Code as pulled*. Each needs an
`-agentic` variant with the window baked in, and that is step 1 of the battery.

The good news, and it is a genuine change since v2: **none of them ships
`presence_penalty`.** That vendor default cost 31–35% of throughput on the Qwen3.6 tags and
was the single cheapest win in v2. The 2026-08 field appears to have dropped it.

---

## Not in the field, and why

| model | reason |
|---|---|
| `Qwen3.8-2.4T-A95B` (Qwen3.8-Max) | ~1.2 TB at FP8. The only Qwen3.8 MoE that exists. |
| `Qwen3.8-35B-A3B` | does not exist — a ModelScope commit and a community request thread |
| `deepseek-v4-flash` | 284B-A13B, **~150 GB at Q4**. An August roundup calls it the 32 GB-VRAM model; the vendor asks for 2×H100 |
| `glm-5.2/5.3`, `kimi-k3`, `minimax-m3`, `deepseek-v4-pro` | 428B–2.8T |
| `laguna-s-2.1` | 118B-A8B → ~65 GB at q4 |
| `ornith-1.5:35b` | 22.62 GB and it would fit — but the card lists **no tool capability**. A driver that cannot call tools is not a candidate |
| `gemma4:31b` | dense 31B; the q8 rung is 33.83 GB, leaving no window |
| `qwen3.8` bf16 / mlx / mxfp8 / nvfp4 | 56–68 GB, Apple-only, or needs Blackwell we cannot confirm |
