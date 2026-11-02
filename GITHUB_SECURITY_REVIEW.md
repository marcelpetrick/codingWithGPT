# GitHub security review

Verdict: Remediation is in progress. GitHub reports 46 open Dependabot alerts and two code scanning alerts. Prioritize GermanDubI and its failing security audit.

## Plan

1. List repositories owned by the authenticated account. Done.
2. Check open Dependabot, code scanning, and secret scanning alerts. Done.
3. Check open Dependabot pull requests and access limits. Done.
4. Rank actionable findings and record the evidence. Done.

## Status

| Time (CET) | Status |
| --- | --- |
| 2026-11-02 11:31 | Started the account-wide security inventory. |
| 2026-11-02 | Checked 119 owned repositories and 357 alert endpoints. |
| 2026-11-02 | Checked priority PR statuses and two failed CI logs. |

## Remediation plan

1. Check the current branches, repository rules, manifests, and quality gates. Allow 20 minutes.
2. Fix and verify the GermanDubI alerts and audit failures. Allow 90 minutes.
3. Fix and verify alerts in AlliumAssault, BavarianLemmings, recognizer, and the affected codingWithGPT project. Allow 2 hours.
4. Review the two test-only CodeQL findings. Allow 20 minutes.
5. Run the updateDependencies skill for each affected project. Commit only after its full gate passes. Allow 2 hours.
6. Report fixes, blocked checks, and alert coverage. Do not enable scanners yet. Allow 15 minutes.

## Remediation status — 2026-11-02

| Repository | State | Evidence |
| --- | --- | --- |
| codingWithGPT / ollama_northmini_jumpNRun | Done locally | Commit `02bb8cb`; `npm run ci` passed; `npm audit` found zero vulnerabilities. |
| BavarianLemmings | Done locally | Commit `d32b8eb`; full pipeline and Docker smoke passed; `npm audit` found zero vulnerabilities. |
| GermanDubI | Done locally | Commit `5a31dc3`; full pipeline passed; npm and default Python audits found no vulnerabilities. |
| AlliumAssault | Running | Worktree `/tmp/allium-security`; combined dependency and CodeQL fix gate `/tmp/allium-security-gate2.log`; npm audit clean. |
| recognizer | Done locally | Commit `e9207cc`; full gate passed on isolated port 4174; one low upstream deepmerge advisory remains. |
| CodeQL test alerts | Part done | LinkedIn fix committed as `6a77d0b`; its full pipeline passed. AlliumAssault test fix is in the running gate. |

The recognizer deepmerge advisory has no patched upstream version. It reaches build tooling through `vite-plugin-pwa`, `workbox-build`, and `@rollup/plugin-node-resolve`. The installed plugin calls deepmerge only to copy its own static defaults. This reduces exposure in the inspected build path. TypeScript 7 is outside the current typescript-eslint peer range. GermanDubI also requires TypeScript 5 for openapi-typescript. The latest recognizer React Vite plugin has an unresolved npm Babel peer conflict. No dependency commit is made until its full gate passes.

## Scope and coverage

- The inventory covers repositories owned by `marcelpetrick`. It includes 97 public repositories, 22 private repositories, and 11 forks. It excludes organization-owned repositories.
- Dependabot alerts were available for 54 repositories. GitHub reported alerts disabled for 65 repositories. A disabled scanner cannot establish that a repository has no vulnerable dependencies.
- Code scanning returned results for six repositories. GitHub reported no analysis for 91 and disabled scanning for 22. The latter 22 are private repositories.
- Secret scanning returned no open alerts for 36 repositories. GitHub reported it disabled for 83. This result does not prove there are no exposed secrets.
- The scan lists open GitHub alerts. It is not an independent dependency audit of each repository. Counts are a snapshot from 2026-11-02.

## Priority findings

1. [GermanDubI certifi alert](https://github.com/marcelpetrick/GermanDubI/security/dependabot/35): GitHub rates this critical. The advisory describes compromised intermediate CA keys and a possible on-path TLS interception. Its current text recommends certifi 2026.10.19 or later. [PR 6](https://github.com/marcelpetrick/GermanDubI/pull/6) proposes 2026.10.18, the first patched version, but its Node CI check fails. Review the version and fix the CI failure before merging. Rebuild any deployed images that include certifi.
2. GermanDubI has 26 Dependabot alerts: one critical, five high, 14 medium, and six low. These involve certifi, filelock, virtualenv, and setuptools. [PR 5](https://github.com/marcelpetrick/GermanDubI/pull/5) proposes filelock 4.2.1. [PR 4](https://github.com/marcelpetrick/GermanDubI/pull/4) proposes virtualenv 21.14.13. Both have a failed Node check. The [CI log](https://github.com/marcelpetrick/GermanDubI/actions/runs/41137299229/job/124342795735) reports nine pnpm audit vulnerabilities, including zod and undici advisories. These may not all appear in the Dependabot alert list.
3. [AlliumAssault](https://github.com/marcelpetrick/AlliumAssault/security/dependabot) and [BavarianLemmings](https://github.com/marcelpetrick/BavarianLemmings/security/dependabot) each have seven alerts. Each has four fast-uri alerts and three markdown-it alerts. GitHub marks two markdown-it alerts high. The flagged dependencies are development dependencies. [AlliumAssault PR 10](https://github.com/marcelpetrick/AlliumAssault/pull/10) proposes fast-uri 3.1.9 and its lint, test, build, and E2E check passed. Check the dependency path and markdown-it remediation separately.
4. [recognizer](https://github.com/marcelpetrick/recognizer/security/dependabot) has five development dependency alerts: four fast-uri alerts and one high undici alert. [PR 23](https://github.com/marcelpetrick/recognizer/pull/23) is a general update PR, not a confirmed fix for these alerts. Its quality check failed on desktop and mobile accessibility tests. Review the dependency paths and failing tests.
5. [codingWithGPT](https://github.com/marcelpetrick/codingWithGPT/security/dependabot/76) has one medium minimatch development dependency alert in `ollama_northmini_jumpNRun/package-lock.json`. Check the parent dependency and a compatible patched version.
6. GitHub labels two code scanning alerts high. Both are in test code. [codingWithGPT alert 19](https://github.com/marcelpetrick/codingWithGPT/security/code-scanning/19) flags a substring in an E2E test assertion. The test intercepts and aborts non-fixture requests. This is not evidence of a production URL authorization bypass. [AlliumAssault alert 1](https://github.com/marcelpetrick/AlliumAssault/security/code-scanning/1) flags an unescaped dot in a test locator regex. This is a test accuracy issue. Review both before dismissal or change.

## Optional model dependency audit

GermanDubI's default Python audit found no known vulnerabilities. An audit of all optional model packages found stanza 1.10.1 and torch 2.10.0 advisories. `argostranslate` 1.11.0 pins stanza 1.10.1 exactly. The upstream fix needs stanza 1.12.2 or later. Torch remains pinned to 2.10.0 for CUDA 12 compatibility. One torch advisory has no patched version, and the other requires 2.13.0. The repository already records both constraints and their recheck conditions in `docs/project/plan.md`. The optional stacks were not changed or tested with a GPU.

## Dependabot pull requests

GitHub search found 46 open Dependabot PRs across 10 owned repositories. These include routine updates as well as security fixes. The inventory did not review all 46 PRs or establish that each fixes an alert. Review each diff and checks before merging.

## Resume here

State: Remediation is running. See the status table for worktrees and gate logs. No scanner settings will change during this phase. GitHub alert data can change.

Check commands: `cat /tmp/allium-security-gate2.exit`; `tail -30 /tmp/allium-security-gate2.log`; `git -C /tmp/allium-security status --short`; `git -C /home/mpetrick/repos/GermanDubI status -sb`.

Restart commands: `cd /tmp/allium-security`; `npm audit --audit-level=moderate`; `npm run lint:reuse`; `npm run verify`. If all pass, commit the four changed files with `/tmp/allium-security-commit-message`. Keep the current `mpe/gource` checkout intact. No changes have been pushed.
