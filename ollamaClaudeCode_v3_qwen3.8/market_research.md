# What is new since v2, and what of it can run on `.67`

Survey date **2026-08-25**. The question is narrow: *which recently published open-weight
models can drive Claude Code on `192.168.100.67` at a usable speed?* Everything else —
cloud models, anything that needs a second box, anything without tool calling — is out of
scope by construction.

The constraint is the one v2 measured, not the one the datasheet claims:

> **≈35.5 GB usable**, not 40.4. At `num_ctx 131072` the dense q8_0 asked for 38.33 GB and
> only 35.56 GB stayed resident. The Ollama API exposes no VRAM field, so 40.4 was always a
> human-supplied number. — [`../ollamaClaudeCode_v2/muse_ollama.md`](../ollamaClaudeCode_v2/muse_ollama.md) §11.4

Weights are only part of that budget. The KV cache for a 256k window is tens of GB on a
dense model, which is why "18 GB of weights" and "fits in 35.5 GB" are different claims.

---

## 1. The blocker: `.67` cannot pull Qwen3.8 today

This is the first thing to settle, because it decides whether half of this project can run
at all.

```console
$ curl -s http://192.168.100.67:11434/api/version
{"version":"0.32.9"}

$ curl -sL https://registry.ollama.ai/v2/library/qwen3.8/blobs/sha256:492b2922…
{"model_format":"gguf","model_family":"qwen35",…,"renderer":"qwen3.8",
 "parser":"qwen3.5","requires":"0.32.12",…}

$ curl -s -X POST http://192.168.100.67:11434/api/pull -d '{"model":"qwen3.8:27b-q4_K_M"}'
{"status":"pulling manifest"}
{"error":"pull model manifest: 412: \nThe model you are attempting to pull requires a
 newer version of Ollama.\n\nPlease download the latest version at:\n\n\thttps://ollama.com/download\n"}
```

Every Qwen3.8 tag carries `"requires":"0.32.12"`. `.67` runs **0.32.9**. The registry
refuses the manifest with **HTTP 412** before a single byte is downloaded — so this is a
hard gate, not a "try it and see whether it works" situation.

Ollama shipped Qwen3.8 27B support in **v0.32.12 (2026-08-14)**; 0.32.13 added developer
instructions for it, 0.32.14 normalised its non-leading system messages, 0.32.15
(2026-08-19) is the current stable, and 0.33.0 (2026-08-21) is a pre-release.

**`.67` belongs to a colleague and we have no SSH to it** — every operation this project
has ever done there is `/api/pull`, `/api/create`, `/api/chat`, `/api/ps`. So the upgrade
is not ours to perform. See [`plan.md`](plan.md) §1 for what we need from you.

*Recommendation: 0.32.15, not 0.33.0.* It is stable, it clears the 0.32.12 gate, and it
carries the two Qwen3.8 message-handling fixes. 0.33.0 is a pre-release and would put a
second variable into every measurement.

**Status 2026-08-25:** the upgrade has been **requested from the owner of `.67`, and cannot
happen right now**. Stage A is therefore parked; Stage B, which needs nothing newer than
0.32.9, runs first.

## 2. Qwen3.8 — what it is

Dense **27B**, Apache-2.0, weights published **2026-08-14**. 256K native context, vision
encoder, thinking on by default and disableable per request, `reasoning_effort` and
`preserve_thinking` knobs. `model_family` in the manifest is `qwen35`, the same family
string the 27B Qwen3.6 dense tags carry.

**It is dense.** That single fact dominates everything below: the incumbent
`qwen3.6:35b-a3b` activates 3B parameters per token and reaches **131.4 tok/s**, while the
*dense* 27B q8_0 measured **18.1 tok/s** on this same box. Qwen3.8 is a smarter model in a
shape this hardware is bad at.

Vendor-reported gains over Qwen3.6-27B (Qwen's own numbers, several on in-house or modified
harnesses — treat as a direction, not a measurement):

| benchmark | Qwen3.6-27B | Qwen3.8-27B |
|---|---|---|
| Terminal-Bench 2.1 (Terminus) | 63.4 | **73.0** |
| SWE-bench Pro | 53.5 | **61.7** |
| LiveCodeBench v6 | 83.9 | **90.3** |
| OSWorld-Verified | 63.9 | **84.3** |
| DeepSWE 1.1 | 13.3 | **42.2** |

The tags that matter, with sizes read from the registry manifests rather than the web page:

| tag | weights+projector | fits ≈35.5 GB? | note |
|---|---|---|---|
| `qwen3.8:27b-q4_K_M` | **17.74 GB** | yes, with room for a large window | the working candidate |
| `qwen3.8:27b-mtp-q4_K_M` | 17.74 GB | yes | MTP head; v2 measured MTP as a *net loss* here |
| `qwen3.8:27b-q8_0` | **29.98 GB** | weights yes, window no | v2's dense q8 capped at `num_ctx 81920` |
| `qwen3.8:27b-mtp-q8_0` | 29.98 GB | same | |
| `qwen3.8:27b-mxfp8` | ~32 GB | no useful window left | |
| `qwen3.8:27b-nvfp4` | ~18 GB | needs Blackwell; `.67`'s GPUs are unknown to us | |
| `27b-bf16`, `27b-mlx*` | 56–68 GB | no | MLX is Apple-only |

### 2b. There is no Qwen3.8 MoE — checked, not assumed

The obvious escape from "dense is slow on this box" would be a Qwen3.8 in the incumbent's
shape. There isn't one. Qwen's Hugging Face org publishes exactly two Qwen3.8 model shapes:

```console
$ curl -s "https://huggingface.co/api/models?author=Qwen&search=Qwen3.8"
Qwen/Qwen3.8-27B            2,945,415 downloads     dense
Qwen/Qwen3.8-27B-FP8        3,363,900 downloads     dense
Qwen/Qwen3.8-2.4T-A95B         20,616 downloads     MoE, 2.4T total / 95B active
Qwen/Qwen3.8-2.4T-A95B-FP8     21,808 downloads     MoE
```

The MoE one is Qwen3.8-Max: ~1.2 TB at FP8, roughly **34× the usable VRAM on `.67`**.

`Qwen3.8-35B-A3B` — the variant that would actually fit and would actually be fast — is **a
leak, not a release**. It surfaced as a commit in Alibaba's ModelScope `ms-swift` repository
and as an open community request thread on `Qwen/Qwen3.8-27B`. No weights exist on Hugging
Face or in the Ollama registry (`qwen3.8-flash`, `-max`, `-moe`, `-coder`, `-plus` all
return 404 from `registry.ollama.ai`).

So on this hardware, **dense 27B is the only Qwen3.8 there will ever be**, and the project's
central question is not "which Qwen3.8 tag" but "is dense fast enough here at all".

The shipped params blob is worth reading, because two of v2's findings show up in it:

```json
{"draft_num_predict":4,"min_p":0,"presence_penalty":0,
 "repeat_penalty":1,"temperature":1,"top_k":20,"top_p":0.95}
```

`presence_penalty` is **0** — the vendor default that cost 31–35% of throughput on Qwen3.6
is gone. `draft_num_predict` is still **4**, which is exactly the setting v2 measured at
100.6 tok/s against 129.2 at 0. So an `-agentic` variant is still required, for one knob
instead of two.

## 3. The other candidates that actually fit

Sizes are registry manifest bytes; `requires` is the manifest's own minimum Ollama version.

| model | shape | q4_K_M | requires | ctx | tools | runs on 0.32.9 today |
|---|---|---|---|---|---|---|
| **`laguna-xs-2.1`** | 33B MoE, **3B active** | **20.27 GB** | 0.32.3 | 256K | yes + thinking | **yes** |
| **`north-mini-code-1.0`** | 30B MoE, **3B active** (Cohere) | **18.59 GB** | 0.30.10 | **488K** | yes + interleaved thinking | **yes** |
| **`gemma4:26b-a4b`** | 26B MoE, 4B active | 17.99 GB | 0.20.0 | 256K | yes, + vision/audio | **yes** |
| `gemma4:31b` | **dense** 31B | 19.87 GB | 0.20.0 | 256K | yes | yes, but dense |
| `nemotron3:33b` | Mamba-2 hybrid | 27.64 GB | — | — | yes | yes |
| `granite4.1:30b` | 29B | 17.49 GB | — | — | tools, **no thinking** | yes |
| `devstral-small-2` | dense 24B (Mistral) | 15.18 GB | — | 256K | yes | yes |

`north-mini-code-1.0` is the interesting one on paper: Cohere trained it specifically for
agentic software engineering across SWE-Agent, OpenCode and Terminus 2, it is 3B-active
like the incumbent, and it advertises a 488K window — larger than anything on the box
except Nemotron's 512k variant.

## 4. Excluded, and why

Stated explicitly so nobody re-litigates them next month:

| model | why not |
|---|---|
| `deepseek-v4-flash` | 284B-A13B. **~150 GB at Q4** — 4× the box. A widely-cited August roundup calls it "the one that fits in 32 GB VRAM"; that claim is wrong, and the vendor's own guide says 2×H100 or 4×RTX 5090. |
| `deepseek-v4-pro`, `glm-5.2`, `glm-5.3`, `kimi-k3`, `minimax-m3`, `qwen3.8-max` | 428B–2.8T. Not close. |
| `laguna-s-2.1` | 118B-A8B → ~65 GB at q4. |
| `ornith-1.5:35b` | 22.62 GB and it would fit, but the library card lists **no tool capability** — vision only. A Claude Code driver that cannot call tools is not a candidate. |
| `qwen3.8` bf16 / mlx / mxfp8 / nvfp4 | too large, Apple-only, or needs hardware we cannot confirm. |
| `mistral-medium-3.5` (128B), `ornith-1.5:397b` | far over budget. |

## 5. What this survey does **not** establish

- **No throughput number here is measured.** The dense-27B prediction of "roughly 2× the
  18.1 tok/s q8 figure" is an extrapolation from memory bandwidth, and v1's own dense-q4
  rows are unusable (that run spilled to CPU — `9.60/17.37 SPLIT`). It gets measured or it
  does not get claimed.
- **Ollama's capability labels are not a tool-calling test.** v2 gated every model through
  T1–T5 against `/v1/messages` for exactly this reason.
- **Free disk on `.67` is unknown.** No API exposes it, and we have no shell. The pull
  budget in [`plan.md`](plan.md) §4 is therefore a request, not a plan we can validate
  ourselves.
- **Whether `gemma4` is genuinely new** — its manifests require Ollama 0.20.0, which
  suggests the family predates v2 and only its tags were refreshed. It is listed here
  because it is untested by us, not because it is necessarily recent.

## Sources

- [ollama.com/library/qwen3.8](https://ollama.com/library/qwen3.8) · [tags](https://ollama.com/library/qwen3.8/tags)
- [ollama/ollama releases](https://github.com/ollama/ollama/releases) — v0.32.12 adds Qwen3.8 27B
- [ollama.com/library?sort=newest](https://ollama.com/library?sort=newest)
- [ollama.com/library/north-mini-code-1.0](https://ollama.com/library/north-mini-code-1.0) · [laguna-xs-2.1](https://ollama.com/library/laguna-xs-2.1/tags) · [gemma4](https://ollama.com/library/gemma4/tags) · [ornith-1.5](https://ollama.com/library/ornith-1.5)
- [Qwen 3.8 27B vs Qwen 3.6 27B (dev.to)](https://dev.to/jamilxt/qwen-38-27b-vs-qwen-36-27b-same-architecture-4-months-apart-and-a-different-kind-of-upgrade-3280) · [Qwen3.8 benchmarks, what is verified (Yotta Labs)](https://www.yottalabs.ai/post/qwen-3-8-benchmarks-what-is-verified-2026)
- [July–August 2026 open-weight roundup](https://local-ai-zone.github.io/blog/july-2026-ai-model-roundup.html) — source of the incorrect DeepSeek-V4-Flash VRAM claim
- [DeepSeek V4 Flash GGUF sizes](https://v4flash.com/gguf/) · [hardware reality check](https://www.modemguides.com/blogs/ai-infrastructure/run-deepseek-v4-flash-locally-hardware-reality-check)
- Registry manifests and config blobs read directly from `registry.ollama.ai/v2/library/*`

---

# Re-survey, 2026-08-27

The 2026-08-25 survey above was written against Ollama **0.32.9** and scoped to "what can
run on the box *today*", which at the time excluded all of Qwen3.8. Two things changed:

1. **`.67` is on 0.32.15.** The `requires` column above no longer excludes anything — every
   manifest in the library that fits now also resolves.
2. **The runtime upgrade re-ranked the field by up to +221%** (`measurements.md` §13), and
   the winners were the hybrid / Mamba-2 architectures. That changes which *shapes* are worth
   surveying, not just which models.

**Standing constraint: nothing below 4-bit.** q4_K_M is the floor. Where a model only fits
by dropping to q3 or q2, the answer is a smaller model or a smaller window — a coarser quant
is not a candidate, so sub-4-bit options are not listed below even as rejected ones.

## 6. What is new in the library since 2026-08-25

Library listing pulled 2026-08-27, newest first. Only models with a **tools** capability are
candidates — a Claude Code driver that cannot call tools is not a driver.

| model | published | verdict |
|---|---|---|
| `qwen3.8-flash-next` | ~11 h ago | **Excluded — does not fit, and is Apple-only.** See §6a |
| `glm-5.3-flash` | ~20 h ago | **Excluded — cloud-only.** The only tag is `:cloud`; no local weights are published. 18B active, 1M context, but nothing to pull |
| `granite4.2` | 2026-08-26 | **Candidate.** 30B tier at **16.50 GiB** q4_K_M, tools + thinking, 128K |
| `gemma4:31b` | updated ~16 h ago | **Candidate.** 18.50 GiB q4_K_M, 256K, vision — the dense 31B sibling of the 26b-a4b that holds the vision slot |
| `ornith-1.5` | ~1 week | Still excluded: vision only, **no tool capability** |
| `qwen3.6` | updated 2026-08-26 | Already the control; re-measured on 0.32.15 |

### 6a. `qwen3.8-flash-next` — the one that looked like the answer

It is billed as "an experimental preview of the architecture that will power Qwen4":
**125B total, 6B active** across 512 experts (10 routed + 1 shared), plus a 51B n-gram
embedding table, 256K native context extensible to 1M with YaRN, multimodal, and 62.5 on
SWE-bench Pro. A 6B-active MoE is exactly the shape this box rewards.

**It cannot run here, for two independent reasons:**

- **The only published tag is `125b-mlx` — 113 GB, MLX format.** MLX is Apple Silicon. There
  is no GGUF.
- **Even if a GGUF existed it would not fit.** 125B at q4_K_M is roughly 65–70 GB against a
  measured 35.56 GB ceiling. Getting it under would need ~q2, which is below the floor.

Worth re-checking if a GGUF of a smaller Flash-Next tier ever ships; the *shape* is right.

## 7. The candidates that fit, re-ranked by shape

Registry manifest bytes, resolved 2026-08-27. `model_family` is from each manifest's own
config blob, not from a vendor card.

| model | `model_family` | shape | q4_K_M | why it is / is not worth measuring |
|---|---|---|---|---|
| **`nemotron-cascade-2:30b`** | `nemotron_h_moe` | **Mamba-2 hybrid MoE**, 31.6B | **22.61 GiB** | **Top candidate.** The same family class as `nemotron-3.5-lightning`, which went 43.9 → 138.1 tok/s on 0.32.15 and is now the fastest generator on the box. Never surveyed — it predates the v3 field by three months and was missed |
| **`granite4.2:30b`** | `granite` | 29.3B | **16.50 GiB** | **Top candidate.** Newest thing that fits, lightest 30B-class model available, tools + thinking |
| **`gemma4:31b-it-q4_K_M`** | `gemma4` | **dense** 31.3B | 18.50 GiB | **Worth settling.** Dense, so expected slow — but it is the bigger sibling of the model holding the vision slot, and "is the 31B worth it over the 26B-a4b" is a question the vision user will ask |
| `granite4.1:30b` | `granite` | 28.9B | 16.29 GiB | Skipped in favour of 4.2, which supersedes it. Pull only if 4.2 disappoints |
| `olmo-3.1:32b` | `olmo3` | 32.2B | 18.14 GiB | Low priority. Dense, and `renderer olmo3-think` is an untested template |
| `devstral-small-2:24b` | `mistral3` | **dense** 24B | 14.14 GiB | Low priority. Dense and coding-tuned; the smallest thing here, but v3 has measured four dense models and all four were 19–31 tok/s |
| `nemotron3:33b` | — | Mamba-2 hybrid | 27.64 GiB | Superseded by `nemotron-3.5-lightning`, already measured |

**The selection rule, stated so it is falsifiable:** after ten models, *active parameters per
token* has predicted end-to-end performance on this box every single time — most sharply in
§9a of `comparison.md`, where a dense proxy called an untested Qwen3.8's speed to within 2%.
So the two hybrid MoEs go first and the dense models go last. **If `gemma4:31b` (dense) beats
either hybrid, that rule is broken and this whole ordering was wrong** — which is exactly why
one dense model is in the queue rather than none.

## 8. Excluded in this round

| model | why not |
|---|---|
| `qwen3.8-flash-next` | 125B/6B-active — right shape, but MLX-only and ~65–70 GB at q4. §6a |
| `glm-5.3-flash` | cloud-only; no local weights published |
| `laguna-s-2.1`, `deepseek-v4-*`, `glm-5.2`, `kimi-k3`, `minimax-m3`, `qwen3.8-max`, `nemotron-3-super/ultra`, `mistral-medium-3.5` | 118B–2.8T. Unchanged from §4 |
| `ornith-1.5:*` | no tool capability |
| everything below q4_K_M | standing constraint, not a size judgement |
