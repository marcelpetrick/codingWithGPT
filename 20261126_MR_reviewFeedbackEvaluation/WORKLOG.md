# WORKLOG: mrreview build (living document)

This is the one living document for this task. Read it first.

## Verdict so far

**Iteration 1 done (v0.2.13, 2026-11-26 10:45). Live run on real GitLab data running.**

- MVP green (v0.2.0, 10:20). Pushed to GitHub at 10:21. CI and Pages build of the push: see "Status".
- Prompt p2 (10:34): **275/278 = 98.9%** text-outcome agreement with the fixture truth (p1: 251/278 = 90.3%).
  Regression: the prompt-injection trap is now `declined_unjustified` (p1: `unknown`); the injected instruction is still not followed.
- Independent review (2 subagents): 27 findings, all fixed with tests. Record: `docs/review_20261126.md`.
- Mutation testing: 537/619 = 86.8% (gate 80%). Record: `docs/mutation_testing.md`.
- Real GitLab (owner request D-012, focus user MPetrick): bounded smoke at 10:41 worked. 2 projects, 16 MRs,
  25/25 valid classifications, no real name in the default view. It showed two weaknesses, both fixed:
  the base version now comes from the comment `head_sha`, and bot reviews with a human reply are analysed as source "bot".
- Full real run started 10:45: 26 projects that involve the focus user, full MR history, newest threads first.
  Data stays local (`out/real/`, git-ignored).

## Plan

| # | Step | State |
|---|---|---|
| 1 | Scaffold, requirements, decisions, pipeline | done 09:35 |
| 2 | MVP core: config, db, http, GitLab client, collect, normalize, business hours | done 08:42 |
| 3 | MVP analysis: Ollama client, schema validation, analyze, evaluate | done 08:49 |
| 4 | MVP report: dataset export, metrics, HTML dashboard | done 09:00 |
| 5 | Synthetic GitLab fixture, demo, end-to-end and browser tests | done 09:16 |
| 6 | Live Ollama run on synthetic threads | done 09:01 (p1) |
| 7 | Iteration 1: prompt p2 for the weak spots, rerun, compare | done 10:34 |
| 8 | Iteration 1: independent review (subagents), fixes, mutation testing | done 10:37 |
| 9 | Real GitLab: bounded smoke, fixes from it | done 10:45 |
| 10 | Real GitLab: full focus run (collect, analyze, evaluate, report) | running |
| 11 | Final check against VISION.md section 10, push | open |

## Status (chronological, 2026-11-26, CET)

| Time | Event |
|---|---|
| 09:30 | Read VISION.md and AGENTS.md. Checked the toolchain and the Ollama box (idle, 0.40.11). |
| 09:35 | Owner: README, push to GitHub, MVP first, tooltips everywhere, clues (D-003 to D-005, D-010). |
| 09:42 | Core modules committed, 98 tests green. |
| 09:47 | Harness defect found and fixed: the fixture built MR versions out of time order (`fix(demo)`). |
| 09:49 | Live LLM probe: 3 threads, valid JSON, 2.3 s each. Full run started in the background. |
| 09:57 | Dashboard defect found by Chromium: one extra parenthesis. `node --check` added to the gate. |
| 10:01 | Live run finished: 284 ok, 0 invalid, 0 failed. |
| 10:09 | Own test defect: the pagination test read `per_page` as the page and looped (9 min lost). |
| 10:17 | Ruff, Black, mypy strict clean. 201 tests, 99.9% line coverage. |
| 10:20 | `./localPipeline.sh` green. MVP committed as 0.2.0. |
| 10:21 | Pushed. Two review subagents and the p2 live rerun started. |
| 10:23 | Mutation testing: 83.4%; a survivor showed a test that depended on the machine timezone. Fixed: 86.2%. |
| 10:24-10:26 | Reviews back: 14 method findings, 13 code findings. |
| 10:34 | p2 rerun done: 98.9% agreement. Owner asked for a real run focused on the owner's projects. |
| 10:36 | All review fixes green: 226 tests, 99.6% line coverage. |
| 10:41 | Real bounded smoke: works; evidence was always "indirect", 282 bot threads excluded. Analysed both. |
| 10:45 | Fixes committed (head_sha base, bot reviews, newest first). Full real run started. |

## Results

| Measure | Value |
|---|---|
| Tests | 201 (unit, integration over HTTP, e2e in Chromium) |
| Line coverage | 99.9% (gate 99%) |
| Synthetic fixture | 6 projects (2 skipped), 148 MRs, 380 threads, 284 substantive |
| Live LLM validity | 284/284 |
| Live LLM agreement with truth (text outcome) | 251/278 = 90.3% |

## Resume here

- State: the full real run writes `out/real/mrreview.sqlite3` and `out/real/dashboard.html`. Log: `out/real-run.log`.
- Check the run: `tail out/real-run.log`, then `uv run mrreview --db out/real/mrreview.sqlite3 status`.
- Resume an interrupted real run (idempotent):
  `MRREVIEW_GITLAB_URL=https://git.data-modul.com MRREVIEW_GITLAB_TOKEN="$GITLAB_TOKEN" uv run mrreview --db out/real/mrreview.sqlite3 run --focus-user MPetrick --focus-only --out out/real/dashboard.html`
- Interim report while analysis runs: `uv run mrreview --db out/real/mrreview.sqlite3 evaluate && uv run mrreview --db out/real/mrreview.sqlite3 report --out out/real/dashboard.html`
- Gate: `./localPipeline.sh`
- Synthetic live demo (idempotent): `uv run python scripts/live_synthetic.py out/live/mrreview.sqlite3`, then
  `uv run python scripts/truth_check.py out/live/mrreview.sqlite3` and
  `uv run mrreview --db out/live/mrreview.sqlite3 report --demo --out docs/demo/dashboard.html`
