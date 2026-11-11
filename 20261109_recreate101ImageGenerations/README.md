# Recreate 101

[![Recreate 101 checks](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/recreate-101.yml/badge.svg)](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/recreate-101.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)

Recreate an image repeatedly and watch the changes accumulate. Each generation uses only the previous image. The skill keeps the original, full-resolution PNG frames, a GIF, and a lineage record.

## Overview of all runs

Every run sends an image through a chain of generations. Each generation sees only the previous frame and one fixed prompt. The table shows each source, its latest frame and the drift `d` (ImageMagick SSIM distortion against the source, 0 = identical). It is generated from the run manifests by `updateComparison.sh`. Click a run for its frames, report and checkpoints. The image sources and licenses are in [examples/README.md](examples/README.md).

<!-- overview:start -->
| Run | Source | Latest frame | Model | Prompt | Generations | Status |
| --- | --- | --- | --- | --- | --- | --- |
| [Wirth, Codex, v1](pilot-niklaus-wirth/) | <img src="comparison/overview-pilot-niklaus-wirth-first.jpg" width="120" alt="Wirth, Codex, v1, source"> | <img src="comparison/overview-pilot-niklaus-wirth-last.jpg" width="120" alt="Wirth, Codex, v1, generation 101"><br>gen 101, d = 0.466 · [GIF](pilot-niklaus-wirth/evolution.gif) | `codex-host-image-tool` | v1 | 101 / 101 | complete |
| [Wirth, ComfyUI, v1](pilot-comfyui-niklaus-wirth/) | <img src="comparison/overview-pilot-comfyui-niklaus-wirth-first.jpg" width="120" alt="Wirth, ComfyUI, v1, source"> | <img src="comparison/overview-pilot-comfyui-niklaus-wirth-last.jpg" width="120" alt="Wirth, ComfyUI, v1, generation 100"><br>gen 100, d = 0.376 · [GIF](pilot-comfyui-niklaus-wirth/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | v1 | 100 / 100 | complete |
| [Limburg, Codex, v1](pilot-limburg-cathedral/) | <img src="comparison/overview-pilot-limburg-cathedral-first.jpg" width="120" alt="Limburg, Codex, v1, source"> | <img src="comparison/overview-pilot-limburg-cathedral-last.jpg" width="120" alt="Limburg, Codex, v1, generation 100"><br>gen 100, d = 0.463 · [GIF](pilot-limburg-cathedral/evolution.gif) | `codex-host-image-tool` | v1 | 100 / 100 | complete |
| [Limburg, ComfyUI, v1](pilot-comfyui-limburg-cathedral/) | <img src="comparison/overview-pilot-comfyui-limburg-cathedral-first.jpg" width="120" alt="Limburg, ComfyUI, v1, source"> | <img src="comparison/overview-pilot-comfyui-limburg-cathedral-last.jpg" width="120" alt="Limburg, ComfyUI, v1, generation 100"><br>gen 100, d = 0.459 · [GIF](pilot-comfyui-limburg-cathedral/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | v1 | 100 / 100 | complete |
| [Turing, Codex, v2](pilot-turing-codex-v2/) | <img src="comparison/overview-pilot-turing-codex-v2-first.jpg" width="120" alt="Turing, Codex, v2, source"> | <img src="comparison/overview-pilot-turing-codex-v2-last.jpg" width="120" alt="Turing, Codex, v2, generation 100"><br>gen 100, d = 0.467 · [GIF](pilot-turing-codex-v2/evolution.gif) | `codex-host-image-tool` | prompt-v2 | 100 / 100 | complete |
| [Turing, ComfyUI, v2](pilot-comfyui-turing-v2/) | <img src="comparison/overview-pilot-comfyui-turing-v2-first.jpg" width="120" alt="Turing, ComfyUI, v2, source"> | <img src="comparison/overview-pilot-comfyui-turing-v2-last.jpg" width="120" alt="Turing, ComfyUI, v2, generation 100"><br>gen 100, d = 0.440 · [GIF](pilot-comfyui-turing-v2/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | complete |
| [Turing, ComfyUI, v1](pilot-comfyui-turing-v1/) | <img src="comparison/overview-pilot-comfyui-turing-v1-first.jpg" width="120" alt="Turing, ComfyUI, v1, source"> | <img src="comparison/overview-pilot-comfyui-turing-v1-last.jpg" width="120" alt="Turing, ComfyUI, v1, generation 100"><br>gen 100, d = 0.473 · [GIF](pilot-comfyui-turing-v1/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | v1 | 100 / 100 | complete |
| [Cat, ComfyUI, v2](pilot-comfyui-tabby-cat/) | <img src="comparison/overview-pilot-comfyui-tabby-cat-first.jpg" width="120" alt="Cat, ComfyUI, v2, source"> | <img src="comparison/overview-pilot-comfyui-tabby-cat-last.jpg" width="120" alt="Cat, ComfyUI, v2, generation 100"><br>gen 100, d = 0.383 · [GIF](pilot-comfyui-tabby-cat/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | complete |
| [Cat, ComfyUI, v3](pilot-comfyui-tabby-cat-v3/) | <img src="comparison/overview-pilot-comfyui-tabby-cat-v3-first.jpg" width="120" alt="Cat, ComfyUI, v3, source"> | <img src="comparison/overview-pilot-comfyui-tabby-cat-v3-last.jpg" width="120" alt="Cat, ComfyUI, v3, generation 100"><br>gen 100, d = 0.469 · [GIF](pilot-comfyui-tabby-cat-v3/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | complete |
| [Cat, ComfyUI img2img, v3](pilot-comfyui-tabby-cat-v3i/) | <img src="comparison/overview-pilot-comfyui-tabby-cat-v3i-first.jpg" width="120" alt="Cat, ComfyUI img2img, v3, source"> | <img src="comparison/overview-pilot-comfyui-tabby-cat-v3i-last.jpg" width="120" alt="Cat, ComfyUI img2img, v3, generation 100"><br>gen 100, d = 0.417 · [GIF](pilot-comfyui-tabby-cat-v3i/evolution.gif) | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 100 / 100 | complete |
| [Corgi, ComfyUI, v2](pilot-comfyui-corgi-puppy/) | <img src="comparison/overview-pilot-comfyui-corgi-puppy-first.jpg" width="120" alt="Corgi, ComfyUI, v2, source"> | <img src="comparison/overview-pilot-comfyui-corgi-puppy-last.jpg" width="120" alt="Corgi, ComfyUI, v2, generation 100"><br>gen 100, d = 0.448 · [GIF](pilot-comfyui-corgi-puppy/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | complete |
| [Corgi, ComfyUI, v3](pilot-comfyui-corgi-puppy-v3/) | <img src="comparison/overview-pilot-comfyui-corgi-puppy-v3-first.jpg" width="120" alt="Corgi, ComfyUI, v3, source"> | <img src="comparison/overview-pilot-comfyui-corgi-puppy-v3-last.jpg" width="120" alt="Corgi, ComfyUI, v3, generation 100"><br>gen 100, d = 0.445 · [GIF](pilot-comfyui-corgi-puppy-v3/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | complete |
| [Corgi, ComfyUI img2img, v3](pilot-comfyui-corgi-puppy-v3i/) | <img src="comparison/overview-pilot-comfyui-corgi-puppy-v3i-first.jpg" width="120" alt="Corgi, ComfyUI img2img, v3, source"> | <img src="comparison/overview-pilot-comfyui-corgi-puppy-v3i-last.jpg" width="120" alt="Corgi, ComfyUI img2img, v3, generation 0"><br>gen 0, d = 0.000 | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | running or queued |
| [Christmas market, ComfyUI, v2](pilot-comfyui-berlin-christmas-market/) | <img src="comparison/overview-pilot-comfyui-berlin-christmas-market-first.jpg" width="120" alt="Christmas market, ComfyUI, v2, source"> | <img src="comparison/overview-pilot-comfyui-berlin-christmas-market-last.jpg" width="120" alt="Christmas market, ComfyUI, v2, generation 100"><br>gen 100, d = 0.441 · [GIF](pilot-comfyui-berlin-christmas-market/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | complete |
| [Christmas market, ComfyUI, v3](pilot-comfyui-berlin-christmas-market-v3/) | <img src="comparison/overview-pilot-comfyui-berlin-christmas-market-v3-first.jpg" width="120" alt="Christmas market, ComfyUI, v3, source"> | <img src="comparison/overview-pilot-comfyui-berlin-christmas-market-v3-last.jpg" width="120" alt="Christmas market, ComfyUI, v3, generation 100"><br>gen 100, d = 0.474 · [GIF](pilot-comfyui-berlin-christmas-market-v3/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | complete |
| [Christmas market, ComfyUI img2img, v3](pilot-comfyui-berlin-christmas-market-v3i/) | <img src="comparison/overview-pilot-comfyui-berlin-christmas-market-v3i-first.jpg" width="120" alt="Christmas market, ComfyUI img2img, v3, source"> | <img src="comparison/overview-pilot-comfyui-berlin-christmas-market-v3i-last.jpg" width="120" alt="Christmas market, ComfyUI img2img, v3, generation 0"><br>gen 0, d = 0.000 | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | running or queued |
| [Dwayne Johnson, ComfyUI, v2](pilot-comfyui-dwayne-johnson/) | <img src="comparison/overview-pilot-comfyui-dwayne-johnson-first.jpg" width="120" alt="Dwayne Johnson, ComfyUI, v2, source"> | <img src="comparison/overview-pilot-comfyui-dwayne-johnson-last.jpg" width="120" alt="Dwayne Johnson, ComfyUI, v2, generation 100"><br>gen 100, d = 0.360 · [GIF](pilot-comfyui-dwayne-johnson/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | complete |
| [Dwayne Johnson, ComfyUI, v3](pilot-comfyui-dwayne-johnson-v3/) | <img src="comparison/overview-pilot-comfyui-dwayne-johnson-v3-first.jpg" width="120" alt="Dwayne Johnson, ComfyUI, v3, source"> | <img src="comparison/overview-pilot-comfyui-dwayne-johnson-v3-last.jpg" width="120" alt="Dwayne Johnson, ComfyUI, v3, generation 100"><br>gen 100, d = 0.468 · [GIF](pilot-comfyui-dwayne-johnson-v3/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | complete |
| [Dwayne Johnson, ComfyUI img2img, v3](pilot-comfyui-dwayne-johnson-v3i/) | <img src="comparison/overview-pilot-comfyui-dwayne-johnson-v3i-first.jpg" width="120" alt="Dwayne Johnson, ComfyUI img2img, v3, source"> | <img src="comparison/overview-pilot-comfyui-dwayne-johnson-v3i-last.jpg" width="120" alt="Dwayne Johnson, ComfyUI img2img, v3, generation 0"><br>gen 0, d = 0.000 | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | running or queued |
| [Mona Lisa, ComfyUI, v2](pilot-comfyui-mona-lisa/) | <img src="comparison/overview-pilot-comfyui-mona-lisa-first.jpg" width="120" alt="Mona Lisa, ComfyUI, v2, source"> | <img src="comparison/overview-pilot-comfyui-mona-lisa-last.jpg" width="120" alt="Mona Lisa, ComfyUI, v2, generation 100"><br>gen 100, d = 0.420 · [GIF](pilot-comfyui-mona-lisa/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | complete |
| [Mona Lisa, ComfyUI, v3](pilot-comfyui-mona-lisa-v3/) | <img src="comparison/overview-pilot-comfyui-mona-lisa-v3-first.jpg" width="120" alt="Mona Lisa, ComfyUI, v3, source"> | <img src="comparison/overview-pilot-comfyui-mona-lisa-v3-last.jpg" width="120" alt="Mona Lisa, ComfyUI, v3, generation 100"><br>gen 100, d = 0.471 · [GIF](pilot-comfyui-mona-lisa-v3/evolution.gif) | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | complete |
| [Mona Lisa, ComfyUI img2img, v3](pilot-comfyui-mona-lisa-v3i/) | <img src="comparison/overview-pilot-comfyui-mona-lisa-v3i-first.jpg" width="120" alt="Mona Lisa, ComfyUI img2img, v3, source"> | <img src="comparison/overview-pilot-comfyui-mona-lisa-v3i-last.jpg" width="120" alt="Mona Lisa, ComfyUI img2img, v3, generation 0"><br>gen 0, d = 0.000 | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | running or queued |
| [Cat, ComfyUI img2img, v2 (control)](pilot-comfyui-tabby-cat-v2i/) | <img src="comparison/overview-pilot-comfyui-tabby-cat-v2i-first.jpg" width="120" alt="Cat, ComfyUI img2img, v2 (control), source"> | <img src="comparison/overview-pilot-comfyui-tabby-cat-v2i-last.jpg" width="120" alt="Cat, ComfyUI img2img, v2 (control), generation 74"><br>gen 74, d = 0.422 · [GIF](pilot-comfyui-tabby-cat-v2i/evolution.gif) | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v2 | 74 / 100 | running or queued |
<!-- overview:end -->

## Prompts

Each run stores its prompt in `manifest.json`. A run without a stored prompt uses v1 from `SKILL.md`.

- v1 asks for a faithful copy. It is the default.
- v2 also names color, contrast, sharpness and grain, to reduce drift. It gave a tie against v1 on ComfyUI (see [IMPLEMENTATION.md](IMPLEMENTATION.md)).
- v3 asks for a very small step toward an oil painting in each generation, to steer the drift into a style. On the default graph the model ignores "small" and paints the full style at once. The img2img runs use the same v3 text on a graph that limits each step.

<!-- prompts:start -->
| Prompt | Text | Runs |
| --- | --- | --- |
| [v1](recreate-101/SKILL.md) | Recreate the provided image as faithfully as possible. Preserve its composition, subjects, shapes, colors, lighting, textures, background, framing, and any visible text. Make no intentional additions, removals, improvements, or stylistic changes. Return one image. | Wirth, Codex, v1, Wirth, ComfyUI, v1, Limburg, Codex, v1, Limburg, ComfyUI, v1, Turing, ComfyUI, v1 |
| [prompt-v2](recreate-101/references/prompt-v2.txt) | Recreate the provided image as an exact copy. Match its colors, saturation, contrast, brightness, sharpness, noise and grain exactly. Do not enhance, sharpen, smooth, saturate, recolor or stylize anything. Preserve the composition, framing, subjects, faces, shapes, lighting, textures, background and any visible text. Make no additions, removals or corrections. Return one image. | Turing, Codex, v2, Turing, ComfyUI, v2, Cat, ComfyUI, v2, Corgi, ComfyUI, v2, Christmas market, ComfyUI, v2, Dwayne Johnson, ComfyUI, v2, Mona Lisa, ComfyUI, v2, Cat, ComfyUI img2img, v2 (control) |
| [prompt-v3](recreate-101/references/prompt-v3.txt) | Recreate the provided image almost exactly. Keep the composition, framing, subjects, faces, poses, shapes, lighting, background and colors. Change only one thing, and only by a very small step: render the image slightly more like a post-impressionist oil painting, with faintly visible brush strokes and a little more painterly color. The change must be barely noticeable when compared with the input. Make no additions or removals. Return one image. | Cat, ComfyUI, v3, Cat, ComfyUI img2img, v3, Corgi, ComfyUI, v3, Corgi, ComfyUI img2img, v3, Christmas market, ComfyUI, v3, Christmas market, ComfyUI img2img, v3, Dwayne Johnson, ComfyUI, v3, Dwayne Johnson, ComfyUI img2img, v3, Mona Lisa, ComfyUI, v3, Mona Lisa, ComfyUI img2img, v3 |
<!-- prompts:end -->

## Step-by-step comparison

Four chains use prompt v1. Two sources (Niklaus Wirth, Limburg Cathedral) go through two image models: the Codex image tool and a local FLUX.2 [klein] 4B in ComfyUI. Each row shows the same generation in every chain. `d` is the drift distance: the ImageMagick SSIM distortion against frame 0 at 256 x 256, where 0 means identical. The thumbnails are JPEG viewing copies. The PNG frames are the source data.

Limits of this comparison:

- `d` comes from ImageMagick 7 (7.1.2-32 here). Other versions can give other values. CI uses ImageMagick 6 and shows `n/a`.
- "Median time" is wall time per frame from the manifest. For Codex it includes the agent session and parallel chains. For ComfyUI it is local GPU time. Do not compare the two directly.
- Codex frames up to Wirth 67 and Limburg 39 went through the Codex agent with its `imagegen` skill active. That skill can reformat prompts, and those sessions did not record the prompt the tool received. From the restart at 23:30, the agent is told to pass the prompt unchanged and to report it. Each frame stores the report (`promptSent`), and each session log is kept in `codex-events/`.
- ComfyUI uses one fixed seed (42) for every frame. Part of its texture drift can come from the repeated noise pattern.

`./updateComparison.sh` generates this section from the run manifests. Do not edit it by hand.

<!-- comparison:start -->
| Run | Provider | Prompt | Generations | Refusals | Median time per generation | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Wirth, Codex | `codex-host-image-tool` | v1 | 101 / 101 | 13 | 33.6 s (91 timed) | complete |
| Wirth, ComfyUI | `comfyui-flux2-klein-4b-distilled` | v1 | 100 / 100 | 0 | 15.7 s (100 timed) | complete |
| Limburg, Codex | `codex-host-image-tool` | v1 | 100 / 100 | 0 | 33.1 s (100 timed) | complete |
| Limburg, ComfyUI | `comfyui-flux2-klein-4b-distilled` | v1 | 100 / 100 | 0 | 15.7 s (100 timed) | complete |

| Generation | Wirth, Codex | Wirth, ComfyUI | Limburg, Codex | Limburg, ComfyUI |
| --- | --- | --- | --- | --- |
| 0 | <img src="comparison/pilot-niklaus-wirth-0000.jpg" width="200" alt="Wirth, Codex, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-niklaus-wirth-0000.jpg" width="200" alt="Wirth, ComfyUI, generation 0"><br>d = 0.000 | <img src="comparison/pilot-limburg-cathedral-0000.jpg" width="200" alt="Limburg, Codex, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-limburg-cathedral-0000.jpg" width="200" alt="Limburg, ComfyUI, generation 0"><br>d = 0.000 |
| 10 | <img src="comparison/pilot-niklaus-wirth-0010.jpg" width="200" alt="Wirth, Codex, generation 10"><br>d = 0.131 | <img src="comparison/pilot-comfyui-niklaus-wirth-0010.jpg" width="200" alt="Wirth, ComfyUI, generation 10"><br>d = 0.225 | <img src="comparison/pilot-limburg-cathedral-0010.jpg" width="200" alt="Limburg, Codex, generation 10"><br>d = 0.338 | <img src="comparison/pilot-comfyui-limburg-cathedral-0010.jpg" width="200" alt="Limburg, ComfyUI, generation 10"><br>d = 0.198 |
| 20 | <img src="comparison/pilot-niklaus-wirth-0020.jpg" width="200" alt="Wirth, Codex, generation 20"><br>d = 0.204 | <img src="comparison/pilot-comfyui-niklaus-wirth-0020.jpg" width="200" alt="Wirth, ComfyUI, generation 20"><br>d = 0.319 | <img src="comparison/pilot-limburg-cathedral-0020.jpg" width="200" alt="Limburg, Codex, generation 20"><br>d = 0.430 | <img src="comparison/pilot-comfyui-limburg-cathedral-0020.jpg" width="200" alt="Limburg, ComfyUI, generation 20"><br>d = 0.255 |
| 30 | <img src="comparison/pilot-niklaus-wirth-0030.jpg" width="200" alt="Wirth, Codex, generation 30"><br>d = 0.258 | <img src="comparison/pilot-comfyui-niklaus-wirth-0030.jpg" width="200" alt="Wirth, ComfyUI, generation 30"><br>d = 0.350 | <img src="comparison/pilot-limburg-cathedral-0030.jpg" width="200" alt="Limburg, Codex, generation 30"><br>d = 0.465 | <img src="comparison/pilot-comfyui-limburg-cathedral-0030.jpg" width="200" alt="Limburg, ComfyUI, generation 30"><br>d = 0.315 |
| 40 | <img src="comparison/pilot-niklaus-wirth-0040.jpg" width="200" alt="Wirth, Codex, generation 40"><br>d = 0.327 | <img src="comparison/pilot-comfyui-niklaus-wirth-0040.jpg" width="200" alt="Wirth, ComfyUI, generation 40"><br>d = 0.349 | <img src="comparison/pilot-limburg-cathedral-0040.jpg" width="200" alt="Limburg, Codex, generation 40"><br>d = 0.472 | <img src="comparison/pilot-comfyui-limburg-cathedral-0040.jpg" width="200" alt="Limburg, ComfyUI, generation 40"><br>d = 0.380 |
| 50 | <img src="comparison/pilot-niklaus-wirth-0050.jpg" width="200" alt="Wirth, Codex, generation 50"><br>d = 0.381 | <img src="comparison/pilot-comfyui-niklaus-wirth-0050.jpg" width="200" alt="Wirth, ComfyUI, generation 50"><br>d = 0.354 | <img src="comparison/pilot-limburg-cathedral-0050.jpg" width="200" alt="Limburg, Codex, generation 50"><br>d = 0.474 | <img src="comparison/pilot-comfyui-limburg-cathedral-0050.jpg" width="200" alt="Limburg, ComfyUI, generation 50"><br>d = 0.367 |
| 60 | <img src="comparison/pilot-niklaus-wirth-0060.jpg" width="200" alt="Wirth, Codex, generation 60"><br>d = 0.412 | <img src="comparison/pilot-comfyui-niklaus-wirth-0060.jpg" width="200" alt="Wirth, ComfyUI, generation 60"><br>d = 0.362 | <img src="comparison/pilot-limburg-cathedral-0060.jpg" width="200" alt="Limburg, Codex, generation 60"><br>d = 0.472 | <img src="comparison/pilot-comfyui-limburg-cathedral-0060.jpg" width="200" alt="Limburg, ComfyUI, generation 60"><br>d = 0.385 |
| 70 | <img src="comparison/pilot-niklaus-wirth-0070.jpg" width="200" alt="Wirth, Codex, generation 70"><br>d = 0.430 | <img src="comparison/pilot-comfyui-niklaus-wirth-0070.jpg" width="200" alt="Wirth, ComfyUI, generation 70"><br>d = 0.363 | <img src="comparison/pilot-limburg-cathedral-0070.jpg" width="200" alt="Limburg, Codex, generation 70"><br>d = 0.468 | <img src="comparison/pilot-comfyui-limburg-cathedral-0070.jpg" width="200" alt="Limburg, ComfyUI, generation 70"><br>d = 0.396 |
| 80 | <img src="comparison/pilot-niklaus-wirth-0080.jpg" width="200" alt="Wirth, Codex, generation 80"><br>d = 0.447 | <img src="comparison/pilot-comfyui-niklaus-wirth-0080.jpg" width="200" alt="Wirth, ComfyUI, generation 80"><br>d = 0.369 | <img src="comparison/pilot-limburg-cathedral-0080.jpg" width="200" alt="Limburg, Codex, generation 80"><br>d = 0.466 | <img src="comparison/pilot-comfyui-limburg-cathedral-0080.jpg" width="200" alt="Limburg, ComfyUI, generation 80"><br>d = 0.414 |
| 90 | <img src="comparison/pilot-niklaus-wirth-0090.jpg" width="200" alt="Wirth, Codex, generation 90"><br>d = 0.453 | <img src="comparison/pilot-comfyui-niklaus-wirth-0090.jpg" width="200" alt="Wirth, ComfyUI, generation 90"><br>d = 0.378 | <img src="comparison/pilot-limburg-cathedral-0090.jpg" width="200" alt="Limburg, Codex, generation 90"><br>d = 0.465 | <img src="comparison/pilot-comfyui-limburg-cathedral-0090.jpg" width="200" alt="Limburg, ComfyUI, generation 90"><br>d = 0.433 |
| 100 | <img src="comparison/pilot-niklaus-wirth-0100.jpg" width="200" alt="Wirth, Codex, generation 100"><br>d = 0.465 | <img src="comparison/pilot-comfyui-niklaus-wirth-0100.jpg" width="200" alt="Wirth, ComfyUI, generation 100"><br>d = 0.376 | <img src="comparison/pilot-limburg-cathedral-0100.jpg" width="200" alt="Limburg, Codex, generation 100"><br>d = 0.463 | <img src="comparison/pilot-comfyui-limburg-cathedral-0100.jpg" width="200" alt="Limburg, ComfyUI, generation 100"><br>d = 0.459 |
<!-- comparison:end -->

## Prompt v2 on Alan Turing

Prompt v2 ([text](recreate-101/references/prompt-v2.txt)) asks the model to match colors, contrast, sharpness and grain, and to not enhance anything. It targets the drift seen with v1. The source is a public-domain photo of Alan Turing at age 16. The ComfyUI v1 run is the control for the prompt effect. The decision rule is in [IMPLEMENTATION.md](IMPLEMENTATION.md): v2 must lower `d` by at least 0.05 at generations 50 and 100. One chain per arm is an indication, not a result.

<!-- turing:start -->
| Run | Provider | Prompt | Generations | Refusals | Median time per generation | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Turing, Codex, v2 | `codex-host-image-tool` | prompt-v2 | 100 / 100 | 9 | 31.4 s (100 timed) | complete |
| Turing, ComfyUI, v2 | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | 0 | 15.7 s (100 timed) | complete |
| Turing, ComfyUI, v1 | `comfyui-flux2-klein-4b-distilled` | v1 | 100 / 100 | 0 | 15.7 s (100 timed) | complete |

| Generation | Turing, Codex, v2 | Turing, ComfyUI, v2 | Turing, ComfyUI, v1 |
| --- | --- | --- | --- |
| 0 | <img src="comparison/pilot-turing-codex-v2-0000.jpg" width="200" alt="Turing, Codex, v2, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-turing-v2-0000.jpg" width="200" alt="Turing, ComfyUI, v2, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-turing-v1-0000.jpg" width="200" alt="Turing, ComfyUI, v1, generation 0"><br>d = 0.000 |
| 10 | <img src="comparison/pilot-turing-codex-v2-0010.jpg" width="200" alt="Turing, Codex, v2, generation 10"><br>d = 0.100 | <img src="comparison/pilot-comfyui-turing-v2-0010.jpg" width="200" alt="Turing, ComfyUI, v2, generation 10"><br>d = 0.223 | <img src="comparison/pilot-comfyui-turing-v1-0010.jpg" width="200" alt="Turing, ComfyUI, v1, generation 10"><br>d = 0.184 |
| 20 | <img src="comparison/pilot-turing-codex-v2-0020.jpg" width="200" alt="Turing, Codex, v2, generation 20"><br>d = 0.243 | <img src="comparison/pilot-comfyui-turing-v2-0020.jpg" width="200" alt="Turing, ComfyUI, v2, generation 20"><br>d = 0.317 | <img src="comparison/pilot-comfyui-turing-v1-0020.jpg" width="200" alt="Turing, ComfyUI, v1, generation 20"><br>d = 0.287 |
| 30 | <img src="comparison/pilot-turing-codex-v2-0030.jpg" width="200" alt="Turing, Codex, v2, generation 30"><br>d = 0.384 | <img src="comparison/pilot-comfyui-turing-v2-0030.jpg" width="200" alt="Turing, ComfyUI, v2, generation 30"><br>d = 0.385 | <img src="comparison/pilot-comfyui-turing-v1-0030.jpg" width="200" alt="Turing, ComfyUI, v1, generation 30"><br>d = 0.361 |
| 40 | <img src="comparison/pilot-turing-codex-v2-0040.jpg" width="200" alt="Turing, Codex, v2, generation 40"><br>d = 0.425 | <img src="comparison/pilot-comfyui-turing-v2-0040.jpg" width="200" alt="Turing, ComfyUI, v2, generation 40"><br>d = 0.399 | <img src="comparison/pilot-comfyui-turing-v1-0040.jpg" width="200" alt="Turing, ComfyUI, v1, generation 40"><br>d = 0.394 |
| 50 | <img src="comparison/pilot-turing-codex-v2-0050.jpg" width="200" alt="Turing, Codex, v2, generation 50"><br>d = 0.437 | <img src="comparison/pilot-comfyui-turing-v2-0050.jpg" width="200" alt="Turing, ComfyUI, v2, generation 50"><br>d = 0.414 | <img src="comparison/pilot-comfyui-turing-v1-0050.jpg" width="200" alt="Turing, ComfyUI, v1, generation 50"><br>d = 0.397 |
| 60 | <img src="comparison/pilot-turing-codex-v2-0060.jpg" width="200" alt="Turing, Codex, v2, generation 60"><br>d = 0.449 | <img src="comparison/pilot-comfyui-turing-v2-0060.jpg" width="200" alt="Turing, ComfyUI, v2, generation 60"><br>d = 0.424 | <img src="comparison/pilot-comfyui-turing-v1-0060.jpg" width="200" alt="Turing, ComfyUI, v1, generation 60"><br>d = 0.415 |
| 70 | <img src="comparison/pilot-turing-codex-v2-0070.jpg" width="200" alt="Turing, Codex, v2, generation 70"><br>d = 0.461 | <img src="comparison/pilot-comfyui-turing-v2-0070.jpg" width="200" alt="Turing, ComfyUI, v2, generation 70"><br>d = 0.440 | <img src="comparison/pilot-comfyui-turing-v1-0070.jpg" width="200" alt="Turing, ComfyUI, v1, generation 70"><br>d = 0.437 |
| 80 | <img src="comparison/pilot-turing-codex-v2-0080.jpg" width="200" alt="Turing, Codex, v2, generation 80"><br>d = 0.462 | <img src="comparison/pilot-comfyui-turing-v2-0080.jpg" width="200" alt="Turing, ComfyUI, v2, generation 80"><br>d = 0.443 | <img src="comparison/pilot-comfyui-turing-v1-0080.jpg" width="200" alt="Turing, ComfyUI, v1, generation 80"><br>d = 0.456 |
| 90 | <img src="comparison/pilot-turing-codex-v2-0090.jpg" width="200" alt="Turing, Codex, v2, generation 90"><br>d = 0.466 | <img src="comparison/pilot-comfyui-turing-v2-0090.jpg" width="200" alt="Turing, ComfyUI, v2, generation 90"><br>d = 0.441 | <img src="comparison/pilot-comfyui-turing-v1-0090.jpg" width="200" alt="Turing, ComfyUI, v1, generation 90"><br>d = 0.464 |
| 100 | <img src="comparison/pilot-turing-codex-v2-0100.jpg" width="200" alt="Turing, Codex, v2, generation 100"><br>d = 0.467 | <img src="comparison/pilot-comfyui-turing-v2-0100.jpg" width="200" alt="Turing, ComfyUI, v2, generation 100"><br>d = 0.440 | <img src="comparison/pilot-comfyui-turing-v1-0100.jpg" width="200" alt="Turing, ComfyUI, v1, generation 100"><br>d = 0.473 |
<!-- turing:end -->

## Five popular subjects on ComfyUI

Five more chains run on the local ComfyUI path with prompt v2: a cat, a dog, a Christmas market, a celebrity portrait and a famous painting. Each chain targets 100 generations, with only the previous frame as input. The sources are CC0, CC BY-SA or public domain. See [the source notes](examples/README.md). These runs have no Codex arm. They show how different subjects drift with one model and one prompt.

<!-- linkedin:start -->
| Run | Provider | Prompt | Generations | Refusals | Median time per generation | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Cat | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | 0 | 15.4 s (100 timed) | complete |
| Corgi | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | 0 | 15.5 s (100 timed) | complete |
| Christmas market | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | 0 | 15.4 s (100 timed) | complete |
| Dwayne Johnson | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | 0 | 15.4 s (100 timed) | complete |
| Mona Lisa | `comfyui-flux2-klein-4b-distilled` | prompt-v2 | 100 / 100 | 0 | 15.5 s (100 timed) | complete |

| Generation | Cat | Corgi | Christmas market | Dwayne Johnson | Mona Lisa |
| --- | --- | --- | --- | --- | --- |
| 0 | <img src="comparison/pilot-comfyui-tabby-cat-0000.jpg" width="200" alt="Cat, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-corgi-puppy-0000.jpg" width="200" alt="Corgi, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0000.jpg" width="200" alt="Christmas market, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-dwayne-johnson-0000.jpg" width="200" alt="Dwayne Johnson, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-mona-lisa-0000.jpg" width="200" alt="Mona Lisa, generation 0"><br>d = 0.000 |
| 10 | <img src="comparison/pilot-comfyui-tabby-cat-0010.jpg" width="200" alt="Cat, generation 10"><br>d = 0.264 | <img src="comparison/pilot-comfyui-corgi-puppy-0010.jpg" width="200" alt="Corgi, generation 10"><br>d = 0.309 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0010.jpg" width="200" alt="Christmas market, generation 10"><br>d = 0.321 | <img src="comparison/pilot-comfyui-dwayne-johnson-0010.jpg" width="200" alt="Dwayne Johnson, generation 10"><br>d = 0.181 | <img src="comparison/pilot-comfyui-mona-lisa-0010.jpg" width="200" alt="Mona Lisa, generation 10"><br>d = 0.325 |
| 20 | <img src="comparison/pilot-comfyui-tabby-cat-0020.jpg" width="200" alt="Cat, generation 20"><br>d = 0.279 | <img src="comparison/pilot-comfyui-corgi-puppy-0020.jpg" width="200" alt="Corgi, generation 20"><br>d = 0.364 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0020.jpg" width="200" alt="Christmas market, generation 20"><br>d = 0.372 | <img src="comparison/pilot-comfyui-dwayne-johnson-0020.jpg" width="200" alt="Dwayne Johnson, generation 20"><br>d = 0.227 | <img src="comparison/pilot-comfyui-mona-lisa-0020.jpg" width="200" alt="Mona Lisa, generation 20"><br>d = 0.362 |
| 30 | <img src="comparison/pilot-comfyui-tabby-cat-0030.jpg" width="200" alt="Cat, generation 30"><br>d = 0.304 | <img src="comparison/pilot-comfyui-corgi-puppy-0030.jpg" width="200" alt="Corgi, generation 30"><br>d = 0.390 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0030.jpg" width="200" alt="Christmas market, generation 30"><br>d = 0.399 | <img src="comparison/pilot-comfyui-dwayne-johnson-0030.jpg" width="200" alt="Dwayne Johnson, generation 30"><br>d = 0.296 | <img src="comparison/pilot-comfyui-mona-lisa-0030.jpg" width="200" alt="Mona Lisa, generation 30"><br>d = 0.393 |
| 40 | <img src="comparison/pilot-comfyui-tabby-cat-0040.jpg" width="200" alt="Cat, generation 40"><br>d = 0.326 | <img src="comparison/pilot-comfyui-corgi-puppy-0040.jpg" width="200" alt="Corgi, generation 40"><br>d = 0.396 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0040.jpg" width="200" alt="Christmas market, generation 40"><br>d = 0.410 | <img src="comparison/pilot-comfyui-dwayne-johnson-0040.jpg" width="200" alt="Dwayne Johnson, generation 40"><br>d = 0.336 | <img src="comparison/pilot-comfyui-mona-lisa-0040.jpg" width="200" alt="Mona Lisa, generation 40"><br>d = 0.406 |
| 50 | <img src="comparison/pilot-comfyui-tabby-cat-0050.jpg" width="200" alt="Cat, generation 50"><br>d = 0.357 | <img src="comparison/pilot-comfyui-corgi-puppy-0050.jpg" width="200" alt="Corgi, generation 50"><br>d = 0.403 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0050.jpg" width="200" alt="Christmas market, generation 50"><br>d = 0.421 | <img src="comparison/pilot-comfyui-dwayne-johnson-0050.jpg" width="200" alt="Dwayne Johnson, generation 50"><br>d = 0.351 | <img src="comparison/pilot-comfyui-mona-lisa-0050.jpg" width="200" alt="Mona Lisa, generation 50"><br>d = 0.408 |
| 60 | <img src="comparison/pilot-comfyui-tabby-cat-0060.jpg" width="200" alt="Cat, generation 60"><br>d = 0.374 | <img src="comparison/pilot-comfyui-corgi-puppy-0060.jpg" width="200" alt="Corgi, generation 60"><br>d = 0.407 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0060.jpg" width="200" alt="Christmas market, generation 60"><br>d = 0.423 | <img src="comparison/pilot-comfyui-dwayne-johnson-0060.jpg" width="200" alt="Dwayne Johnson, generation 60"><br>d = 0.369 | <img src="comparison/pilot-comfyui-mona-lisa-0060.jpg" width="200" alt="Mona Lisa, generation 60"><br>d = 0.406 |
| 70 | <img src="comparison/pilot-comfyui-tabby-cat-0070.jpg" width="200" alt="Cat, generation 70"><br>d = 0.387 | <img src="comparison/pilot-comfyui-corgi-puppy-0070.jpg" width="200" alt="Corgi, generation 70"><br>d = 0.420 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0070.jpg" width="200" alt="Christmas market, generation 70"><br>d = 0.423 | <img src="comparison/pilot-comfyui-dwayne-johnson-0070.jpg" width="200" alt="Dwayne Johnson, generation 70"><br>d = 0.383 | <img src="comparison/pilot-comfyui-mona-lisa-0070.jpg" width="200" alt="Mona Lisa, generation 70"><br>d = 0.403 |
| 80 | <img src="comparison/pilot-comfyui-tabby-cat-0080.jpg" width="200" alt="Cat, generation 80"><br>d = 0.389 | <img src="comparison/pilot-comfyui-corgi-puppy-0080.jpg" width="200" alt="Corgi, generation 80"><br>d = 0.433 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0080.jpg" width="200" alt="Christmas market, generation 80"><br>d = 0.434 | <img src="comparison/pilot-comfyui-dwayne-johnson-0080.jpg" width="200" alt="Dwayne Johnson, generation 80"><br>d = 0.370 | <img src="comparison/pilot-comfyui-mona-lisa-0080.jpg" width="200" alt="Mona Lisa, generation 80"><br>d = 0.415 |
| 90 | <img src="comparison/pilot-comfyui-tabby-cat-0090.jpg" width="200" alt="Cat, generation 90"><br>d = 0.381 | <img src="comparison/pilot-comfyui-corgi-puppy-0090.jpg" width="200" alt="Corgi, generation 90"><br>d = 0.441 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0090.jpg" width="200" alt="Christmas market, generation 90"><br>d = 0.442 | <img src="comparison/pilot-comfyui-dwayne-johnson-0090.jpg" width="200" alt="Dwayne Johnson, generation 90"><br>d = 0.362 | <img src="comparison/pilot-comfyui-mona-lisa-0090.jpg" width="200" alt="Mona Lisa, generation 90"><br>d = 0.413 |
| 100 | <img src="comparison/pilot-comfyui-tabby-cat-0100.jpg" width="200" alt="Cat, generation 100"><br>d = 0.383 | <img src="comparison/pilot-comfyui-corgi-puppy-0100.jpg" width="200" alt="Corgi, generation 100"><br>d = 0.448 | <img src="comparison/pilot-comfyui-berlin-christmas-market-0100.jpg" width="200" alt="Christmas market, generation 100"><br>d = 0.441 | <img src="comparison/pilot-comfyui-dwayne-johnson-0100.jpg" width="200" alt="Dwayne Johnson, generation 100"><br>d = 0.360 | <img src="comparison/pilot-comfyui-mona-lisa-0100.jpg" width="200" alt="Mona Lisa, generation 100"><br>d = 0.420 |
<!-- linkedin:end -->

## Prompt v3: steered drift toward a painting

Prompt v3 asks for an almost exact copy plus one very small step toward a post-impressionist oil painting. Over 100 generations the small steps should add up to a painted style. The five subjects above run again with v3, with the same model, seed and source. Compare each row with the v2 table above. The decision rule is in [IMPLEMENTATION.md](IMPLEMENTATION.md).

<!-- steered:start -->
| Run | Provider | Prompt | Generations | Refusals | Median time per generation | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Cat, v3 | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | 0 | 15.8 s (100 timed) | complete |
| Corgi, v3 | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | 0 | 15.5 s (100 timed) | complete |
| Christmas market, v3 | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | 0 | 15.4 s (100 timed) | complete |
| Dwayne Johnson, v3 | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | 0 | 15.4 s (100 timed) | complete |
| Mona Lisa, v3 | `comfyui-flux2-klein-4b-distilled` | prompt-v3 | 100 / 100 | 0 | 15.5 s (100 timed) | complete |

| Generation | Cat, v3 | Corgi, v3 | Christmas market, v3 | Dwayne Johnson, v3 | Mona Lisa, v3 |
| --- | --- | --- | --- | --- | --- |
| 0 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0000.jpg" width="200" alt="Cat, v3, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0000.jpg" width="200" alt="Corgi, v3, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0000.jpg" width="200" alt="Christmas market, v3, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0000.jpg" width="200" alt="Dwayne Johnson, v3, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0000.jpg" width="200" alt="Mona Lisa, v3, generation 0"><br>d = 0.000 |
| 10 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0010.jpg" width="200" alt="Cat, v3, generation 10"><br>d = 0.373 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0010.jpg" width="200" alt="Corgi, v3, generation 10"><br>d = 0.337 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0010.jpg" width="200" alt="Christmas market, v3, generation 10"><br>d = 0.347 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0010.jpg" width="200" alt="Dwayne Johnson, v3, generation 10"><br>d = 0.375 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0010.jpg" width="200" alt="Mona Lisa, v3, generation 10"><br>d = 0.340 |
| 20 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0020.jpg" width="200" alt="Cat, v3, generation 20"><br>d = 0.397 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0020.jpg" width="200" alt="Corgi, v3, generation 20"><br>d = 0.352 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0020.jpg" width="200" alt="Christmas market, v3, generation 20"><br>d = 0.395 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0020.jpg" width="200" alt="Dwayne Johnson, v3, generation 20"><br>d = 0.392 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0020.jpg" width="200" alt="Mona Lisa, v3, generation 20"><br>d = 0.373 |
| 30 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0030.jpg" width="200" alt="Cat, v3, generation 30"><br>d = 0.425 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0030.jpg" width="200" alt="Corgi, v3, generation 30"><br>d = 0.390 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0030.jpg" width="200" alt="Christmas market, v3, generation 30"><br>d = 0.432 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0030.jpg" width="200" alt="Dwayne Johnson, v3, generation 30"><br>d = 0.412 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0030.jpg" width="200" alt="Mona Lisa, v3, generation 30"><br>d = 0.411 |
| 40 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0040.jpg" width="200" alt="Cat, v3, generation 40"><br>d = 0.442 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0040.jpg" width="200" alt="Corgi, v3, generation 40"><br>d = 0.410 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0040.jpg" width="200" alt="Christmas market, v3, generation 40"><br>d = 0.451 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0040.jpg" width="200" alt="Dwayne Johnson, v3, generation 40"><br>d = 0.426 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0040.jpg" width="200" alt="Mona Lisa, v3, generation 40"><br>d = 0.440 |
| 50 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0050.jpg" width="200" alt="Cat, v3, generation 50"><br>d = 0.461 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0050.jpg" width="200" alt="Corgi, v3, generation 50"><br>d = 0.423 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0050.jpg" width="200" alt="Christmas market, v3, generation 50"><br>d = 0.463 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0050.jpg" width="200" alt="Dwayne Johnson, v3, generation 50"><br>d = 0.429 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0050.jpg" width="200" alt="Mona Lisa, v3, generation 50"><br>d = 0.452 |
| 60 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0060.jpg" width="200" alt="Cat, v3, generation 60"><br>d = 0.467 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0060.jpg" width="200" alt="Corgi, v3, generation 60"><br>d = 0.433 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0060.jpg" width="200" alt="Christmas market, v3, generation 60"><br>d = 0.472 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0060.jpg" width="200" alt="Dwayne Johnson, v3, generation 60"><br>d = 0.440 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0060.jpg" width="200" alt="Mona Lisa, v3, generation 60"><br>d = 0.459 |
| 70 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0070.jpg" width="200" alt="Cat, v3, generation 70"><br>d = 0.472 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0070.jpg" width="200" alt="Corgi, v3, generation 70"><br>d = 0.442 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0070.jpg" width="200" alt="Christmas market, v3, generation 70"><br>d = 0.476 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0070.jpg" width="200" alt="Dwayne Johnson, v3, generation 70"><br>d = 0.454 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0070.jpg" width="200" alt="Mona Lisa, v3, generation 70"><br>d = 0.467 |
| 80 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0080.jpg" width="200" alt="Cat, v3, generation 80"><br>d = 0.474 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0080.jpg" width="200" alt="Corgi, v3, generation 80"><br>d = 0.445 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0080.jpg" width="200" alt="Christmas market, v3, generation 80"><br>d = 0.474 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0080.jpg" width="200" alt="Dwayne Johnson, v3, generation 80"><br>d = 0.461 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0080.jpg" width="200" alt="Mona Lisa, v3, generation 80"><br>d = 0.470 |
| 90 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0090.jpg" width="200" alt="Cat, v3, generation 90"><br>d = 0.471 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0090.jpg" width="200" alt="Corgi, v3, generation 90"><br>d = 0.442 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0090.jpg" width="200" alt="Christmas market, v3, generation 90"><br>d = 0.472 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0090.jpg" width="200" alt="Dwayne Johnson, v3, generation 90"><br>d = 0.463 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0090.jpg" width="200" alt="Mona Lisa, v3, generation 90"><br>d = 0.472 |
| 100 | <img src="comparison/pilot-comfyui-tabby-cat-v3-0100.jpg" width="200" alt="Cat, v3, generation 100"><br>d = 0.469 | <img src="comparison/pilot-comfyui-corgi-puppy-v3-0100.jpg" width="200" alt="Corgi, v3, generation 100"><br>d = 0.445 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3-0100.jpg" width="200" alt="Christmas market, v3, generation 100"><br>d = 0.474 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3-0100.jpg" width="200" alt="Dwayne Johnson, v3, generation 100"><br>d = 0.468 | <img src="comparison/pilot-comfyui-mona-lisa-v3-0100.jpg" width="200" alt="Mona Lisa, v3, generation 100"><br>d = 0.471 |
<!-- steered:end -->

## Prompt v3 with img2img: really small steps

The first v3 runs jump to a full painting in generation 1. The cause is the graph: it paints every frame from pure noise, so the model redraws the whole image. The img2img graph ([comfy-flux2-klein-img2img.json](recreate-101/references/comfy-flux2-klein-img2img.json)) starts from the previous frame and removes only a little noise (denoise 0.25). One generation then changes the image by a very small amount (`d` about 0.01). The question is whether 100 small steps add up to a painted style. The cat with prompt v2 on the same graph is the control: it shows how much of the drift comes from the loop and not from the prompt. The decision rule is in [IMPLEMENTATION.md](IMPLEMENTATION.md).

<!-- img2img:start -->
| Run | Provider | Prompt | Generations | Refusals | Median time per generation | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Cat, v3 img2img | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 100 / 100 | 0 | 8.5 s (100 timed) | complete |
| Corgi, v3 img2img | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | 0 | Unavailable | running or stopped |
| Christmas market, v3 img2img | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | 0 | Unavailable | running or stopped |
| Dwayne Johnson, v3 img2img | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | 0 | Unavailable | running or stopped |
| Mona Lisa, v3 img2img | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v3 | 0 / 100 | 0 | Unavailable | running or stopped |
| Cat, v2 img2img (control) | `comfyui-flux2-klein-4b-img2img-d0.25` | prompt-v2 | 74 / 100 | 0 | 8.6 s (74 timed) | running or stopped |

| Generation | Cat, v3 img2img | Corgi, v3 img2img | Christmas market, v3 img2img | Dwayne Johnson, v3 img2img | Mona Lisa, v3 img2img | Cat, v2 img2img (control) |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0000.jpg" width="200" alt="Cat, v3 img2img, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-corgi-puppy-v3i-0000.jpg" width="200" alt="Corgi, v3 img2img, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-berlin-christmas-market-v3i-0000.jpg" width="200" alt="Christmas market, v3 img2img, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-dwayne-johnson-v3i-0000.jpg" width="200" alt="Dwayne Johnson, v3 img2img, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-mona-lisa-v3i-0000.jpg" width="200" alt="Mona Lisa, v3 img2img, generation 0"><br>d = 0.000 | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0000.jpg" width="200" alt="Cat, v2 img2img (control), generation 0"><br>d = 0.000 |
| 10 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0010.jpg" width="200" alt="Cat, v3 img2img, generation 10"><br>d = 0.168 | — | — | — | — | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0010.jpg" width="200" alt="Cat, v2 img2img (control), generation 10"><br>d = 0.143 |
| 20 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0020.jpg" width="200" alt="Cat, v3 img2img, generation 20"><br>d = 0.340 | — | — | — | — | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0020.jpg" width="200" alt="Cat, v2 img2img (control), generation 20"><br>d = 0.303 |
| 30 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0030.jpg" width="200" alt="Cat, v3 img2img, generation 30"><br>d = 0.378 | — | — | — | — | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0030.jpg" width="200" alt="Cat, v2 img2img (control), generation 30"><br>d = 0.369 |
| 40 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0040.jpg" width="200" alt="Cat, v3 img2img, generation 40"><br>d = 0.396 | — | — | — | — | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0040.jpg" width="200" alt="Cat, v2 img2img (control), generation 40"><br>d = 0.394 |
| 50 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0050.jpg" width="200" alt="Cat, v3 img2img, generation 50"><br>d = 0.404 | — | — | — | — | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0050.jpg" width="200" alt="Cat, v2 img2img (control), generation 50"><br>d = 0.409 |
| 60 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0060.jpg" width="200" alt="Cat, v3 img2img, generation 60"><br>d = 0.406 | — | — | — | — | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0060.jpg" width="200" alt="Cat, v2 img2img (control), generation 60"><br>d = 0.416 |
| 70 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0070.jpg" width="200" alt="Cat, v3 img2img, generation 70"><br>d = 0.409 | — | — | — | — | <img src="comparison/pilot-comfyui-tabby-cat-v2i-0070.jpg" width="200" alt="Cat, v2 img2img (control), generation 70"><br>d = 0.420 |
| 80 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0080.jpg" width="200" alt="Cat, v3 img2img, generation 80"><br>d = 0.412 | — | — | — | — | — |
| 90 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0090.jpg" width="200" alt="Cat, v3 img2img, generation 90"><br>d = 0.416 | — | — | — | — | — |
| 100 | <img src="comparison/pilot-comfyui-tabby-cat-v3i-0100.jpg" width="200" alt="Cat, v3 img2img, generation 100"><br>d = 0.417 | — | — | — | — | — |
<!-- img2img:end -->

## Niklaus Wirth experiment

![Sequential recreations of Niklaus Wirth](pilot-niklaus-wirth/evolution.gif)

The current animation uses the Codex image tool. The experiment targets 101 generations. The original photograph is by Tyomitch. See [the source and license notes](examples/README.md). The source and generated PNGs are in [the pilot directory](pilot-niklaus-wirth/). The GIF is a color-quantized viewing copy.

## ComfyUI local path

![Ten local recreations of Niklaus Wirth with FLUX.2 klein 4B](pilot-comfyui-niklaus-wirth/evolution.gif)

A second, fully local chain uses ComfyUI on the workstation GPU (RTX A2000, 8 GB). The model is FLUX.2 [klein] 4B distilled (Apache 2.0), with the same fixed prompt and only the previous frame as input. A generation takes about 15 s. The colours and the contrast grow with each generation. See [COMFYUI_PATH.md](COMFYUI_PATH.md) and [the run directory](pilot-comfyui-niklaus-wirth/). The driver is `recreate-101/scripts/comfy-chain.mjs`.

## Limburg Cathedral experiment

The second chain uses a CC BY-SA 3.0 photo of Limburg Cathedral by Norbert Nagel. It targets 100 generations with the same driver. See [its page](pilot-limburg-cathedral/README.md).

## Checkpoints and usage

The checkpoint table for this run is on [its own page](pilot-niklaus-wirth/README.md).

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

The project code is GPL-3.0-or-later. See [LICENSE](LICENSE). The images have their own terms, recorded in [examples/README.md](examples/README.md):

- Niklaus Wirth (Tyomitch): copyrighted free use; personality rights can apply.
- Limburg Cathedral (Norbert Nagel / Wikimedia Commons): CC BY-SA 3.0. The generated frames, GIFs and comparison thumbnails of both Limburg runs are adaptations under CC BY-SA 3.0.
- Alan Turing at age 16: public domain.
- Tabby cat and Corgi puppy (Pixabay authors via Commons): CC0 1.0.
- Berlin Christmas market (Arild Vågen / Wikimedia Commons): CC BY-SA 3.0. Its generated frames are adaptations under CC BY-SA 3.0.
- Dwayne Johnson (Harald Krichel / Wikimedia Commons): CC BY-SA 4.0. Its generated frames are adaptations under CC BY-SA 4.0. Personality rights apply: no endorsement or advertising use.
- Mona Lisa (Leonardo da Vinci): public domain.
