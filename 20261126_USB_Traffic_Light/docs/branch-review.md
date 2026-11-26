# Branch review

Base `origin/master` at `b9ddb0e`. Reviewed head `1d3f7c0`.
The project diff contains 21 files and 2,262 additions. The review covers only this project.

## Plan

1. Trace the status, USB, and release paths. Allow 10 minutes.
2. Reproduce each confirmed failure and add a test. Allow 10 minutes.
3. Fix confirmed findings and commit by requirement. Allow 20 minutes.
4. Verify a clean checkout and publish the approved commits. Allow 10 minutes.

## Status

| Time (CET) | Result |
| --- | --- |
| 17:12 | Found the merge base and read the project changes. |
| 17:13 | The monitor was running. The attached light reported green. |

## Resume here

Run the tests and release checks in [README.md](../README.md).
Inspect the reviewed changes with `git diff b9ddb0e...HEAD -- .`.

## Findings

| Rank | Severity | Category | Location at reviewed head | Finding | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | HIGH | Code | `agent_status.py:159` | A thread could vanish during a scan and hide a blocker already read. Malformed replies or repeated cursors could stop the scan. | Fixed in `11b59ed`. The regression tests preserve known red and yellow states. |
| 2 | MEDIUM | Code | `traffic_light.py:17` | Two units with one descriptor marker can share a by-ID symlink. The controller could select the wrong unit. | Fixed in `86383e6`. The fixture checks both ambiguity and explicit USB port selection. |
| 3 | MEDIUM | Code | `agent_status.py:256` | A stopped monitor left an old green or red signal on the light. | Fixed in `dcb7901`. The tests cover an interrupt, termination signal, dry run and absent device. |
| 4 | MEDIUM | Architecture | `tools/build_release.py:42` | A release build could include untracked notes or rules from the checkout. | Fixed in `2b3fba9`. The archive fixture confirms that both untracked files stay out. |
| 5 | MEDIUM | Architecture | `.github/workflows/check.yml` | GitHub discovers workflows at the repository root. The current project-local workflow only runs in a standalone repository. | Open. Moving it requires a change outside the project directory. |

[GitHub workflow discovery](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)

## Follow-up and verification

| Time (CET) | Result |
| --- | --- |
| 17:15 | Reproduced the Codex partial-read failure and the device-selection gap. |
| 17:17 | Fixed the four project findings and ran the clean-clone gate. |
| 17:20 | Added monitor version 0.2.0 and the display counts in `e8d6983`. |
| 17:21 | Verified that a reconnect adds a new display period in `65d496a`. |
| 17:21 | Repeated the full check from a clean checkout at `65d496a`. |

The clean checkout passed 36 tests. Coverage measured 296 of 296 executable lines.
The tests caught all 11 mutations. One mutant exposed a missing failed-write assertion, which the updated test caught.
The archive check passed both packaged entry points and SHA-256 verification.
The live dry run queried the four profiles and printed version 0.2.0 with one planned green period.
A separate process still owns the current monitor session on the host. Restart it to use the new code.

## Verdict

The fixes inside the project pass local verification. Hosted CI needs a root workflow.
The GitHub README link needs publication of the local commits.

## Second review

Base `origin/master` at `b9ddb0e`. Reviewed head `fc83c42`.
The project diff contained 23 files and 2,682 additions.

| Rank | Severity | Category | Location at reviewed head | Finding | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | MEDIUM | Code | `agent_status.py:217` | A failed quota refresh discarded a recently verified block and could turn red to green before reset. | Fixed in `bf702dc`. The tests cover a failed refresh, the window reset and the cache age limit. |
| 2 | MEDIUM | Code | `agent_status.py:315` | An interrupt during the first USB write could leave a color on because cleanup required a completed write. | Fixed in `bf702dc`. The test interrupts the first write and confirms the off command. |

The Codex schema from the installed client confirmed the wait flags and quota-limited goal states.
Both regression tests failed at the reviewed head.
The clean checkout at `bf702dc` passed 39 tests and covered 299 of 299 executable lines.
The tests caught all 13 mutations. The release archive and its checksums passed.
The live dry run printed version 0.2.1 and queried both Claude and both Codex profiles.
The hosted CI and GitHub publication decisions remain open.
