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
