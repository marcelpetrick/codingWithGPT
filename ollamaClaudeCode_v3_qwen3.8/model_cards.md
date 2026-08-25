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

**What v3 measures:** tok/s against 131.4, the real `num_ctx` ceiling against 262144, and
whether Poolside's tool-calling template survives `/v1/messages`.

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

**What v3 measures:** T1–T5 first — if the tool gates fail, nothing else about this model
matters. Then tok/s, and which context number is real.

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

**What v3 measures:** whether a non-Qwen template passes T1–T5 cleanly, and what 4B-active
costs against 3B-active on tok/s.

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

**What v3 measures:** the same battery as everyone else, twice if the upgrade lands
mid-project — once before, once after.

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
