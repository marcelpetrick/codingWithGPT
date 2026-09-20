# Qwen-Image-2.1 — can we run it here?

Released 2026-09-20 by the Qwen team ([blog](https://qwen.ai/blog?id=qwen-image-2.1),
[GitHub](https://github.com/QwenLM/Qwen-Image-2.1),
[HF](https://huggingface.co/Qwen/Qwen-Image-2.1)).

## Task

Find out whether Qwen-Image-2.1 is worth running on **this** machine, and if so, how.
Concretely:

1. Pick the smallest weight set that still clears the 4-bit quality floor.
2. Get a 1024×1024 text-to-image pass through the existing ComfyUI install.
3. Measure it — time per image, peak VRAM, whether it spills to RAM.
4. Then decide if the transparency (RGBA) path is reachable, since that is the one
   capability nothing else local offers.

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
| RAM | 31 GB total, **~13 GB free** right now, 33 GB swap |
| Disk | 97 GB free on `/home` |
| ComfyUI | `~/repos/ComfyUI`, v0.34.0, already running Flux Klein 4B fp8 (3.8 GB) |

### What the model wants

Comfy-Org ships pre-split weights ([Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1)):

| File | bf16 | int8 | w4a8 |
|---|---|---|---|
| `diffusion_models/qwen_image_2.1_*` | 14.23 GB | **7.26 GB** | — |
| `text_encoders/qwen3vl_8b_*` | 17.53 GB | 9.35 GB | **6.31 GB** |
| `vae/qwen_image_2.1_vae_bf16` | 0.68 GB | — | — |

Leanest usable set: **14.25 GB** on disk. No GGUF variants exist yet, and there is no
w4a8 build of the DiT — int8 is the floor on the generator side.

### Verdict: not as shipped — only through a stack of workarounds

**As the Qwen team ships it, no.** The reference setup is bf16 through `diffusers`
(`QwenImage21Pipeline`), which means ~32.4 GB of weights, native 2K output, and up to
10 reference images. That wants a 48 GB card to sit resident, or a 24 GB card (3090 /
4090) with sequential loading. This machine has 8 GB. The as-intended configuration is
off the table by a factor of three to six.

**With workarounds, probably yes — for a narrow slice of it.** Every one of these is
required, not optional:

1. int8 DiT instead of bf16 (7.26 GB instead of 14.23 GB) — halves quality headroom.
2. w4a8 text encoder instead of bf16 (6.31 GB instead of 17.53 GB) — sits exactly on
   the 4-bit floor, nothing below it is acceptable.
3. ComfyUI's sequential load, so peak VRAM is the *larger* of DiT and encoder rather
   than their sum. This is the only reason the thing fits at all.
4. Block-level offload streaming from RAM every step, because a 7.26 GB DiT against
   8.19 GB of card leaves nothing for activations.
5. Drop to 1024×1024, giving up the native-2K headline feature.
6. One reference image at most, giving up the 10-reference headline feature.

And even that stack is **RAM-limited, not VRAM-limited**: 14.25 GB of offloaded weights
against ~13 GB free means closing things first. If it touches swap the run is finished —
spill has cost ~5.3× in past measurements here.

So the honest framing: this is not "running Qwen-Image-2.1", it is running a quantised
DiT at a quarter of the intended pixel count with one reference image. Expectation per
capability:

| | |
|---|---|
| 1024×1024 text-to-image | should work, with offload — the thing to measure first |
| RGBA / transparency | same cost as above, and the one capability nothing else local offers |
| Native 2K (2048²) | no — 16k-token latent attention on a card already full |
| 10 reference images | no — KV-cache reuse is a speedup on big cards, not a fit here |
| bf16 anything | no |

Worth one evening to find out whether step 1 produces an image at all. If it does not,
the fallback is the hosted API rather than a smaller quant — there is nothing below int8
on the generator side.

### ⚠️ License

**Qwen Research License Agreement — non-commercial use only.** Section 2(b) requires a
separate commercial licence from Hangzhou Tongyi Laboratory. This is a change from
Qwen-Image 1.x, which was Apache-2.0. Research and evaluation here is fine; anything
client-facing is not.
