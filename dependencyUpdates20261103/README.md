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
| recognizer | Done | Commit 4360dc4 pushed. The local pipeline, CI, CodeQL, and Pages passed. |
| GermanDubI | Done | Commit 9487eea pushed. Local pipeline, container, CI and audit passed. |
| androidCatEars | Done | Commit dde262b pushed. Local gate, CI, CodeQL and Secret Scan passed. |
| myLastFmPlayer | Done | Commit 7e2cdec pushed. Local pipeline, CI and CodeQL passed. |
| DividendenDackel | Done | Commit 079d90f pushed. The local gate and all five GitHub CI jobs passed. |
| Raumfreund | Done | Commit 67aac6f pushed. The local gate, CI, and Docker workflow passed. |
| CroLingo | Running | Commits e3aee74 and ddf6290 are pushed. The local gate passed. GitHub checks are running. |
| GitLabTeamPulse | Waiting | — |

## Chronological log

| Date | Step | Result |
| --- | --- | --- |
| 2026-11-03 | Check AlliumAssault | Local tests and GitHub CI passed. TypeScript 7 exceeds the supported typescript-eslint range. |
| 2026-11-03 | Review codingWithGPT | Ten independent project updates were pushed. The latest GitHub checks passed. |
| 2026-11-03 | Change scope | Exclude codingWithGPT. Continue with the other repositories. |
| 2026-11-03 | Start recognizer | Update lucide-react 1.66.0 → 1.67.0 and vitest 5.0.5 → 5.1.0. The full local pipeline passed, including ten browser tests. Commit 4360dc4 was pushed. |
| 2026-11-03 | Check compatibility | TypeScript 7 and fast-uri 4 exceed consumer ranges. The latest Vite React plugin has a Babel peer conflict. |
| 2026-11-03 | Start GermanDubI | Update backend and frontend pins. Run the full pipeline in an isolated worktree. |

| 2026-11-04 | Complete GermanDubI | Commit 9487eea passed the local gate and GitHub checks. |
| 2026-11-04 | Complete androidCatEars | Commit dde262b passed the local gate and GitHub checks. The HTML coverage artifact was missing. The coverage gate passed. |
| 2026-11-04 | Complete myLastFmPlayer | Commit 7e2cdec passed the local gate and GitHub checks. The gate ran 613 tests with 99.01% coverage. |
| 2026-11-04 | Complete DividendenDackel | Commit 079d90f passed the local gate and all five GitHub jobs. The gate ran 684 tests. |
| 2026-11-04 | Complete Raumfreund | Commit 67aac6f passed the local gate, CI, and Docker workflow. The workflow published its verified image. |
| 2026-11-04 | Clean completed work | Removed task worktrees, temporary branches, isolated SDKs, and task-created Docker tags. Preserved the original checkouts and Docker image. |
| 2026-11-05 | Update CroLingo | Commit e3aee74 passed the local gate. GitHub CI found an incorrect OSV scanner checksum. |
| 2026-11-05 | Fix CroLingo bootstrap | Commit ddf6290 passed a clean bootstrap and the full local commit gate. Pushed both commits. GitHub checks are running. |

## Results and limits

Recognizer: npm audit reports four related low-severity entries through `vite-plugin-pwa`. The latest plugin-react release has a peer conflict. TypeScript 7 and fast-uri 4 exceed consumer ranges. CI, CodeQL, and Pages passed for commit 4360dc4.

CroLingo: the updated security scanners found no known SBOM vulnerabilities. The Linux window check confirmed 412 × 915 pixels. AGP 9.5 fails Android lint on Flutter integration-test code. AGP 9.4.1 passes. The version pin records when to retry 9.5.

## Resume here

1. Check `gh run list -R marcelpetrick/CroLingo --limit 5` for commit ddf6290.
2. Fix any failed checks and run the full gate before another push.
3. After all checks pass, remove `/home/mpetrick/repos/CroLingo-deps-20261104` and its temporary branch.
4. Remove `/tmp/cro-bootstrap-sdk-20261104` and other task-created temporary copies.
5. Inspect `/home/mpetrick/repos/GitLabTeamPulse` and its instructions.
6. Update its dependencies, run its full gate, push, and confirm GitHub checks.
7. Remove its task-created copies and commit the final update to this document.

CroLingo gate log: `/tmp/cro-fix-commit-20261104.log`. The isolated worktree owns its Flutter SDK. The owner authorized dependency pushes. This document remains a local commit.
