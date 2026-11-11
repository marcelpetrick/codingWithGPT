# ComfyUI local path (Track B)

Verdict: the local path works and passes the rule by a wide margin. FLUX.2 [klein] 4B distilled made 10 generations with a median of 15.2 s each (range 11.2–15.3 s), against a limit of 240 s. Peak GPU memory was 7618 MiB of 8192 MiB. The frames drift clearly: saturation, contrast and sharpening grow, skin turns red, and a fine texture appears. The composition stays the same.

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
3. A frame is valid only if it is a PNG, is not uniform (not black, not one color), and differs from its input. The driver stops on an invalid frame. It never books it. (Review F9, 2026-11-10: the size check was in this rule but not in the code. The rule now matches the code; all frames were checked at the end with `identify`.)
4. An unreachable server or an empty read stops the chain. It is never booked as a result.

## Constant settings (the whole chain)

| Setting | Value |
| --- | --- |
| Graph | Template `image_flux2_klein_image_edit_4b_distilled`, flattened to API format |
| Input | Only the previous frame, through `LoadImage` → `ImageScaleToTotalPixels` → `VAEEncode` → `ReferenceLatent` |
| Prompt | The run's prompt: `manifest.json` field `prompt` if present (prompt v2 runs), else the fixed prompt from `recreate-101/SKILL.md` (v1) |
| Negative | `ConditioningZeroOut` of the prompt, with the same reference latent (as in the template) |
| Size | `ImageScaleToTotalPixels` lanczos, 0.47 MP, resolution steps 16. The 800 x 612 Wirth source becomes 800 x 608, and every later frame keeps the size. Other sources get their own size from their aspect ratio. |
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
| 4 | Probe one generation through the API. | Done 22:31, 15.2 s |
| 5 | Build `recreate-101/scripts/comfy-chain.mjs` and a test with a fake ComfyUI. | Done 22:33, `a3f488f`, `71701a5` |
| 6 | Run 10 generations into `pilot-comfyui-niklaus-wirth/`. | Done 22:37, `b3c625e` |
| 7 | Look at frames 0, 5 and 10. Write the results and the README section. | Done 22:42 |
| 8 | Extend the chain to 100 generations (about 25 min). | Done 2026-11-10 23:23 (owner asked for the comparison); Limburg and Turing v1/v2 added |

## Status log

| Time (2026-11-10) | Event |
| --- | --- |
| 22:27 | ComfyUI found at `/home/mpetrick/repos/ComfyUI` (0.37.0, PyTorch 2.14.0+cu130, Python 3.13.16). GPU: RTX A2000 8 GB Laptop. Not running. |
| 22:28 | Server started with the owner's flags (`--lowvram --disable-api-nodes --listen 127.0.0.1`), log in `~/.cache/recreate101-comfy/comfyui.log`. |
| 22:30 | Model chosen and rule fixed (this document, `e3f9e6b`). |
| 22:31 | Probe in `~/.cache/recreate101-comfy/probe/`: 15.2 s end to end, 14.86 s in ComfyUI, model load included. Output 800 x 608, faithful. Rule passed; no change to the settings. |
| 22:32 | `host.mjs init --provider` added, so the report does not claim the Codex tool (`a3f488f`, 0.9.0). |
| 22:33 | Driver `comfy-chain.mjs`, graph file and fake-server tests added (`71701a5`, 0.10.0). Pipeline green, driver line coverage 100%. |
| 22:34 | Chain started detached under `systemd-inhibit`. |
| 22:37 | 10 / 10 done, exit 0. Checkpoint commit `b3c625e`. A second, empty-value commit `50e1077` came from the DONE step; fixed in `046225e` (0.10.1). |
| 22:40 | Frames 0, 5 and 10 checked by eye. Lineage checked: each frame's input hash is the previous frame's hash. README section added. |

## Results

| Generation | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Seconds (API, end to end) | 11.2 | 14.4 | 15.2 | 15.2 | 15.2 | 15.2 | 15.3 | 15.3 | 15.3 | 15.3 |
| Pixel standard deviation | 0.307 | 0.321 | 0.333 | 0.344 | 0.352 | 0.356 | 0.359 | 0.359 | 0.358 | 0.357 |

Frame 0 (the source) has a standard deviation of 0.250. The values are from `identify -format '%[fx:standard_deviation]'`. They show the contrast growth, and it slows after generation 7.

- Median: 15.2 s. Range: 11.2–15.3 s. The limit is 240 s. The rule passed.
- The driver loop adds about 1.3 s per generation for the ledger and the GIF. A generation thus takes about 16.5 s of wall clock.
- Peak GPU memory (whole GPU, `nvidia-smi` every 0.5 s): 7618 MiB of 8192 MiB. ComfyUI loads the 3.9 GB model dynamically in `--lowvram` mode.
- RMSE to the previous frame: 0.031 at generation 5, 0.024 at generation 10. RMSE between generation 1 and generation 10: 0.164.

Visual check (frames 0, 5 and 10, side by side): no black frame, no copy, the correct input each time. Generation 1 is close to the source but sharper and more saturated. By generation 5 the suit is a strong blue, the skin is red and the background is yellow-green. By generation 10 the face and the jacket have a fine crosshatch texture, and the beard and the tie start to break up. The pose, the glasses, the bottle and the microphone stay in place.

Open points:

1. The fixed seed gives the same noise each generation. The noise may print the same texture again and again, and this may cause part of the crosshatch. A second arm with seed `42 + n` would test this. Label it as an A/B arm; do not pool it with this run.
2. The fp8 weights are upcast on the A2000. This affects speed only. At 15 s per generation it does not matter.
3. ComfyUI keeps the uploaded frames in `~/repos/ComfyUI/input/recreate101/` (about 1 MB each). The outputs go to its `temp/` directory, which ComfyUI clears at start.
4. If the driver stops between `POST /prompt` and the `queued` line in `comfy.jsonl` (a window of milliseconds), the next start cancels the request. ComfyUI may still finish that prompt; the result is then not used.

## Resume here

State (2026-11-10 23:35): `pilot-comfyui-niklaus-wirth` 100 / 100 done. `pilot-comfyui-turing-v2` running, then `pilot-comfyui-turing-v1`, then `pilot-comfyui-limburg-cathedral` (stopped at generation 1 with a queued prompt; the driver resumes it from the ComfyUI history). The scratchpad script `comfy-reorder.sh` runs the church last and then stops the server. Logs: `~/.cache/recreate101-comfy/*.log`.

Check (read-only; `status` takes no lock since 0.14.3):

```sh
cd /home/mpetrick/repos/codingWithGPT/20261109_recreate101ImageGenerations
node recreate-101/scripts/host.mjs status --run-dir RUN
tail -n 5 RUN/chain.log
curl -s 127.0.0.1:8188/system_stats | head -c 200
ps -eo pid,args | grep -E '^ *[0-9]+ node recreate-101/scripts/comfy-chain.mjs'
```

Start the ComfyUI server (if `system_stats` gives no answer):

```sh
cd /home/mpetrick/repos/ComfyUI
setsid nohup systemd-inhibit --what=sleep:idle --why="recreate-101 ComfyUI server" \
  venv/bin/python main.py --lowvram --preview-method none --disable-api-nodes --listen 127.0.0.1 --port 8188 \
  >> ~/.cache/recreate101-comfy/comfyui.log 2>&1 < /dev/null & disown
```

Resume one run (only one ComfyUI chain at a time):

```sh
cd /home/mpetrick/repos/codingWithGPT/20261109_recreate101ImageGenerations
setsid nohup systemd-inhibit --what=sleep:idle --why="recreate-101 ComfyUI chain" \
  node recreate-101/scripts/comfy-chain.mjs RUN >> RUN/chain.log 2>&1 < /dev/null & disown
```

The driver is idempotent. A restart resumes a queued prompt from ComfyUI's history, or cancels a request that was never queued. It stops (exit 3) on an unreachable server, an empty read, a failed prompt, or an invalid image. Stop the server afterwards with `pkill -f 'main.py --lowvram --preview-method none'`.
