# GitHub dependency updates

Verdict: AlliumAssault is complete. Recognizer is under review. Exclude codingWithGPT from further dependency work.

Started: 2026-11-03. Process one repository at a time. Times below use Europe/Berlin.

## Plan

1. Inspect the current repository, instructions, dependency files, and quality gates.
2. Check exact pins and query each upstream registry for stable releases.
3. Update compatible dependencies and install them in an isolated environment when needed.
4. Run the complete local quality gate.
5. Commit and push passing changes. Do not push unrelated work.
6. Confirm the GitHub checks pass before starting the next repository.

## Status

| Repository | State | Result |
| --- | --- | --- |
| AlliumAssault | Done | Compatible pins are current. The local gate and GitHub CI passed. No commit was needed. |
| codingWithGPT | Excluded | The owner removed this repository from the task. Earlier updates remain in its history. |
| recognizer | Running | Registry review started. The local checkout is clean. |
| GermanDubI | Waiting | — |
| androidCatEars | Waiting | — |
| myLastFmPlayer | Waiting | — |
| DividendenDackel | Waiting | — |
| Raumfreund | Waiting | — |
| CroLingo | Waiting | — |
| GitLabTeamPulse | Waiting | — |

## Chronological log

| Date | Step | Result |
| --- | --- | --- |
| 2026-11-03 | Check AlliumAssault | Local tests and GitHub CI passed. TypeScript 7 exceeds the supported typescript-eslint range. |
| 2026-11-03 | Review codingWithGPT | Ten independent project updates were pushed. The latest GitHub checks passed. |
| 2026-11-03 | Change scope | Exclude codingWithGPT. Continue with the other repositories. |
| 2026-11-03 | Start recognizer | Check package versions, compatibility, and the full pipeline. |

## Resume here

1. Run `git -C /home/mpetrick/repos/recognizer status --short --branch`.
2. Read `/home/mpetrick/repos/recognizer/AGENTS.md` and `package.json`.
3. Check package releases with `npm view PACKAGE version`.
4. Run `cd /home/mpetrick/repos/recognizer && ./localPipeline.sh --install`.
5. Check GitHub runs with `gh run list -R marcelpetrick/recognizer --limit 10`.
6. Continue with GermanDubI after recognizer is complete and GitHub checks pass.

The owner authorized pushing dependency commits. This README commit is local until explicitly pushed.
