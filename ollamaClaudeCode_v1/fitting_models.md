# Model proposal for `192.168.100.67` — 36 GB VRAM, agentic coding

Written 2026-08-04, on the measurements in `review.md`.

> **Superseded in part, 2026-08-06.** Everything below was a *proposal* based on
> round-1 measurements and estimates. The full matrix has since been run — 11
> configurations across both servers — and the results are in **`review2.md`**, with
> a one-page summary in **`evaluation.pdf`**. Where the two disagree, `review2.md`
> is measured and this file is not.
>
> **The recommendation confirmed and sharpened:**
>
> ```shell
> curl -X POST http://192.168.100.67:11434/api/create \
>   -H "Content-Type: application/json" \
>   -d '{"model":"qwen3.6:35b-a3b-q4_K_M-agentic",
>        "from":"qwen3.6:35b-a3b-q4_K_M",
>        "parameters":{"num_ctx":262144,"temperature":0,"presence_penalty":0},
>        "stream":false}'
> ```
>
> Measured **127.2 / 131.5 tok/s**, 33.08 GB fully in VRAM, full 262144 context
> resident, all ten agentic gates PASS, needle recalled at 146957 prompt tokens.
> **7.2× the `qwen3.6:27b-q8_0` that was on the box.** This model tag now exists on
> `.67`.
>
> **What round 1 got wrong, corrected by measurement:**
>
> | this file said | measured |
> |---|---|
> | MoE KV rate unknown, est. ~0.08 GB/1k → ~150k ctx ceiling | **0.032 GB/1k → full 262144 fits at 33.09 GB** |
> | sampling not considered | **`presence_penalty 1.5` (a vendor default) costs 35% of throughput** |
> | MTP untested | **+170% on dense q8, but −25% on the MoE — wrong choice here** |
> | `num_ctx` treated as free headroom | **overflow discards half the window on Ollama 0.32.5; a 12.5% spill costs 5.3×** |
>
> The flagged caveat about the KV estimate not transferring across architectures was
> the right call — the real figure was 2.5× better than the estimate.

---

## The budget

Measured usable VRAM: **36.1 GB**. Everything must satisfy

```
weights_GB  +  KV_cache  ≤  36.0
```

with KV measured at **~0.08 GB per 1k tokens** for a dense 27B at q8. That rate is
architecture-specific — it scales with layers and KV heads, not with total
parameter count — so for the MoE candidates below it is an *estimate* until
measured. Flagged as such throughout.

## The key insight: active parameters, not total parameters

Token generation is memory-bandwidth-bound. What matters is **how many bytes get
streamed per token**, which for a mixture-of-experts model is the *active*
parameters, not the total. This is why Alex's "36B" model beat an 8B model:

| Model | Total | Active/token | Measured |
|---|---|---|---|
| `llama3.1:8b` | 8B | 8B (dense) | 86.9 tok/s |
| `qwen3.6:35b-a3b` q4_K_M | 36B | **3B** (MoE) | **89.8 tok/s** |
| `qwen3.6:27b-q8_0` | 27.8B | 27.8B (dense) | **18.1 tok/s** ← what is on the box now |

The model currently installed is the **worst possible pick** for this hardware:
dense *and* q8, so it streams ~30 GB per token. A 3B-active MoE streams ~2 GB.

---

## Ranked proposal

### 1. `qwen3.6:35b-a3b-q4_K_M` — 24 GB — **primary recommendation**

MoE, 36B total / 3B active, 256K native context, tool calling, Apache 2.0.

- **~90 tok/s already measured on this exact machine** by Alex. That is a 5×
  improvement over what is installed today.
- 12.1 GB left for KV after weights → roughly **150k context** at the measured
  rate (estimate; MoE KV differs).
- Newest Qwen generation, explicitly tuned for agentic coding and repo-level
  reasoning.
- Caveat: it is a thinking model. Send `"think": false` or budget for the
  reasoning block — this is the failure that made the q8 model look broken.

### 2. `qwen3.6:27b-q4_K_M` — 17 GB — **the reliability pick**

Dense 27B, same family we already verified end-to-end.

- **Tool use verified by us** on the q8 sibling (identical family and template):
  `stop_reason: tool_use` with correct arguments.
- Reported 77.2% on SWE-bench Verified — the strongest quality number in this
  size class.
- Dense models tend to hold up better than MoE across long multi-turn agentic
  chains, where MoE routing can drift.
- Slowest of the three at an estimated **~32 tok/s** (scaling our measured 18.1
  tok/s at 30.9 GB down to 17 GB of weights).
- 19.1 GB of KV headroom → close to the **full 256k context** in VRAM.

### 3. `qwen3-coder:30b` — 19 GB — **the no-thinking workhorse**

MoE, 30B total / ~3.3B active, 256K context, coder-specialised.

- In our `.37` sweep it emitted **zero thinking tokens** — measured, not assumed.
  For an agentic harness that is a real advantage: no reasoning block to blow the
  token budget, no `think:false` to remember.
- Expect MoE-class speed, in the same league as candidate 1.
- **Tool use untested** — must be probed before trusting it.

### 4. `devstral-small-2:24b` — ~14 GB — **the specialist**

Purpose-built for the read-edit-coordinate agent loop across multiple files.
Smaller and cheaper; useful as a second opinion or for a parallel worker. Lower
general capability than the Qwen 27/35B options.

---

## Does not fit

| Model | Size | Verdict |
|---|---|---|
| `qwen3-coder-next` (80B/3B active) q4_K_M | **52 GB** | Over budget by 16 GB. The one to want if the box ever grows — 3B active means it would fly. |
| `qwen3.6:35b-a3b-q8_0` | 39 GB | Over budget, and q8 is the wrong trade anyway. |
| `devstral-2:123b` | ~70 GB+ | Far over. |
| GLM-5.2 / Kimi K2.6 / DeepSeek V4 | 96–128 GB+ | Not in reach on this hardware. |

---

## Recommended action

Pull the top two — **41 GB total** on Alex's disk — and run the standard
verification on each:

```shell
export OLLAMA_HOST=http://192.168.100.67:11434
ollama pull qwen3.6:35b-a3b-q4_K_M      # 24 GB — primary
ollama pull qwen3.6:27b-q4_K_M          # 17 GB — reliability pick
```

Then, for each:

```shell
# 1. speed, both profiles, thinking disabled
./benchmark.sh --host 192.168.100.67 --models <model> --think-off

# 2. tool use — the gate that decides usability
#    (probe from v0/OLLAMA_PULL.md; expect stop_reason: tool_use)

# 3. context ceiling — find where it spills, as done for the q8 model
#    runtime num_ctx sweep 64k / 128k / 256k, watching size_vram vs size
```

The context sweep matters most for candidate 1: the 150k estimate above rests on
a KV rate measured on a *dense* model, and MoE may not match it.

### Then update the aliases

```shell
alias claude-ol='ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_BASE_URL=http://192.168.100.67:11434 ANTHROPIC_API_KEY="" claude --model qwen3.6:35b-a3b-q4_K_M'
```

### And free the disk

`qwen3.6:27b-q8_0` (30 GB) is dominated on every axis by candidate 2 — same
family, same quality tier, half the size, roughly double the speed. Once
candidate 2 is verified, that q8 build is dead weight. **Alex's call, not ours.**

---

## Expected outcome

| | now | after |
|---|---|---|
| Model | `qwen3.6:27b-q8_0` | `qwen3.6:35b-a3b-q4_K_M` |
| Speed | 18.1 tok/s | ~90 tok/s (**5×**) |
| Context in VRAM | 64k | ~150k (est.) |
| VRAM used | 30.9 GB | 24 GB |
| Thinking runaway | yes, unless disabled | still needs `think:false` |

---

## Caveats, stated plainly

- The ~90 tok/s for candidate 1 is **Alex's measurement, not ours** — his prompt
  was the uncapped prose one (profile L). Our profile-L numbers are the ones to
  compare it against, not profile S.
- The ~32 tok/s for candidate 2 is an **extrapolation** from our q8 measurement by
  weight-size ratio. Bandwidth scaling is a good first approximation but not exact.
- Context estimates use a KV rate measured on a dense model. **Measure, don't
  trust, for the MoE candidates.**
- Tool use is confirmed only for the Qwen 3.6 dense family and `qwen3.5:9b`.
  `qwen3-coder:30b` and `devstral` are unverified.
- SWE-bench figures are vendor/aggregator-reported, not reproduced by us.

Sources:
[qwen3.6 tags](https://ollama.com/library/qwen3.6/tags),
[qwen3-coder-next](https://ollama.com/library/qwen3-coder-next),
[Morph rankings](https://www.morphllm.com/best-ollama-models),
[InsiderLLM VRAM tiers](https://insiderllm.com/guides/best-local-coding-models-2026/),
[RockB Ollama coding models](https://baeseokjae.github.io/posts/best-ollama-models-coding-2026/).
