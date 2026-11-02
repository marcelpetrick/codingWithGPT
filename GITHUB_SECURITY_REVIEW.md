# GitHub security review

Verdict: GitHub reports 46 open Dependabot alerts in five repositories and two open code scanning alerts. The scan has large coverage gaps. Prioritize GermanDubI's critical certifi alert and its failing security audit.

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

## Dependabot pull requests

GitHub search found 46 open Dependabot PRs across 10 owned repositories. These include routine updates as well as security fixes. The inventory did not review all 46 PRs or establish that each fixes an alert. Review each diff and checks before merging.

## Resume here

State: Inventory complete. No repository settings, alerts, PRs, or dependencies were changed. GitHub alert data can change.

Check commands: `gh repo list marcelpetrick --limit 1000`; `gh api 'repos/marcelpetrick/GermanDubI/dependabot/alerts?state=open&per_page=100'`; `gh pr checks 6 -R marcelpetrick/GermanDubI`.

Restart commands: `cd /home/mpetrick/repos/codingWithGPT`; read this file; repeat the inventory with GitHub alert endpoints for each current owned repository.
