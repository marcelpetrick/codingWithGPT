# Model cards — the v3 benchmark field

One card per model, written **2026-08-25, before measurement**. Everything under *What it
is* comes from a vendor card or a registry manifest; everything else was either a v1/v2
measurement on this exact box or was labelled as a prediction.

**The Qwen3.8 card (A1–A3) has since been updated with results** — measured 2026-08-27 on
Ollama 0.32.15, and written to show the pre-registered prediction next to what happened.
Every other card is still pre-measurement; their results are in
[`README.md`](README.md) and [`measurements.md`](measurements.md).

The box: `192.168.100.67`, **35.56 GB usable** — a v2 single observation that Stage A
reproduced to three decimals a model generation later (`measurements.md` §19c).
Runtime: **0.32.9** when these cards were written, **0.32.15** since 2026-08-27 — a
difference worth 0% to +221% of generation throughput depending on the model, so treat any
tok/s figure below without a version attached as a 0.32.9 number.
The bar, as it stood: `qwen3.6:35b-a3b-q4_K_M-agentic` @ 262144 — **131.4 tok/s**.

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

**Measured 2026-08-27 on Ollama 0.32.15.** The blocker cleared and all three rungs ran.
Full detail in [`measurements.md`](measurements.md) §12–21.

| | A1 `27b-q4_K_M` | A2 `27b-mtp-q4_K_M` | A3 `27b-q8_0` |
|---|---|---|---|
| weights | 16.52 GiB | 16.52 GiB *(same blob)* | 27.92 GiB |
| **max window @100% GPU** | **131,072** | 131,072 | **65,536** |
| resident there | 26.24 GB | 26.24 GB | 32.82 GB |
| **generation @2k** | **30.39 tok/s** | 36.58 | 19.41 |
| **prefill @35k** | **1,428 tok/s** | 767 | 1,487 |
| 20k-word turn, wall | **28.9 s** | 50.9 s | 32.0 s |
| tool gates T1–T7 | **9/10** | not run | 8/10 |
| T5 over n=11 | **11/11** | not run | 9/11 |
| deepest verified retrieval | **119,015** | not run | window-bound |
| Claude Code session | PASS 111 s | PASS 109 s | PASS 137 s |
| vision | **PASS** | not run | not run |

**Vendor claim vs measured.** The card was written to ask "whether 73.0 on Terminal-Bench
survives being three to four times slower than the model it would replace". It is **4.3×
slower**, and the answer is no — not because the model is bad, but because nothing in this
workload can pay that.

**Prediction vs measurement, the one that matters.** This card predicted "dense q4 should
land somewhere near 35–40 tok/s … an extrapolation from bandwidth, **not a measurement**".
Measured: **30.4 tok/s.** The extrapolation was 15–30% optimistic. The *better* predictor
was the dense stand-in v3 ran in its place — `qwen3.6:27b-q4_K_M` at **31.0 tok/s**, which
called it to within 2%. Same at the q8 rung: predecessor 19.5, Qwen3.8 **19.41**.

**Where it is genuinely good, and it is worth saying.** This is not a model that failed:

- **Tool calling is sound.** T4 (parallel calls) and T7 (3/3 at 53,283 tokens) both pass —
  the two gates `laguna-xs-2.1` failed, which was that model's disqualification. T5 held
  11/11 over a re-run.
- **Best window utilisation in the field.** Retrieves to 119,015 of 131,072 baked = **90.8%**,
  against north-mini's 40% and the incumbent's 56%. Its window is the smallest here and the
  most completely usable.
- **It drives Claude Code correctly**, with a tool histogram *identical* to the incumbent's
  (`Bashx4,Readx3,Editx1`) — no blind `Write`, no thrash, did not touch the test file.
- **Vision works and is accurate**, not just capability-flagged: 71.2 s on the v0 screenshot
  fixture, and it read the version string, model tag and working directory correctly.

**Two things the card got wrong about the memory side.**

*It is not naive-dense.* `full_attention_interval 4` means only **18 of 65 layers** hold full
KV, measured at **73,730 B/token** against 266,240 naive — 3.6× cheaper (§19b). Without that
it could not hold 131k on this box at all. So the "dense punishes you" intuition was right
about speed and wrong about memory.

*MTP reverses v2's finding, and is still the wrong tag.* v2 measured MTP as a straight
generation loss (129.2 → 100.6). Here it is **+20% generation** — the first time speculative
decoding has paid off anywhere in this project — bought with **−46% prefill**. For an agentic
loop that re-reads its context every turn that is a net loss on a large prompt (28.9 s vs
50.9 s at 35k tokens) and a wash on a small one (session 111 s vs 109 s).

> **Pull `qwen3.8:27b-q4_K_M`, never `qwen3.8:27b`.** The bare tag's params digest is
> byte-identical to the MTP build, so the name a person naturally types silently enables
> speculative decoding.

**And there was no MoE escape hatch.** Qwen published exactly two Qwen3.8 shapes:
`Qwen3.8-27B` (this one) and `Qwen3.8-2.4T-A95B` — Qwen3.8-Max, ~1.2 TB even at FP8, about
34× this box. The `Qwen3.8-35B-A3B` the community is asking for is **a leak, not a
release**: a commit in Alibaba's ModelScope `ms-swift` repo and an open request thread on
Hugging Face, with no weights anywhere. So on `.67`, dense was the only Qwen3.8 there was
ever going to be, and that settled it.

**Verdict: measured, not recommended.** Use it only if you specifically want Qwen3.8's
reasoning quality and will accept 111 s where the field does 54–58 s. `qwen3.8:27b-q4_K_M`
baked at `num_ctx 131072` is the rung.

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
| needle @160k depth | PASS @ 114,457 tok |
| **deepest verified retrieval** | **201,737 tok** |
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
