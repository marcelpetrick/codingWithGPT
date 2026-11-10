# Recreate 101

[![Recreate 101 checks](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/recreate-101.yml/badge.svg)](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/recreate-101.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)

Recreate an image repeatedly and watch the changes accumulate. Each generation uses only the previous image. The skill keeps the original, full-resolution PNG frames, a GIF, and a lineage record.

## Step-by-step comparison

Four chains use the same fixed prompt. Two sources (Niklaus Wirth, Limburg Cathedral) go through two image models: the Codex image tool and a local FLUX.2 [klein] 4B in ComfyUI. Each row shows the same generation in every chain. The thumbnails are JPEG viewing copies. The PNG frames are the source data.

`./updateComparison.sh` generates this section from the run manifests. Do not edit it by hand.

<!-- comparison:start -->
| Run | Provider | Generations | Refusals | Median time per generation | Status |
| --- | --- | --- | --- | --- | --- |
| Wirth, Codex | `codex-host-image-tool` | 64 / 101 | 9 | 33.6 s (54 timed) | request pending |
| Wirth, ComfyUI | `comfyui-flux2-klein-4b-distilled` | 64 / 100 | 0 | 15.5 s (64 timed) | request pending |
| Limburg, Codex | `codex-host-image-tool` | 38 / 100 | 0 | 40.8 s (38 timed) | request pending |
| Limburg, ComfyUI | `comfyui-flux2-klein-4b-distilled` | 0 / 100 | 0 | Unavailable | running or stopped |

| Generation | Wirth, Codex | Wirth, ComfyUI | Limburg, Codex | Limburg, ComfyUI |
| --- | --- | --- | --- | --- |
| 0 | <img src="comparison/run0-0000.jpg" width="200" alt="Wirth, Codex, generation 0"> | <img src="comparison/run1-0000.jpg" width="200" alt="Wirth, ComfyUI, generation 0"> | <img src="comparison/run2-0000.jpg" width="200" alt="Limburg, Codex, generation 0"> | <img src="comparison/run3-0000.jpg" width="200" alt="Limburg, ComfyUI, generation 0"> |
| 10 | <img src="comparison/run0-0010.jpg" width="200" alt="Wirth, Codex, generation 10"> | <img src="comparison/run1-0010.jpg" width="200" alt="Wirth, ComfyUI, generation 10"> | <img src="comparison/run2-0010.jpg" width="200" alt="Limburg, Codex, generation 10"> | — |
| 20 | <img src="comparison/run0-0020.jpg" width="200" alt="Wirth, Codex, generation 20"> | <img src="comparison/run1-0020.jpg" width="200" alt="Wirth, ComfyUI, generation 20"> | <img src="comparison/run2-0020.jpg" width="200" alt="Limburg, Codex, generation 20"> | — |
| 30 | <img src="comparison/run0-0030.jpg" width="200" alt="Wirth, Codex, generation 30"> | <img src="comparison/run1-0030.jpg" width="200" alt="Wirth, ComfyUI, generation 30"> | <img src="comparison/run2-0030.jpg" width="200" alt="Limburg, Codex, generation 30"> | — |
| 40 | <img src="comparison/run0-0040.jpg" width="200" alt="Wirth, Codex, generation 40"> | <img src="comparison/run1-0040.jpg" width="200" alt="Wirth, ComfyUI, generation 40"> | — | — |
| 50 | <img src="comparison/run0-0050.jpg" width="200" alt="Wirth, Codex, generation 50"> | <img src="comparison/run1-0050.jpg" width="200" alt="Wirth, ComfyUI, generation 50"> | — | — |
| 60 | <img src="comparison/run0-0060.jpg" width="200" alt="Wirth, Codex, generation 60"> | <img src="comparison/run1-0060.jpg" width="200" alt="Wirth, ComfyUI, generation 60"> | — | — |
<!-- comparison:end -->

## Niklaus Wirth experiment

![Sequential recreations of Niklaus Wirth](pilot-niklaus-wirth/evolution.gif)

The current animation uses the Codex image tool. The experiment targets 101 generations. The original photograph is by Tyomitch. See [the source and license notes](examples/README.md). The source and generated PNGs are in [the pilot directory](pilot-niklaus-wirth/). The GIF is a color-quantized viewing copy.

## ComfyUI local path

![Ten local recreations of Niklaus Wirth with FLUX.2 klein 4B](pilot-comfyui-niklaus-wirth/evolution.gif)

A second, fully local chain uses ComfyUI on the workstation GPU (RTX A2000, 8 GB). The model is FLUX.2 [klein] 4B distilled (Apache 2.0), with the same fixed prompt and only the previous frame as input. A generation takes about 15 s. The colours and the contrast grow with each generation. See [COMFYUI_PATH.md](COMFYUI_PATH.md) and [the run directory](pilot-comfyui-niklaus-wirth/). The driver is `recreate-101/scripts/comfy-chain.mjs`.

## Limburg Cathedral experiment

The second chain uses a CC BY-SA 3.0 photo of Limburg Cathedral by Norbert Nagel. It targets 100 generations with the same driver. See [its page](pilot-limburg-cathedral/README.md).

## Checkpoints and usage

The table is generated from `pilot-niklaus-wirth/manifest.json` by `host.mjs readme`. Do not edit it by hand.

<!-- checkpoints:start -->
| Completed generations | Animation | Refusals so far | Codex agent tokens (calls with data) | Subscriber allowance |
| --- | --- | --- | --- | --- |
| 10 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0010.gif) | 0 | Unavailable | Unavailable |
| 20 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0020.gif) | 6 | 391118 in (284800 cached), 1186 out, 8 calls | Unavailable |
| 30 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0030.gif) | 8 | 872591 in (665600 cached), 2628 out, 18 calls | Unavailable |
| 40 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0040.gif) | 8 | 1331703 in (1028736 cached), 4054 out, 28 calls | Unavailable |
| 50 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0050.gif) | 8 | 1831080 in (1435264 cached), 5633 out, 38 calls | Unavailable |
| 60 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0060.gif) | 8 | 2345333 in (1816064 cached), 7212 out, 48 calls | Unavailable |
<!-- checkpoints:end -->

Generations 1–12 ran in one Codex session on 2026-11-09. The image tool refused generation 13 at the output moderation stage. From 2026-11-10, Claude Code runs the chain. It starts one fresh `codex exec` session for each generation with `recreate-101/scripts/codex-chain.sh`. The prompt does not change. A refused frame is sent again, at most three times in a row. See the [experiment report](pilot-niklaus-wirth/report.md).

The host tool does not expose image token counts, per-call charges, or remaining subscription allowance. "Codex agent tokens" are the tokens of the `codex exec` sessions that called the tool. These values are unknown, not zero. A generation may consume included usage. The count is the number of completed image-tool calls in this experiment.

## Setup

Install Node.js 24, ImageMagick (`convert` and `identify`), FFmpeg (`ffprobe`), and ShellCheck. Copy `recreate-101/` to the supported skill directory for your agent. The skill uses Codex's built-in image tool when the host provides it. The agent must invoke that tool once for each frame. The Node scripts cannot invoke the private tool by themselves.

In Codex, request: `Use recreate-101 on /path/to/image.jpg for 10 generations.` The agent reads [SKILL.md](recreate-101/SKILL.md) and follows [the operating reference](recreate-101/references/usage.md). The host tool may consume included usage. Its token count and cost are not exposed by this runner.

## Local test

Run the no-network mock test with a local input:

```sh
node recreate-101/scripts/recreate.mjs run --input examples/niklaus-wirth.jpg --iterations 3 --provider mock --budget-usd 0
```

The mock changes a pixel in each frame. It does not call an image model. For a real Codex tool run, use the agent and the host checkpoint commands in the operating reference. The optional direct API path requires separate credentials, an explicit budget, and acceptance of its estimated reserve.

## Checks

```sh
./localPipeline.sh
```

The pipeline checks shell syntax with ShellCheck, checks JavaScript syntax, runs the Node tests, and enforces 95% line coverage. The tests cover mock and host checkpoint workflows. They do not measure real image quality or API billing. The [GitHub Actions workflow](../.github/workflows/recreate-101.yml) runs the same pipeline. This project has no graphical UI or Docker image.

## Scripts

- `recreate-101/scripts/host.mjs` records a host-tool run, its refusals and checkpoints, and builds its GIF.
- `recreate-101/scripts/codex-chain.sh` runs a host-tool chain with one `codex exec` session per generation.
- `recreate-101/scripts/comfy-chain.mjs` runs a chain through a local ComfyUI server, one API prompt per generation.
- `recreate-101/scripts/recreate.mjs` runs the mock or optional direct API provider.
- `localPipeline.sh` runs local checks.

The [vision](vision.md) defines the experiment. [IMPLEMENTATION.md](IMPLEMENTATION.md) records progress and restart commands. [review_20261109.md](review_20261109.md) records known limits.

## License

The project code is GPL-3.0-or-later. See [LICENSE](LICENSE). The example photograph has its own permission terms, recorded in [examples/README.md](examples/README.md).
