# Recreate 101

[![Recreate 101 checks](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/recreate-101.yml/badge.svg)](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/recreate-101.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)

Recreate an image repeatedly and watch the changes accumulate. Each generation uses only the previous image. The skill keeps the original, full-resolution PNG frames, a GIF, and a lineage record.

## Niklaus Wirth experiment

![Sequential recreations of Niklaus Wirth](pilot-niklaus-wirth/evolution.gif)

The current animation uses the Codex image tool. The experiment targets 101 generations. The original photograph is by Tyomitch. See [the source and license notes](examples/README.md). The source and generated PNGs are in [the pilot directory](pilot-niklaus-wirth/). The GIF is a color-quantized viewing copy.

## Limburg Cathedral experiment

The second chain uses a CC BY-SA 3.0 photo of Limburg Cathedral by Norbert Nagel. It targets 100 generations with the same driver. See [its page](pilot-limburg-cathedral/README.md).

## Checkpoints and usage

The table is generated from `pilot-niklaus-wirth/manifest.json` by `host.mjs readme`. Do not edit it by hand.

<!-- checkpoints:start -->
| Completed generations | Animation | Refusals so far | Codex agent tokens (calls with data) | Subscriber allowance |
| --- | --- | --- | --- | --- |
| 10 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0010.gif) | 0 | Unavailable | Unavailable |
| 20 | [Checkpoint GIF](pilot-niklaus-wirth/checkpoints/0020.gif) | 6 | 391118 in (284800 cached), 1186 out, 8 calls | Unavailable |
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
- `recreate-101/scripts/recreate.mjs` runs the mock or optional direct API provider.
- `localPipeline.sh` runs local checks.

The [vision](vision.md) defines the experiment. [IMPLEMENTATION.md](IMPLEMENTATION.md) records progress and restart commands. [review_20261109.md](review_20261109.md) records known limits.

## License

The project code is GPL-3.0-or-later. See [LICENSE](LICENSE). The example photograph has its own permission terms, recorded in [examples/README.md](examples/README.md).
