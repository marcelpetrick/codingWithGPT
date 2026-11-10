# AGENTS.md: Recreate 101

This file adds project rules to the repository `AGENTS.md`. Where they differ, this file applies.

## What this project is

Recreate 101 sends an image through a chain of image generations. Each generation uses only the previous frame. The chain is packed into a GIF. The main example is `pilot-niklaus-wirth/`.

## Files

- `recreate-101/SKILL.md`: the skill and the fixed prompt.
- `recreate-101/scripts/host.mjs`: the checkpoint ledger (`init`, `next`, `accept`, `refuse`, `target`, `encode`).
- `recreate-101/scripts/codex-chain.sh`: the driver. It starts one `codex exec` session for each generation.
- `recreate-101/scripts/recreate.mjs`: the mock and the direct API runner.
- `IMPLEMENTATION.md`: the living document. Read its "Resume here" section first.

## Rules

1. Use the fixed prompt without change. Never change the prompt to avoid a moderation block.
2. Use only the previous committed frame as the input. Never feed back a GIF frame.
3. Record every attempt in `usage.jsonl`, including refusals. Never delete a pending record to hide a call.
4. Stop after 3 consecutive refusals on the same frame. The owner decides what happens next.
5. Mark host charges and subscription allowance as unavailable, never as zero.
6. Do not edit `codex-chain.sh` while it runs. Write a `.new` file and rename it.
7. Generate the README checkpoint table with `host.mjs readme`. Do not edit it by hand.
8. Run `./localPipeline.sh` before each commit. It needs 95% line coverage.
9. Bump `VERSION` (semver) with each code change. Commit as you go. Push only on request.
