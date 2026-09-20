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
| Native 2K (2048²) | still unlikely — 16k-token latent attention on a card already full |
| All 10 reference images | unlikely at any useful speed |
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
