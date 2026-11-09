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
