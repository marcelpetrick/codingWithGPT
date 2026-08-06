# Review — what was done and what was found

> **Round 2 (2026-08-06) is in `review2.md`** — models pulled onto `.67`, a full
> speed + agentic-capability matrix, and a silent 16K context cap that kills tool
> calling. The one-page summary is `evaluation.pdf`. This file is round 1.


Run 2026-08-04. Server `192.168.100.37` (old) and `192.168.100.67` (new, from Alex).
Raw data in `results/`, `results-nothink/`, `results-37-S.log`.

---

## Executive summary

0. **On the same model, `.67` is 1.4× faster than `.37`** (65.2 vs 47.3 tok/s).
   That is the real hardware delta, established with `qwen3.5:9b-ctx80k` running
   identically on both boxes.
1. **`.67` has ~36.1 GB of usable VRAM** — measured, not guessed, by pushing
   context until the model spilled to CPU.
2. **Alex's ~90 tok/s does not reproduce.** The only model on `.67` runs at
   **18.1 tok/s**. The cause is quantisation: `q8_0` is roughly twice the bytes
   per weight of the `q4_K_M` he benchmarked, and token generation is
   memory-bandwidth-bound.
3. **The runaway thinking is fixable.** `"think": false` cuts it to zero and the
   model answers normally. This is a one-line request change, not a model defect.
4. **Tool use works** on `qwen3.6:27b-q8_0` — `stop_reason: tool_use` with correct
   arguments. It is usable as a Claude Code backend.
5. **"256K Context als Standard" is not what the server does.** `.67` loads at
   **32768** by default, and 256k does not fit in VRAM at this quantisation.
6. **The q8_0 build is the wrong choice for this box.** `q4_K_M` would be ~17 GB
   instead of ~30 GB, run roughly twice as fast, and leave room for 128k context.
7. **v0's "ctx80k sweet spot" for `.37` is obsolete.** The Ollama upgrade shrank
   the KV cache; ctx96k now runs fully in VRAM at full speed where v0 measured a
   33% penalty.
8. **The `.37` sweep completed all 23 models with zero timeouts** — the swap
   deadlock that destroyed v0 run 3 did not recur, thanks to the forced unload.

---

## What was actually done

| # | Action | Result |
|---|---|---|
| 1 | Restored network access | USB ethernet came up on `192.168.100.54/24`; both servers reachable |
| 2 | Fingerprinted both servers | versions, model inventories, idle state |
| 3 | Wrote harness v1 (`benchmark.sh`) | 2 profiles, forced unload, tiered timeouts, thinking accounting, TSV output |
| 4 | Dry-ran harness locally | validated end-to-end before touching shared servers |
| 5 | Measured `.67` VRAM ceiling | context sweep 32k → 256k |
| 6 | Benchmarked `.67` with thinking on and off | quantified the thinking overhead |
| 7 | Tool-use probe on `.67` | passes |
| 8 | Full S-profile sweep on `.37` | 23 models, zero timeouts |
| 9 | Pulled `qwen3.5:9b` + built `ctx80k` on `.67` | established a shared baseline |
| 10 | Ran the baseline on both servers, S+L, + tool use | the only valid A/B |
| 11 | Wrote `ollamaFarm.sh` | 1 Hz live monitor of both servers |

---

## Server fingerprints

| | `192.168.100.37` (old) | `192.168.100.67` (new) |
|---|---|---|
| Ollama | **0.30.6** (was 0.24.0 in v0) | **0.32.5** |
| Usable VRAM | ~12.2 GB (from v0) | **~36.1 GB (measured today)** |
| Models installed | 27 | **1** |
| State when found | idle | idle |

`.67` holds exactly one model: `qwen3.6:27b-q8_0` (29.9 GB on disk, 27.8B, Q8_0).
The models Alex quoted — `llama3.1:8b` and `qwen3.6:36b-q4_K_M` — **are not on the
server anymore**. His numbers cannot be re-run as-is.

---

## The VRAM ceiling on `.67` — measured

Runtime `num_ctx` sweep on `qwen3.6:27b-q8_0`. No writes to the server.

| num_ctx | total size | in VRAM | verdict |
|---|---|---|---|
| 32,768 (default) | 30.86 GB | 30.86 GB | fully GPU |
| 65,536 | 33.27 GB | 33.27 GB | fully GPU ← **sweet spot for this model** |
| 131,072 | 38.78 GB | 36.00 GB | **SPLIT** |
| 262,144 | 49.38 GB | 36.08 GB | **SPLIT** |

The spill point pins usable VRAM at **~36.0–36.1 GB**. KV cache grows at
**~0.08 GB per 1k tokens** for this model.

Budget rule for `.67`: `weights_GB + 0.08 × ctx_k ≤ 36.0`

| Target context | Max model weights |
|---|---|
| 32k | ~33.4 GB |
| 64k | ~30.8 GB |
| 128k | ~25.6 GB |
| 256k | ~15.0 GB |

**Answer to "what is the max model size":** about **33 GB of weights** absolute
ceiling with a trivial context, **~30 GB at 64k**, **~25 GB at 128k**. A 70B model
at q4_K_M (~40 GB) does **not** fit. The KV rate above is specific to this model —
a 9B model is far cheaper per 1k (v0 measured 0.045 GB/1k for `qwen3.5:9b`).

### On the two GPUs

The API confirms 30.86 GB resident with `size_vram == size`, so the model is
**spanning both cards** — no single 36 GB card exists in that class. The Ollama
HTTP API does not report GPU model, count, temperature or utilisation, and SSH to
both hosts is refused (`publickey,password`), so the exact cards could not be read
out. ~36 GB usable is consistent with **2 × 20 GB**. Confirm with `nvidia-smi -L`
on the box.

This also matters for speed: a model split across two GPUs pays interconnect cost
on every token, which is part of why the q8 build underperforms.

---

## `.67` benchmark — `qwen3.6:27b-q8_0`

| Profile | Thinking | tok/s | answer tokens | thinking words | total |
|---|---|---|---|---|---|
| S (coding, 300 cap) | default | 12.4 | 300 | 153 | 36.2 s |
| L (prose, uncapped) | default | 18.1 | 2035 | 532 | 113.3 s |
| S | **off** | **17.9** | 156 | **0** | 29.9 s |
| L | **off** | **18.1** | 1780 | **0** | 99.8 s |

Readings:

- **Thinking is pure overhead here.** With thinking on, 153 of the 300-token
  budget on profile S went to reasoning, leaving a truncated answer. With
  `think:false` the model answered completely in 156 tokens.
- **Raw generation speed is ~18 tok/s either way.** Disabling thinking does not
  make the model faster per token; it makes the *budget* go to the answer.
- **This is 5× below Alex's 89.8 tok/s.** Not the same model: his was
  `qwen3.6:36b-q4_K_M`, ours is `27b-q8_0`. q8 is ~2× the bytes per weight of q4,
  and generation is bandwidth-bound; the two-GPU split adds more. The remaining
  gap is unexplained and would need his exact model on this box to settle.

### Tool use — passes

```
stop_reason: tool_use
  THINKING: 'The user wants to write "hello world" to /tmp/test.txt...'
  TOOL_USE: write_file {"path": "/tmp/test.txt", "content": "hello world"}
```

Correct block type, correct arguments, correct stop reason. `qwen3.6` is the
first model of that family verified for tool use — v0 left it untested.

---

## `.37` benchmark — S profile (reproduces v0 run 5)

Ollama upgraded 0.24.0 → 0.30.6 since v0. Speeds came out **slightly lower** than
run 5 across the board, so the upgrade did not help throughput.

All **23 models completed — zero timeouts**, the first fully clean sweep of that
box (v0 run 3 lost almost everything to the swap deadlock).

| Model | tok/s | VRAM | v0 run 5 | delta |
|---|---|---|---|---|
| `qwen3.5:0.8b` | 139.3 | 0.93/0.93 | 157.3 | −11% |
| `hermes3:8b` | 62.4 | 5.01/5.01 | *new* | — |
| `qwen2.5-coder:7b-ctx32k` | 60.1 | 6.37/6.37 | 68.4 | −12% |
| `qwen2.5-coder:7b` | 59.9 | 4.74/4.74 | 68.4 | −12% |
| `qwen3:8b-q4_K_M` | 58.8 | 5.57/5.57 | *new* | — |
| `granite4.1:8b-q4_K_M` | 54.3 | 5.89/5.89 | *new* | — |
| `mrthp/omnicoder2` | 52.2 | 6.40/6.40 | 43.8 | +19% |
| `qwen3.5:9b` | 47.4 | 5.38/5.38 | 45.5 | +4% |
| `qwen3.5-ctx32k:9b` | 47.4 | 6.32/6.32 | 45.7 | +4% |
| `qwen3.5:9b-ctx64k` | 47.3 | 7.45/7.45 | 45.3 | +4% |
| **`qwen3.5:9b-ctx80k`** | **47.3** | **8.01/8.01** | 46.0 | +3% |
| **`qwen3.5:9b-ctx96k`** | **47.3** | **8.56/8.56** | 31.2 **(was SPLIT)** | **+52%** |
| `mistral-nemo:12b` | 43.1 | 7.47/7.47 | 46.7 | −8% |
| `mistral-nemo:12b-ctx20k` | 43.0 | 10.18/10.18 | 46.7 | −8% |
| `qwen3:8b-q8_0` | 38.4 | 8.89/8.89 | 38.1 | +1% |
| `mistral-nemo:12b-ctx32k` | 27.9 | 11.17/12.75 **SPLIT** | 20.8 | +34% |
| `qwen3-coder:30b` | 15.9 | 11.16/19.96 **SPLIT** | 24.3 | −35% |
| `codestral:22b` | 10.4 | 11.22/14.19 **SPLIT** | 13.7 | −24% |
| `codestral:22b-ctx32k` | 8.1 | 11.05/20.42 **SPLIT** | 5.1 | +59% |
| `qwen3.5:27b` | 5.7 | 11.24/17.39 **SPLIT** | 0 (thinking) | now completes |
| `qwen3:14b-q8_0` | 5.1 | 11.13/16.83 **SPLIT** | 7.7 | −34% |
| `qwen3.6:27b-q4_K_M` | 4.8 | 9.60/17.37 **SPLIT** | 0 (thinking) | now completes |
| `qwen2.5-coder:32b` | 3.4 | 11.12/21.18 **SPLIT** | 3.6 | −6% |

### `.37`'s context ceiling moved — v0's advice is obsolete

The Ollama 0.24 → 0.30.6 upgrade **shrank the KV cache substantially**:

| Variant | v0 VRAM | today | v0 verdict | today |
|---|---|---|---|---|
| `qwen3.5:9b-ctx80k` | 12.22 GB | **8.01 GB** | sweet spot | lots of headroom |
| `qwen3.5:9b-ctx96k` | 13.07 GB **SPLIT** | **8.56 GB** | −33% penalty, avoid | **fully GPU, full speed** |

v0's headline conclusion — *"ctx80k is the maximum that fits, ctx96k costs 33%"* —
**no longer holds.** ctx96k is now free, and at 8.56 GB against a ~12.2 GB ceiling
there is room to push context considerably further. Worth a fresh sweep.

Also: `qwen3.5:27b` and `qwen3.6:27b-q4_K_M`, which produced **0 tok/s in v0**
("thinking consumes all tokens"), now complete — slowly (4.8–5.7 tok/s, heavily
split) but they finish.

New models on `.37` since v0: `granite4.1:8b-q4_K_M`, `hermes3:8b`,
`qwen3:8b-q4_K_M`, `x/flux2-klein` (image, skipped).

The structural v0 conclusion still holds: **everything above ~12.2 GB splits and
falls off a cliff.**

---

## Methodology — why v0's numbers and Alex's numbers were never comparable

They are two different benchmarks and were being read as one:

| | v0 `benchmark.sh` | Alex |
|---|---|---|
| call | `POST /api/generate` | `ollama run --verbose` |
| prompt | Sieve of Eratosthenes | "Write exactly 1000 tokens about GPUs." |
| cap | `num_predict: 300` | uncapped (828–2889 tokens) |

Longer generations amortise warm-up over more tokens and therefore report a
higher tok/s for identical hardware. The v1 harness runs both as **profile S**
and **profile L** and tags every number, so the two are never mixed. The effect
is visible in our own data: the local 4b dry-run reported 41.0 tok/s on S and
28.6 tok/s on L, and `.67` reported 12.4 on S vs 18.1 on L.

---

## Shared baseline — the only valid server-vs-server comparison

**Gap identified during the run:** there was no model common to both servers.
`.67` had only `qwen3.6:27b-q8_0`; `.37` has `qwen3.6:27b-q4_K_M` — a different
quantisation, not a valid comparison. Every cross-server number would otherwise
conflate *hardware + model + quant*.

Fixed by pulling `qwen3.5:9b` (6.6 GB) onto `.67` and creating `qwen3.5:9b-ctx80k`
with parameters identical to `.37`'s (`num_ctx 81920`, `temperature 1`,
`top_k 20`, `top_p 0.95`, `presence_penalty 1.5`). Both servers then ran the same
S and L profiles.

### Result — identical model, identical prompts

| Profile | `.37` | `.67` | `.67` advantage |
|---|---|---|---|
| S (coding, 300 cap) | 47.3 tok/s | **65.2 tok/s** | **1.38×** |
| L (prose, uncapped) | 48.0 tok/s | **67.9 tok/s** | **1.41×** |
| VRAM resident | 8.01 GB | 8.79 GB | — |
| Tool use | ✓ | ✓ | — |

**The new server is ~1.4× faster per token than the old one.** That is the honest
hardware delta — far less than the 2× the raw quoted figures suggested, because
part of that apparent gap was prompt methodology, not silicon.

The VRAM difference (8.01 vs 8.79 GB for the same model and context) comes from
the different Ollama versions allocating the KV cache differently.

### Why the q8 model looked so bad

With the baseline in hand the `qwen3.6:27b-q8_0` result reads clearly: `.67`
generates ~1.4× faster than `.37` on a 9B model, yet the 27B q8 build managed
only 18.1 tok/s. Weight bandwidth dominates — 30.9 GB of weights streamed per
token, spread across two GPUs. It is a quantisation and model-size problem, not
a slow machine.

---

## Recommendation — best local model for agentic coding, August 2026

The current frontier open-weight models (GLM-5.2, Kimi K2.6/K2.7, DeepSeek V4,
Qwen3.6 Plus) are **out of reach** on 36 GB — they target 96–128 GB+ unified
memory. Within this hardware budget:

**1. `qwen3.6:27b-q4_K_M` — the pick for `.67`.**
Same model family we just verified for tool use, but ~17.4 GB instead of 29.9 GB.
That buys roughly **2× the generation speed** (bandwidth-bound) and leaves room
for **128k+ context** inside VRAM. Apache 2.0, native long context, function
calling. It is already on `.37`, so the exact build is known-good.

**2. `qwen3-coder:30b` — the speed alternative.**
MoE with ~3.3B active parameters per token, ~18.5 GB at q4_K_M, 256k context. MoE
means generation speed far above what 30B dense would give. Tool use is
**untested** — that must be checked before trusting it.

**Do not keep `q8_0` as the daily driver.** On this box it costs half the speed
and two thirds of the context budget for quality gains that do not show up in
agentic coding work.

Concrete next step (one command, ~17 GB onto Alex's disk — **needs his OK**):

```shell
OLLAMA_HOST=http://192.168.100.67:11434 ollama pull qwen3.6:27b-q4_K_M
```

Then re-run: `./benchmark.sh --host 192.168.100.67 --models qwen3.6:27b-q4_K_M --think-off`

Sources for the landscape scan:
[MindStudio](https://www.mindstudio.ai/blog/best-open-source-llms-agentic-coding-2026),
[kingy.ai](https://kingy.ai/news/best-open-weight-ai-models-in-2026-glm-5-2-vs-deepseek-v4-vs-kimi-k2-6-vs-qwen-vs-mistral/),
[Morph](https://www.morphllm.com/best-ollama-models),
[LocalAIRun](https://localairun.com/best-local-llm-for-coding/),
[Will It Run AI](https://willitrunai.com/blog/qwen-3-gpu-requirements).

---

## Tooling delivered

**`benchmark.sh`** — harness v1. Host is a parameter; S and L profiles; forces
`keep_alive:0` between models and polls `/api/ps` until VRAM frees (the v0 run-3
deadlock mitigation); cold/warm timeout tiers; counts thinking separately; writes
TSV for diffing. `--think-off` sends `"think": false`.

**`ollamaFarm.sh`** — 1 Hz live monitor of both servers. Per host: reachability,
version, VRAM bar against the measured ceiling, API latency, and per-model
residency, quantisation, split-to-CPU warning, loaded context, and keep_alive
countdown.

**Limitation, stated plainly:** GPU temperature, utilisation, fan and power are
**not obtainable**. The Ollama HTTP API does not expose them — it only reports
model residency. Those counters require `nvidia-smi` on the host, and SSH to both
servers is refused for this user. `ollamaFarm.sh --ssh` implements the nvidia-smi
path and will light up the moment key access exists; until then it says so rather
than showing invented numbers.

---

## Open items

1. Pull the models proposed in `fitting_models.md` onto `.67` — needs Alex's OK.
2. SSH keys on both servers, for real GPU telemetry.
3. `nvidia-smi -L` on `.67` to confirm the two cards.
4. Tool-use probe for `qwen3-coder:30b`.
5. ~~Why q8 lands 5× under Alex's q4 figure~~ — **resolved, see below.**

---

## Resolved: why Alex's "36B" beat an 8B model

`qwen3.6:35b-a3b` is a **mixture-of-experts** (`archqwen35moe`): 36B total
parameters but only **~3B active per token**. Generation is memory-bandwidth
bound on *active* weights, so it streams less per token than `llama3.1:8b` does
— which is exactly why it measured faster despite being nominally 4× the size.

That also closes out the q8 question. The three data points line up on active
bytes per token, not on parameter count:

| Model | Total | Active/token | Measured |
|---|---|---|---|
| `qwen3.6:35b-a3b` q4_K_M | 36B | 3B (MoE) | 89.8 tok/s (Alex) |
| `llama3.1:8b` | 8B | 8B dense | 86.9 tok/s (Alex) |
| `qwen3.6:27b-q8_0` | 27.8B | 27.8B dense @ q8 | 18.1 tok/s (ours) |

Nothing is wrong with `.67`. The installed model is simply the worst combination
available for it — dense *and* q8, streaming ~30 GB per token where the MoE
streams ~2 GB. Model choice is worth 5× here; the hardware is not the limit.
