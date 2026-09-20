# Qwen-Image-2.1 — can we run it here?

Released 2026-09-20 by the Qwen team ([blog](https://qwen.ai/blog?id=qwen-image-2.1),
[GitHub](https://github.com/QwenLM/Qwen-Image-2.1),
[HF](https://huggingface.co/Qwen/Qwen-Image-2.1)).

## Task

Find out whether Qwen-Image-2.1 is worth running on **this** machine, and if so, how.
Concretely:

1. ~~Establish whether the tooling here can load it at all.~~ Answered below: ComfyUI
   v0.37.0 supports it natively.
2. Pick the smallest weight set that still clears the 4-bit quality floor. Answered:
   int8 DiT + w4a8 text encoder + bf16 VAE, 14.25 GB.
3. Pull those three files and get a 1024×1024 text-to-image pass through ComfyUI.
4. Measure it — time per image, peak VRAM, whether it spills to RAM.
5. Then reach for the transparency (RGBA) path, since that is the one capability
   nothing else local offers.

## What the model can do

1. **Text-to-image and image editing in one checkpoint** — no separate edit model.
2. **Native transparency**: generates true RGBA layers straight from a prompt, absorbing
   the old separate Qwen-Image-Layered model.
3. **Edits transparent images directly** — change a subject's expression or replace text
   inside a layer while the alpha background survives.
4. **Extracts subjects from ordinary photos** as RGBA cut-outs.
5. **Up to 10 reference images** composed into one scene (group portraits, try-on, interiors).
6. **Local edits by annotation** — coloured circles, painted regions, or a separate mask
   image when you need the original left unobscured.
7. **Identity and product fidelity**: faces stay recognisable across edits, product text,
   texture and shape are preserved.
8. **Strong typography** — type style and layout are treated as part of the composition,
   not just glyph content.
9. **Native 2K output**: 2048×2048, plus 2400×1792, 1792×2400, 2752×1536, 1536×2752.
10. **Wider task coverage**: panoramas, infographics, storyboards from a character sheet.

## What it is made of

| Part | Detail |
|---|---|
| Visual generator | 32-layer single-stream DiT, **7B params** |
| Text encoder | **Qwen3-VL 8B** — nearly as big as the generator |
| VAE | 64-channel RGBA, 16× spatial compression |
| Speed trick | mixed-granularity attention + prefix KV cache reuse for reference images |

The 7B headline number is only the DiT. The full bf16 repo is **33.1 GB**.

## Infrastructure

### What is already here

| | |
|---|---|
| GPU | RTX A2000 **8 GB** Laptop (Ampere, cc 8.6), driver 610.57.04 |
| RAM | 31 GB total, **~21 GB available**, 33 GB swap |
| Disk | 97 GB free on `/home` |
| ComfyUI | `~/repos/ComfyUI`, **v0.37.0**, venv on Python 3.13.14 + torch 2.14.0+cu130 |
| Proven on this box | Flux Klein 4B fp8 (3.8 GB), 768×768, 4 steps, ~11 s/image |

### What the model wants

Comfy-Org ships pre-split weights ([Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1)):

| File | bf16 | int8 | w4a8 |
|---|---|---|---|
| `diffusion_models/qwen_image_2.1_*` | 14.23 GB | **7.26 GB** | — |
| `text_encoders/qwen3vl_8b_*` | 17.53 GB | 9.35 GB | **6.31 GB** |
| `vae/qwen_image_2.1_vae_bf16` | 0.68 GB | — | — |

Leanest usable set: **14.25 GB** on disk. No GGUF variants exist yet, and there is no
w4a8 build of the DiT — int8 is the floor on the generator side.

### Verdict: yes — quantised, but the workarounds are supported settings

The first pass at this concluded "not as shipped, only through a stack of workarounds".
Two things changed that, and both are worth writing down.

**ComfyUI v0.37.0 supports Qwen-Image-2.1 natively.** This is not a community port or a
custom node. Upstream carries a dedicated DiT implementation, text encoder, latent format
and purpose-built nodes:

| Piece | Where |
|---|---|
| DiT | `comfy/ldm/qwen_image21/model.py`, `QwenImage21Transformer2DModel` |
| Model config | `comfy/supported_models.py`, `class QwenImage21` |
| Text encoder | `comfy/text_encoders/qwen_image21.py` on top of `qwen3vl.py` |
| Latent | `latent_formats.QwenImage21` — 64 channels, 16× downscale, as the blog says |
| Nodes | `comfy_extras/nodes_qwen.py` |

The nodes cover the whole feature set: `TextEncodeQwenImage21` (t2i, plus up to 16
reference image slots), `TextEncodeQwenImageEdit` / `…EditPlus`, `QwenImage21Cache`, and
`EmptyQwenImageLayeredLatentImage` for the transparency path.

**RAM is no longer the binding constraint.** With the browser closed there is ~21 GB
available against 14.25 GB of weights. The earlier worry — that offloaded weights would
spill into swap and cost the 5.3× seen in past measurements — is off the table with
roughly 7 GB to spare.

**The memory pressure is a designed-for case, not an accident.** `QwenImage21Cache`
exists precisely for this machine's shape. Its `device` option is documented upstream as
"auto uses spare VRAM, then RAM. cpu (RAM) is prefetched behind compute and costs little
speed", and `dtype` offers int8 ("halves the cache at about bf16 accuracy") and int4
("quarters it but roughly doubles the per-step error"). So the KV cache that makes
multi-reference editing expensive can be pushed to RAM deliberately, prefetched, at
little cost.

So the corrected reading: quantisation is still mandatory, because a bf16 DiT of 14.23 GB
will never fit an 8 GB card. But int8 weights, sequential loading, `--lowvram` block
offload and a CPU-side KV cache are all first-class options in the tool, not hacks around
it. That is a different claim from the one made above.

Still honest about the limits:

| | |
|---|---|
| 1024×1024 text-to-image | expected to work — the thing to measure first |
| RGBA / transparency | reachable; `EmptyQwenImageLayeredLatentImage` defaults to 640×640 |
| A few reference images | plausible with the KV cache on CPU |
| Native 2K (2048²) | fits in memory, but degrades into swap on a long run — 1024² is the practical ceiling |
| All 10 reference images | untested |
| bf16 anything | no |

### How the pieces get loaded

One wiring detail that is easy to get wrong: **`CLIPLoader` has no `qwen_image21` type.**
You pick `qwen_image`, and ComfyUI detects the Qwen3-VL-8B weights and routes them to the
2.1 encoder itself (`comfy/sd.py`: *"Qwen-Image 2.1: full Qwen3-VL-8B, last hidden state,
image slots spliced by the DiT"*). Picking `qwen_image` with a 2.1 text encoder file is
therefore correct, not a downgrade to 1.x.

Files go to the usual places under `~/repos/ComfyUI/models/`:

| File | Destination |
|---|---|
| `qwen_image_2.1_int8_convrot.safetensors` | `models/diffusion_models/` |
| `qwen3vl_8b_w4a8.safetensors` | `models/text_encoders/` |
| `qwen_image_2.1_vae_bf16.safetensors` | `models/vae/` |

Launch stays what already works here: `venv/bin/python main.py --lowvram`.

### ⚠️ License

**Qwen Research License Agreement — non-commercial use only.** Section 2(b) requires a
separate commercial licence from Hangzhou Tongyi Laboratory. This is a change from
Qwen-Image 1.x, which was Apache-2.0. Research and evaluation here is fine; anything
client-facing is not.

## What is configured here

Everything below is set up and committed. Nothing needs picking again.

### Files downloaded (14.25 GB, into the ComfyUI checkout)

| File | Size | Landed in |
|---|---|---|
| `qwen_image_2.1_int8_convrot.safetensors` | 7.26 GB | `~/repos/ComfyUI/models/diffusion_models/` |
| `qwen3vl_8b_w4a8.safetensors` | 6.31 GB | `~/repos/ComfyUI/models/text_encoders/` |
| `qwen_image_2.1_vae_bf16.safetensors` | 0.68 GB | `~/repos/ComfyUI/models/vae/` |

All three come from [Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1),
which is the pre-split repack. The original `Qwen/Qwen-Image-2.1` repo is the bf16
original at 33.1 GB and is the wrong thing to download for this machine.

### Settings, and why each one

| Setting | Value | Reason |
|---|---|---|
| ComfyUI launch | `--lowvram` | Splits the model and streams blocks; the DiT does not fit whole. |
| `UNETLoader` weight_dtype | `default` | The quantisation is baked into the file. Forcing fp8 here would break it. |
| `CLIPLoader` type | `qwen_image` | There is no `qwen_image21` option. ComfyUI sees Qwen3-VL-8B weights and routes to the 2.1 encoder by itself. |
| `QwenImage21Cache` device | `cpu` | Keeps the KV cache out of VRAM. Upstream says it is prefetched behind compute, so it costs little speed. |
| `QwenImage21Cache` dtype | `int8` | Halves the cache "at about bf16 accuracy". `int4` roughly doubles per-step error, so it stays off. |
| Sampler / scheduler | `euler` / `simple` | Standard for a flow-matching DiT. |
| Shift | 0.69 | Comes from the model config, not a node. Do not add a ModelSampling node. |
| Steps / CFG | 30 / 3.5 | Starting point; the reference `diffusers` snippet uses 40 steps. |
| Resolution | 1024 | `TextEncodeQwenImage21` emits its own 64-channel latent at `resolution/16`, so no EmptyLatent node is wired in. |

### Running it

```bash
cd ~/repos/codingWithGPT/qwenImage2.1
./serve.sh                    # starts ComfyUI if it is not already up
./run_showcase.py             # all five prompts, writes images/ + images/timings.json
./run_showcase.py --only 01-visor-reflection --steps 20   # one, faster
```

## What actually bites on this hardware

In plain terms, these are the things that cause trouble here.

### 1. `/tmp` is a RAM disk — do not download models there

`/tmp` on this machine is `tmpfs`, 16 GB, held in RAM. Staging 14.25 GB of weights there
would eat the RAM the model needs for offload, and would run out of space anyway. The
first download attempt did exactly this and had to be killed. Weights go to `/home`,
which is real disk with 97 GB free.

### 2. The DiT very nearly fills the card by itself

The int8 DiT is 7.26 GB. The card has 8.22 GB, of which ~8.07 GB is free. That leaves
about 800 MB for activations, attention, and the VAE decode — which is not enough, so
ComfyUI keeps part of the model in RAM and streams it in every step. That streaming is
the main cost of running this model here. It is the difference between "works" and
"works fast", and there is no setting that removes it on 8 GB.

### 3. ComfyUI rates this model as unusually memory-hungry

Each model in ComfyUI carries a `memory_usage_factor` that says how much working memory
it needs relative to its weights. Qwen-Image-2.1 is set to **6.0**. For comparison:

| Model | Factor |
|---|---|
| SDXL | 0.8 |
| SD 1.5 | 1.0 |
| Flux | 3.1 |
| LTXV (video) | 5.5 |
| **Qwen-Image-2.1** | **6.0** |

It is rated heavier than Flux by nearly 2×, and heavier than a video model. That is a
direct statement from the tooling that this is a demanding model to run, quite apart
from how big the weights are.

### 4. fp8 does not work on this GPU — but int8 does

The A2000 is Ampere (`sm_86`). Checked directly against ComfyUI's own capability probe:

```
supports_int8_compute:  True
supports_fp8_compute:   False
supports_nvfp4_compute: False
supports_mxfp8_compute: False
disabled quant formats: float8_e4m3fn, float8_e5m2, mxfp8, nvfp4
```

This is the one genuinely good piece of news, and it is why the file choice above
matters. Ampere has real INT8 tensor cores, so `int8_convrot` and `asym_w4a8_int8` run
on hardware. fp8 — the format the Flux Klein setup on this machine uses — is emulated.
Picking the int8 build was not just the smallest option, it is the fast one here.

### 5. Things that are simply out of reach

- **All 10 reference images.** The KV cache can be pushed to RAM, which helps, but the
  sequence length still has to be attended to on the GPU. Untested.
- **bf16 anything.** The bf16 DiT alone is 14.23 GB, nearly twice the card.

## Measured results

Everything below was measured on this machine, not estimated.

### Five showcase images, 1024×1024, 30 steps

| | |
|---|---|
| Total | **20.5 min** for five images |
| Per image | **246 s** (4.1 min) |
| Per step | **8.2 s** |
| Peak VRAM | **7689 MiB** of 8192 (94%) |

Settings: euler / simple, cfg 3.5, shift 0.69 from the model config, int8 DiT,
w4a8 text encoder, KV cache on CPU at int8. Images are in `images/`, timings in
`images/timings.json`, prompts in `prompts.json`.

The model delivered on the claims that could be checked here:

- **Typography is as good as advertised.** `QWEN IMAGE 2.1` and `MODULE 07 / EVA ACCESS`
  came out stencilled, legible and correctly wrapped around the curve of the hull. The
  poster placed five separate strings at three sizes without garbling any of them. This
  is the thing most open image models get wrong, and it got it right twice.
- **The visor test passed.** Both the planet limb and the service module appear in the
  curved glass with plausible mirror distortion, alongside breath fog and skin texture.
- **Fine texture holds up.** Individual thread crossings in the glove weave, distinct
  frost crystals on the rail.

### Two measurements that corrected earlier assumptions

**1. int8 did not visibly cost tonal quality.** The nebula gradients show no banding.
The concern that a coarse quantisation would mush smooth gradients did not show up in
the one test aimed at it.

**2. VRAM is spent on weights, not activations.** Peak VRAM barely moves with resolution:

| Resolution | Steps | Peak VRAM | s/step |
|---|---|---|---|
| 512² | 8 | 7551 MiB | 1.9 |
| 1024² | 30 | 7689 MiB | 8.2 |
| 2048² | 8 | **7689 MiB** | **54** |

ComfyUI fills the card with as much model as fits and streams the rest, so the card
reads ~94% full no matter what is being generated. **Resolution costs time, not memory.**

### Correction: native 2K runs

This file said twice that 2048×2048 was "not happening" and "out of reach", reasoning
that four times the latent tokens would not fit. That was wrong, and the table above is
why: a 2048² generation completed with *exactly* the same peak VRAM as 1024². Memory was
never the barrier.

What 2K costs is time. An 8-step 2K run averaged 54 s/step against 8.2 s/step at
1024² — about 6.6× for 4× the pixels, the quadratic part of attention showing but not
fatal. On that figure a 30-step 2K image looked like roughly 27 minutes.

**That extrapolation was wrong, and the way it was wrong is the interesting part.** A
30-step 2K run does not hold 54 s/step. It degrades as it goes:

| Step | s/step |
|---|---|
| 14 | 91 |
| 15 | 127 |
| 16 | 174 |
| 18 | 174 |
| 19 | 143 |

Thirty-one minutes in it had managed 19 of 30 steps, was still slowing, and was
abandoned there. Meanwhile VRAM in use had *fallen* from 7689 MiB to 6221 MiB and swap
had grown to 5.0 GB. That combination is the tell: as host RAM tightened, ComfyUI kept
shifting weights out of VRAM, so each step had more to stream, which made the next step
slower still. This is the spill spiral, entered gradually rather than as one OOM.

Two practical lessons. **Per-step cost at 2K is not a constant**, so measuring a short
run and multiplying gives a number that is far too optimistic. And **a second job
queued behind the first is enough to start it**, because the queued process holds RAM
the running one needed.

Still unestablished: at 8 steps the 2K result came back badly undercooked — a near-blank
hull with no lettering. The model config tunes its scheduler shift at 1024² ("base 0.5 @
256 tokens, max 0.9 @ 8192") and a 2048² latent is 16384 tokens, past the top of that
range. **2K fits in memory; 2K at usable quality has not been reached on this machine.**
1024² is the practical ceiling here.
