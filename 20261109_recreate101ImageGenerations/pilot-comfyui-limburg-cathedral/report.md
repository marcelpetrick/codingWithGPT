# Host-tool run

Status: ready.

Completed generations: 0 / 100. Refusals recorded: 0. 

Provider: comfyui-flux2-klein-4b-distilled. The notes below give the model and the settings. API cost: not applicable; no remote calls were made.

Original SHA-256: b1a6dc513137d92ead11e5c293ff094728d6e599dbb9edf63111ea039281c898. See manifest.json and usage.jsonl for frame lineage.

## ComfyUI run notes

This run is Track B on the second source: a fully local chain on Limburg Cathedral (Norbert Nagel / Wikimedia Commons, CC BY-SA 3.0; the frames use the same license, see ../examples/README.md). The living document is [COMFYUI_PATH.md](../COMFYUI_PATH.md).

| Item | Value |
| --- | --- |
| Provider label | `comfyui-flux2-klein-4b-distilled` |
| Diffusion model | FLUX.2 [klein] 4B distilled, `flux-2-klein-4b-fp8.safetensors` (fp8), SHA-256 `97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6` |
| Text encoder | `qwen_3_4b_fp4_mixed.safetensors` (fp4 mixed), SHA-256 `7ca32dcf07dfe7692945d80fff86e3a74cb83c6206b9b223ac6836b939bb85d6` |
| VAE | `flux2-vae.safetensors`, SHA-256 `d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5` |
| License | Apache 2.0 (FLUX.2 [klein] 4B). Commercial use is allowed. |
| ComfyUI | 0.37.0, commit `43a41b5c`, PyTorch 2.14.0+cu130, Python 3.13.16, flags `--lowvram --preview-method none --disable-api-nodes` |
| GPU | NVIDIA RTX A2000 8 GB Laptop (no fp8 hardware; fp8 weights are upcast to bf16) |
| Graph | `recreate-101/references/comfy-flux2-klein-edit.json` (from the template `image_flux2_klein_image_edit_4b_distilled`) |
| Driver | `recreate-101/scripts/comfy-chain.mjs` |
| Input | Only the previous frame, as a reference latent |
| Prompt | The fixed prompt from `recreate-101/SKILL.md` |
| Size | lanczos to 0.47 MP, multiple of 16 (the size follows the source aspect ratio; see frame 1) |
| Sampler | euler, `Flux2Scheduler` 4 steps, CFG 1.0, denoise 1.0 (empty latent; no pixel copy) |
| Seed | 42, fixed for every generation |

Per-generation seconds are in `comfy.jsonl` (`seconds`, end to end through the API, from `next` to the downloaded PNG). The results section of `COMFYUI_PATH.md` summarises them.
