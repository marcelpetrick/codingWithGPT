# Recreate 101 implementation

Verdict: implementation in progress. No paid image calls have been made.

## Plan

1. Build the skill and a sequential runner with a local mock provider.
2. Add the OpenAI image edit adapter and conservative accounting.
3. Test lineage, budget stops, recovery, and GIF output.
4. Run a three-generation pilot when an image and budget are available.

## Status

| Time | Step | Result |
| --- | --- | --- |
| 2026-11-09 | Plan | Started. |
| 2026-11-09 | Documentation | Checked official image API and pricing documentation. |

## Resume here

State: implementation in progress.
Check: `node --test recreate-101/tests/*.test.mjs`.
Restart: `node recreate-101/scripts/recreate.mjs --help`.
