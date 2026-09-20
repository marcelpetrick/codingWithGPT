# Qwen-Image-2.1 on an 8 GB RTX A2000 — model, runtime, measurements

Everything here was measured on this machine between 2026-09-20 17:57 and 20:4x.
Numbers are from `nvidia-smi`, `/proc/meminfo`, ComfyUI's own logs and
`images/timings*.json`. Nothing is estimated unless it says so.

---

## 1. The model

Released 2026-09-20 ([blog](https://qwen.ai/blog?id=qwen-image-2.1),
[GitHub](https://github.com/QwenLM/Qwen-Image-2.1),
[HF](https://huggingface.co/Qwen/Qwen-Image-2.1)).

| Component | Detail |
|---|---|
| Visual generator | 32-layer **single-stream DiT, 7B params** |
| Text encoder | **Qwen3-VL 8B** — nearly as large as the generator |
| VAE | **64-channel RGBA**, 16× spatial compression |
| Attention | mixed-granularity: token-level causal mask for text, chunk-level for images |
| Efficiency | prefix KV-cache reuse — reference images encoded once, not per step |
| Scheduler shift | **0.69**, from the model config (not a node); tuned at 1024² |
| Licence | **Qwen Research — non-commercial only** (1.x was Apache-2.0) |
| Full bf16 repo | **33.1 GB** |

The "7B" headline covers only the DiT. Encoder + DiT + VAE in bf16 is ~32.4 GB.

### What it can do

Unified generation *and* editing in one checkpoint; native RGBA transparency
(absorbing the separate Qwen-Image-Layered model from Dec 2025); subject
extraction from ordinary photos as alpha layers; up to 10 reference images;
local edits via circles, painted annotations or a separate mask; native 2K
(2048² plus 2400×1792, 1792×2400, 2752×1536, 1536×2752); strong typography.

---

## 2. The runtime

### Hardware

| | |
|---|---|
| GPU | NVIDIA RTX A2000 8GB Laptop, Ampere **sm_86**, driver 610.57.04 |
| VRAM | 8192 MiB (8.07 GB free at idle) |
| RAM | 31 GB, 33 GB swap |
| Disk | `/home` on NVMe, 97 GB free |

### Software

| | |
|---|---|
| ComfyUI | **v0.37.0** (native Qwen-Image-2.1 support, not a community port) |
| Python / torch | 3.13.14 / **2.14.0+cu130** |
| Launch flag | `--lowvram` |

Upstream carries `comfy/ldm/qwen_image21/model.py`, `class QwenImage21` in
`supported_models.py`, `comfy/text_encoders/qwen_image21.py` over `qwen3vl.py`,
`latent_formats.QwenImage21` (64 channels, 16× — matching the blog), and the
nodes `TextEncodeQwenImage21`, `TextEncodeQwenImageEdit(Plus)`,
`QwenImage21Cache`, `EmptyQwenImageLayeredLatentImage`.

### Quantisation support, measured on this GPU

```
supports_int8_compute:  True      <- the format used here
supports_fp8_compute:   False
supports_nvfp4_compute: False
supports_mxfp8_compute: False
disabled quant formats: float8_e4m3fn, float8_e5m2, mxfp8, nvfp4
```

**This is the single most useful fact for this hardware.** Ampere has real INT8
tensor cores, so `int8_convrot` and `asym_w4a8_int8` execute on hardware. fp8 —
the format the Flux Klein setup on this same machine uses — is *not* supported
and is emulated. The int8 build was not merely the smallest option; it is the
fast one here.

### Weights actually used (14.25 GB)

| File | Size | Location |
|---|---|---|
| `qwen_image_2.1_int8_convrot.safetensors` | 7.26 GB | `models/diffusion_models/` |
| `qwen3vl_8b_w4a8.safetensors` | 6.31 GB | `models/text_encoders/` |
| `qwen_image_2.1_vae_bf16.safetensors` | 0.68 GB | `models/vae/` |

From [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1).
No GGUF variants exist; there is no w4a8 DiT, so **int8 is the floor on the
generator side**. Sustained download rate was ~14 MB/s (a 10-second probe read
29.6 MB/s and was not representative).

### Settings

| Setting | Value | Why |
|---|---|---|
| `UNETLoader` weight_dtype | `default` | Quantisation is baked into the file; forcing fp8 breaks it |
| `CLIPLoader` type | `qwen_image` | **No `qwen_image21` option exists.** ComfyUI detects Qwen3-VL-8B weights and routes to the 2.1 encoder itself |
| `QwenImage21Cache` device | `cpu` | Keeps the KV cache out of VRAM; prefetched behind compute |
| `QwenImage21Cache` dtype | `int8` | Halves the cache at ~bf16 accuracy; int4 doubles per-step error |
| Sampler / scheduler | `euler` / `simple` | Standard for a flow-matching DiT |
| Steps / CFG | 30 / 3.5 | Reference `diffusers` snippet uses 40 |

`TextEncodeQwenImage21` emits its own 64-channel latent at `resolution/16`, so
no EmptyLatent node is wired in.

---

## 3. Measurements

All times are **server-side execution** (`execution_start` → `execution_success`),
excluding queue wait.

| Image | Res | Steps | Time | s/step | Peak VRAM | Machine state |
|---|---|---|---|---|---|---|
| smoke (visor) | 512² | 8 | 15.3 s | **1.91** | 7551 MiB | warm |
| 01-visor-reflection | 1024² | 30 | 243.1 s | 8.10 | 7655 MiB | warm |
| 05-nebula-scale | 1024² | 30 | 246.9 s | 8.23 | 7689 MiB | warm |
| 04-mission-poster | 1024² | 30 | 247.2 s | 8.24 | 7657 MiB | warm |
| 02-hull-typography | 1024² | 30 | 247.3 s | 8.24 | 7367 MiB | warm |
| 03-glove-texture | 1024² | 30 | 247.4 s | 8.25 | 7335 MiB | warm |
| bavaria-02-goldenhour | 1024² | 30 | 398.2 s | 13.27 | 7757 MiB | cache re-warming |
| 2K probe (hull) | 2048² | 8 | 433.0 s | **54.16** | 7689 MiB | warm |
| bavaria-01-daylight | 1024² | 30 | 663.0 s | **22.10** | 7757 MiB | cold, post-spill |
| 2K @ 30 steps | 2048² | 19/30 | *abandoned at 31:19* | 91 → 174 | 6221 MiB | spiralling |
| mp-01-wiesn | 1024² | 30 | 237.1 s | 7.90 | 7567 MiB | warm |

### 3.1 Wall clock per image

```
smoke  01-visor        15.3s █
mp-01-wiesn           237.1s ████████████████
01-visor-reflection   243.1s █████████████████
05-nebula-scale       246.9s █████████████████
04-mission-poster     247.2s █████████████████
02-hull-typography    247.3s █████████████████
03-glove-texture      247.4s █████████████████
bavaria-02-golden     398.2s ████████████████████████████
2K probe (hull)       433.0s ██████████████████████████████
bavaria-01-daylight   663.0s ██████████████████████████████████████████████
                     └────────────────────────────────────────────┘
                     0                                          663s

ABANDONED
2K @ 30 steps        >1879s ███████████████████████████████████████████████▶
                            killed at step 19/30, still slowing
```

### 3.2 Cost per step by resolution

```
 512²    1.91 s/step  ██
1024²    8.21 s/step  ████████
2048²   54.16 s/step  ██████████████████████████████████████████████████
                      └────────────────────────────────────────────────┘
                      0                                             55 s
```

### 3.3 Cost per step by machine state — identical work

```
warm, 22 GB cache, no swap      8.2 s/step  ████████
cache re-warming, 5.7 GB swap  13.3 s/step  █████████████
cold, cache evicted, swapping  22.1 s/step  ██████████████████████
                                            └────────────────────┘
                                            0                  22 s
```

The same 1024²/30-step job, varying only by what the machine did beforehand.

### 3.4 2K degradation over a single run

```
step 14   91 s/step  ██████████████████████████
step 15  127 s/step  ████████████████████████████████████
step 16  174 s/step  ██████████████████████████████████████████████████
step 18  174 s/step  ██████████████████████████████████████████████████
step 19  143 s/step  █████████████████████████████████████████
                     └────────────────────────────────────────────────┘
                     0                                            175 s
```

Against 54 s/step measured on the 8-step 2K probe. The run never reached a
steady rate; it was abandoned at step 19.


---

## 4. What the measurements mean

### 4.1 Content is free; pixels and steps are not

The five showcase images span wildly different subjects and landed within **2%**
of each other (243.1–247.4 s). Cost is set by resolution and step count alone.

### 4.2 VRAM holds weights, not activations

| Resolution | Peak VRAM |
|---|---|
| 512² | 7551 MiB |
| 1024² | 7689 MiB |
| 2048² | 7689 MiB |

Peak barely moves with resolution. ComfyUI fills the card with as much model as
fits and streams the rest, so it reads ~94% full regardless of what is being
generated. **Resolution costs time, not memory.** This disproved an earlier
assumption here that 2K would not fit.

### 4.3 Resolution scaling turns superlinear past 1024²

| Step up | Pixels | Time | Behaviour |
|---|---|---|---|
| 512² → 1024² | 4× | 4.3× | ~linear |
| 1024² → 2048² | 4× | 6.6× | superlinear — quadratic attention appearing |

### 4.4 The page cache is the dominant runtime variable

Identical model, settings and resolution; only the machine's prior state differs:

| s/step | Page cache | Swap |
|---|---|---|
| **8.2** | 22 GB | 0 |
| **13.3** | partly re-warmed | 5.7 GB |
| **22.1** | 5 GB (evicted) | 5.7 GB |

**2.7× spread on identical work.** A 1024² image is ~4 minutes on a quiet
machine and ~11 minutes on one that has just been thrashed.

### 4.5 2K fits but spirals into swap

A 30-step 2K run does not hold its 54 s/step. It degrades:

| Step | s/step |
|---|---|
| 14 | 91 |
| 15 | 127 |
| 16 | 174 |
| 18 | 174 |
| 19 | 143 |

After 31 minutes it had managed 19 of 30 steps and was still slowing, so it was
abandoned. VRAM in use had *fallen* from 7689 to 6221 MiB while swap grew to
5.0 GB: as host RAM tightened, ComfyUI shifted more weight out of VRAM, so each
step had more to stream, making the next slower again. **A spill spiral entered
gradually rather than as a single OOM** — which is why it never errored.

A second job queued behind the first is enough to trigger this, since the queued
process holds RAM the running one needs.

### 4.6 int8 did not visibly cost tonal quality

The nebula gradients show no banding. The concern that coarse quantisation would
mush smooth gradients did not appear in the one test aimed at it.

---

## 5. Verdict

**1024² at ~4 minutes per image is the practical operating point.** It is
reliable, it uses the quantisation format this GPU accelerates in hardware, and
quality on the model's advertised strengths — typography above all — held up.

| Capability | Status here |
|---|---|
| 1024² text-to-image | **works well**, ~246 s at 30 steps |
| Typography | **excellent** — multi-line, multi-size, all legible |
| RGBA / transparency | reachable; untested |
| Native 2K | fits in memory, but degrades into swap on a long run |
| 10 reference images | untested |
| bf16 anything | no — the bf16 DiT alone is 14.23 GB |

---

## 6. Corrections made while measuring

Recorded because the errors are instructive, not to pad the log.

1. **"Not runnable as shipped, only via workarounds."** Wrong emphasis — ComfyUI
   v0.37.0 supports the model natively and the quantised paths are first-class
   options, not hacks.
2. **"Native 2K is out of reach."** Wrong — it fits in memory at exactly the
   1024² peak. The barrier is time and swap, not capacity.
3. **"~27 minutes for a 30-step 2K image."** Wrong — extrapolated from a short
   run that never built enough memory pressure to show the degradation. Real
   behaviour is >60 minutes and non-convergent.
4. **"bavaria-01 took 2145 s."** Wrong — the runner timed submit→result and so
   counted 25 minutes of queue wait as render time. Actual 663 s. Fixed in
   `run_showcase.py`; `timings.json` now carries `queued_seconds` separately.
5. **"5.0 s/step, the fastest yet."** Wrong — that was the first two steps before
   the rate settled to the usual 8.0 s/step.
