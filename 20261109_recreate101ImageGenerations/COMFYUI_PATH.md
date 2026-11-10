# ComfyUI local path (Track B)

Verdict: pending. The model is chosen and the decision rule is fixed. No probe has run yet.

This document is the living document for Track B. Track B recreates the Wirth image with a fully local model in ComfyUI. It does not touch the Codex chain in `pilot-niklaus-wirth/`.

## Decision (fixed 2026-11-10 22:30, before any probe)

Model: FLUX.2 [klein] 4B distilled, file `flux-2-klein-4b-fp8.safetensors`, with the text encoder `qwen_3_4b_fp4_mixed.safetensors` and `flux2-vae.safetensors`. All three files are already on the workstation. No download is necessary.

Reasons:

1. It is an edit model. It takes the previous frame as a reference image and follows the fixed prompt. This matches the Codex experiment better than img2img with a denoise strength.
2. It is small (4B, 4.1 GB file). It fits in the 8 GB VRAM of the A2000. The owner's text-to-image samples took about 11 s at 768 x 768.
3. The license is Apache 2.0. Commercial use is allowed.
4. It uses 4 distilled steps and CFG 1.0, so a generation is fast.

Quantization note: the diffusion model is fp8 (8-bit) and the text encoder is fp4 mixed (4-bit). Both are at or above the 4-bit floor. The A2000 has no fp8 hardware, so ComfyUI upcasts the fp8 weights at compute time. This costs speed, not quality.

## Candidate evaluation (checked 2026-11-10)

| Candidate | Size at the 4-bit floor | License | Fits 8 GB VRAM | Result |
| --- | --- | --- | --- | --- |
| FLUX.2 [klein] 4B distilled (fp8 file) | 4.1 GB, installed | Apache 2.0 | Yes | Selected |
| FLUX.1 Kontext [dev] GGUF | Q4_K_M 6.93 GB, Q5_K_M 8.42 GB, plus T5-XXL | FLUX.1 [dev] Non-Commercial | Tight; Q5 does not fit | Known, not fitting. Needs a custom node and about 12 GB of downloads. 12B, 20+ steps: slower than klein. |
| Qwen-Image-Edit GGUF (20B) | Q4_0 11.9 GB, Q4_K_M 13.1 GB | Apache 2.0 | No | Known, not fitting. Larger than the VRAM at the 4-bit floor. |
| Qwen-Image 2.1 (installed, int8) | 7.3 GB, installed | One guide flags non-commercial; not verified | Partly; text encoder is 6.3 GB | Known, not fitting. Text-to-image at 512 x 512, 30 steps took 60.9 s here (`llmPEG` smoke, 2026-09-22). An edit at full size would come near the limit. Recheck if klein fails the rule. |
| FLUX.1 [schnell] / [dev] img2img | 6.8 GB Q4 | schnell Apache 2.0, dev non-commercial | Tight | Known, not fitting. Img2img with denoise below 1 is partly a pixel copy. Drift then depends on the denoise value, not on the model. |
| SDXL / SD1.5 img2img | 2–7 GB | Open RAIL | Yes | Known, not fitting. Same denoise problem. Weaker faces than klein. |

Sources:

- [black-forest-labs/FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B): "Open weights available for commercial use under the Apache 2.0 license", text-to-image and multi-reference editing, 4 steps, guidance 1.0.
- [black-forest-labs/FLUX.2-klein-4b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8): Apache 2.0; vendor says "~13GB VRAM" (a vendor claim; the owner ran it in 8 GB with `--lowvram`).
- [Comfy blog: FLUX.2 klein 4B and 9B](https://blog.comfy.org/p/flux2-klein-4b-fast-local-image-editing): 4B Apache 2.0, 9B non-commercial; single- and multi-reference editing.
- [QuantStack/FLUX.1-Kontext-dev-GGUF](https://huggingface.co/QuantStack/FLUX.1-Kontext-dev-GGUF): GGUF sizes, `flux-1-dev-non-commercial-license`.
- [QuantStack/Qwen-Image-Edit-GGUF](https://huggingface.co/QuantStack/Qwen-Image-Edit-GGUF): GGUF sizes, Apache 2.0.
- ComfyUI template `image_flux2_klein_image_edit_4b_distilled.json` (package `comfyui-workflow-templates` 0.11.66): the node graph that the driver uses.

## Decision rule (fixed before the results)

1. A generation must finish in less than 240 s wall clock. The measure is the median over the 10 generations, end to end through the HTTP API (upload, queue, wait, download).
2. If the first probe takes 240 s or more, change the resolution or the steps, then probe again. Record each change here.
3. A frame is valid only if it is a PNG of the expected size, is not uniform (not black, not one color), and differs from its input. The driver stops on an invalid frame. It never books it.
4. An unreachable server or an empty read stops the chain. It is never booked as a result.

## Constant settings (the whole chain)

| Setting | Value |
| --- | --- |
| Graph | Template `image_flux2_klein_image_edit_4b_distilled`, flattened to API format |
| Input | Only the previous frame, through `LoadImage` → `ImageScaleToTotalPixels` → `VAEEncode` → `ReferenceLatent` |
| Prompt | The fixed prompt from `recreate-101/SKILL.md`, without change |
| Negative | `ConditioningZeroOut` of the prompt, with the same reference latent (as in the template) |
| Size | `ImageScaleToTotalPixels` lanczos, 0.47 MP, resolution steps 16. The 800 x 612 source becomes 800 x 608, and every later frame stays 800 x 608. |
| Latent | `EmptyFlux2LatentImage` of the same size. Denoise is 1.0: no pixels are copied. The input enters only as the reference. |
| Sampler | `euler`, `Flux2Scheduler` 4 steps, `CFGGuider` cfg 1.0 |
| Seed | Fixed seed 42 for every generation |

Deviation from the template: the template scales to 1.0 MP with `nearest-exact`. The source is 0.49 MP. An upscale to 1 MP with nearest-neighbour adds block artefacts, and it doubles the cost. The chain keeps the source size instead.

The fixed seed is a choice. With a fixed seed, the noise is the same for each generation. Only the reference frame changes. Thus the drift comes from the model, not from the noise.

## Plan

| Step | Action | Status |
| --- | --- | --- |
| 1 | Find ComfyUI, the GPU and the installed models. | Done 22:27 |
| 2 | Pre-evaluate the candidates on the web and fix the rule. | Done 22:30 |
| 3 | Start ComfyUI 0.37.0 detached on 127.0.0.1:8188. | Done 22:28 |
| 4 | Probe one generation through the API. | Open |
| 5 | Build `recreate-101/scripts/comfy-chain.sh` and a test with a fake ComfyUI. | Open |
| 6 | Run 10 generations into `pilot-comfyui-niklaus-wirth/`. | Open |
| 7 | Look at frames 0, 5 and 10. Write the results and the README section. | Open |

## Status log

| Time (2026-11-10) | Event |
| --- | --- |
| 22:27 | ComfyUI found at `/home/mpetrick/repos/ComfyUI` (0.37.0, PyTorch 2.14.0+cu130, Python 3.13.16). GPU: RTX A2000 8 GB Laptop. Not running. |
| 22:28 | Server started with the owner's flags (`--lowvram --disable-api-nodes --listen 127.0.0.1`), log in `~/.cache/recreate101-comfy/comfyui.log`. |
| 22:30 | Model chosen and rule fixed (this document). |

## Results

None yet.

## Resume here

None yet.
