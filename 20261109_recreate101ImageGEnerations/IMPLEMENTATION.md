# Recreate 101 implementation

Verdict: the skill and runner are available for a local mock run. The paid API path needs a pilot.

## Plan

1. Build the skill and a sequential runner with a local mock provider. Done.
2. Add the OpenAI image edit adapter and conservative accounting. Done, with the limits in the review.
3. Test lineage, budget stops, recovery, and GIF output. Done for the local mock path.
4. Run a three-generation pilot when an image, allowance, and reserve acceptance are available. Open.

## Status

| Time | Step | Result |
| --- | --- | --- |
| 2026-11-09 | Plan | Recorded the work. |
| 2026-11-09 | Documentation | Checked official image API and pricing documentation. |
| 2026-11-09 | Implementation | Added the skill, runner, mock provider, rate snapshot, and tests. |
| 2026-11-09 | Local test | Three mock generations produced four PNGs and a playable GIF. |
| 2026-11-09 | Checks | Four automated tests and skill validation passed. |
| 2026-11-09 | Review | Recorded open limits in `review_20261109.md`. No paid calls were made. |

## Resume here

State: waiting for the pilot image, USD allowance, and acceptance of an estimated request reserve. Strict mode cannot establish a provider-enforced maximum and blocks paid calls. Review current OpenAI model settings and prices before a paid run.

Check: `node --test recreate-101/tests/*.test.mjs`.

Validate: `python3 /home/mpetrick/.codex/skills/.system/skill-creator/scripts/quick_validate.py recreate-101`.

Local test: `node recreate-101/scripts/recreate.mjs run --input IMAGE --iterations 3 --provider mock --budget-usd 0`.

Paid pilot, after the required choices: `node recreate-101/scripts/recreate.mjs run --input IMAGE --iterations 3 --provider openai --model gpt-image-2 --size 1024x1024 --quality medium --budget-usd BUDGET --reserve-usd RESERVE --accept-estimated-reserve`.

## Updated plan: host-tool product

The user selected the Codex image tool and excluded Docker. The requested live test now has ten generations. The original source and every generated PNG remain in `pilot-niklaus-wirth/frames/`. The first request used the original JPEG. Later requests use only the previous generated PNG. The Codex host does not expose token usage or a per-call price here.

1. Save all ten host-tool generations in sequence. Running.
2. Build the GIF, retain the frames, and embed the GIF in the README. Open.
3. Validate the host checkpoint workflow and local pipeline. Running.
4. Review the branch and repository About text. Open.
5. Push the checked commits and inspect GitHub Actions. The existing unrelated local commit needs a push decision.

The repository uses `master` as its default branch. It has no `main` branch. The project is one directory inside the larger `codingWithGPT` repository. Docker work is excluded by the user.

## Ten-generation host test

The Codex image tool completed ten sequential generations. The saved GIF contains 11 frames and lasts 4.25 seconds. The first call used the JPEG source. Each later call used the preceding generated PNG. The lineage ledger was reconstructed after the calls. Per-call times, host tokens, and charges are unavailable. No direct API calls were made.

The PNGs and GIF are in `pilot-niklaus-wirth/`. The README embeds the GIF. The original photograph and permission information are in `examples/`.
