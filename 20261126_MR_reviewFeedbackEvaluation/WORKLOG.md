# WORKLOG: mrreview build (living document)

This is the one living document for this task. Read it first.

## Verdict so far

**Scope widening done (17:37): all 76 active projects (of 706 visible), 3,274 MRs, 5,578 threads classified (5,574 valid). All review findings fixed.**

- MVP green (v0.2.0, 10:20). Pushed to GitHub at 10:21. CI and Pages build of the push: see "Status".
- Prompt p2 (10:34): **275/278 = 98.9%** text-outcome agreement with the fixture truth (p1: 251/278 = 90.3%).
  Regression: the prompt-injection trap is now `declined_unjustified` (p1: `unknown`); the injected instruction is still not followed.
- Independent review (2 subagents): 27 findings, all fixed with tests. Record: `docs/review_20261126.md`.
- Mutation testing: 537/619 = 86.8% (gate 80%). Record: `docs/mutation_testing.md`.
- Real GitLab (owner request D-012, focus user MPetrick): bounded smoke at 10:41 worked. 2 projects, 16 MRs,
  25/25 valid classifications, no real name in the default view. It showed two weaknesses, both fixed:
  the base version now comes from the comment `head_sha`, and bot reviews with a human reply are analysed as source "bot".
- Full real run started 10:45 (restarted 10:46 with focus-first order): 26 projects that involve the focus user.
  Collection done 11:29: **1,637 MRs, 0 failed**; threads: 3,581 substantive, 490 bot reviews, 2,621 bot-only,
  1,389 author notes, 112 routine. 4,071 threads to classify (about 4.5 h at about 4 s each);
  the focus user's 2,960 threads (2,048 as giver, 912 as recipient) go first (about 3.3 h).
  Data stays local (`out/real/`, git-ignored).
- 11:55 interim report: works on real data (42 people, no real name in the default view, no script errors).
  It showed a defect: 89% "indirect" evidence. Cause: GitLab returns **empty diff lists for old MR versions**,
  and the collector booked them as complete. Fixed (12:03): such versions count as incomplete (migration 3 repairs
  stored data), and a new `evidence` stage uses the GitLab compare API from the commented commit to the final
  version. Real result: 1,955 diff comments, 1,106 changed later, 849 on the final version, 0 unavailable.
  Verified remediation in the interim report went from 1.6% to 18.4%.

## Plan

| # | Step | State |
|---|---|---|
| 1 | Scaffold, requirements, decisions, pipeline | done 09:35 |
| 2 | MVP core: config, db, http, GitLab client, collect, normalize, business hours | done 09:42 |
| 3 | MVP analysis: Ollama client, schema validation, analyze, evaluate | done 09:49 |
| 4 | MVP report: dataset export, metrics, HTML dashboard | done 10:00 |
| 5 | Synthetic GitLab fixture, demo, end-to-end and browser tests | done 10:16 |
| 6 | Live Ollama run on synthetic threads | done 10:01 (p1) |
| 7 | Iteration 1: prompt p2 for the weak spots, rerun, compare | done 10:34 |
| 8 | Iteration 1: independent review (subagents), fixes, mutation testing | done 10:37 |
| 9 | Real GitLab: bounded smoke, fixes from it | done 10:45 |
| 10 | Real GitLab: full focus run (collect, evidence, analyze, evaluate, report) | done 14:10 (4,060/4,071 valid) |
| 11 | Owner D-013: reaction-rate and decline columns (unsortable) | done 12:20 |
| 12 | Owner D-014: project pseudonyms in the name switch (REQ-UI-6) | done 12:20 |
| 13 | Owner D-015: chunked scope widening (`--max-minutes`, discovery reuse, `scripts/widen.sh`, AGENTS.md) | done 12:21 |
| 14 | Owner D-016: review of all documents (subagent): 18 findings, fixed; drift tests added | done 14:35 |
| 15 | Owner D-016: `/reviewBranch` over the whole project: 9 findings, all fixed | done 14:31 |
| 16 | Owner D-016: self-review from a clean GitHub clone: gate green (259 tests), CLI and demo work | done 14:40 |
| 17 | Owner D-016: profiling (see "Profiling" below): report did not finish in 1 h, now 8 s | done 14:26 |
| 18 | Owner D-018: database portable (backup before migrations, `db-pack`, `db-export`/`db-import`, pinned migration checksums) | done 12:25 |
| 18b | Fix all findings of steps 14 to 18, gate green, push | done 14:36 |
| 19 | After the focus run: final evidence, evaluate, report with current code | done 14:31 |
| 20 | `scripts/widen.sh` (steps 2 to 4, chunks of one hour); record each chunk | done 17:37 (one stop at 15:50 for low laptop memory, restarted 16:43) |
| 22 | Owner D-023/D-024: Opus annotation, prompt p5, fresh-sample check | done 10:10 |
| 23 | Owner D-025: per-developer reaction profile (REQ-UI-7) | done 11:05 |
| 24 | Owner D-026: project All/None, log scale; fix: dashboard showed only the current step's projects (REQ-UI-8) | done 11:05 |
| 25 | p5 reclassification of all threads; final report; README screenshot (Everyone view); figures in docs refreshed | running since 09:47 |
| 26 | Tone and thanks reliability against Opus; self-review; document review | open |
| 21 | Final check against VISION.md section 10 and docs/acceptance.md, push | done 17:40: all 10 criteria met; 4 open items need a person (see acceptance.md) |

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
| 10:46 | Restarted with focus-first order; collection resumed. |
| 10:48 | Pushed; CI green (both runs). |
| 11:29 | Real collection done: 1,637 MRs, 0 failed, 4,071 threads to classify. |
| 11:55 | Interim report: evidence almost always "indirect". Harness suspected first, confirmed: empty version diffs. |
| 12:03 | Compare-API evidence stage committed (mutation gate caught missing unit tests on the way: 77.8% → 85.8%). |
| 12:05 | Evidence stage on real data done; interim report regenerated. Analysis at 810/4,071. |
| 12:20 | D-013/D-014 (decline columns, project pseudonyms), 12:21 D-015 (chunks, widen.sh). |
| 12:25 | D-018 database portability; a migration edited after it ran was found and moved to migration 4. |
| 14:10 | Focus run done: 4,060/4,071 valid. |
| 14:26 | Profiling: report path 1 h+ → 8 s. |
| 14:31 | reviewBranch findings fixed (gate 256 tests); final focus report; widen.sh started. |
| 14:35 | Document review findings fixed; drift tests added. |
| 14:35 | Widening step 1 done (no new work). Step 2 (top 50 projects): collection 2,880 MRs, 0 failed. |
| 15:50 | Step 2 chunk 1 stopped at 780/1,364 threads. Claude Code stopped the chain: RAM 29/31 GiB, swap 26/33 GiB, mostly Firefox tabs. Database state is consistent: 4,848 classified, 2 failed. |
| 16:43 | Owner: continue. Chain restarted (RAM 7 GiB available). |
| 17:10 | Step 1 done: 6 new MRs, 594 threads (the step 2 leftovers included, analyze takes all open threads, focus first). |
| 17:13 | Step 2 done: 4 new MRs, 3 threads. Only 76 projects are active in the 12-month window, so steps 3 and 4 select the same 76. |
| 17:34 | Step 3 done: 26 more projects, 392 MRs, 140 threads (138 valid). |
| 17:37 | Step 4 done: 1 MR, 1 thread. `all steps done`, exit 0. |
| 18:15 | Harness check of the open outcomes: 390 open findings have a direct code change; the existing clue "Code changed, no reply" shows them (no defect). 4 failed threads: 3 had more than 5 findings, 1 hit the length limit (kept as failures). |
| 18:15 | Comparison with the Microsoft code review baselines: defect and maintainability shares match; learning-curve and size trends differ (proxy limits). `docs/literature_comparison.md`. |
| 18:20 | Placebo check of the direct-evidence rule: 91.7% hits at the commented line, 13.6% 50 lines away; no growth with MR size. `scripts/placebo_check.py`. Gate green. |
| 2026-11-27 08:50 | Self-check of the real dashboard in Chromium (all tabs, bot source): no script error, no external request. One defect: bot display names showed in the default view. Fixed (D-019, REQ-UI-6), test first; recheck: 0 real person, bot or project names. Gate green (260 tests). |
| 2026-11-27 09:16 | Owner OK (D-020): README screenshot of the real dashboard, default view. Page text checked for names and host, image inspected. |
| 2026-11-27 09:17 | Owner: Opus annotates instead of a person (D-023); works council not needed (D-021); business hours and palette stay approximations (D-022). |
| 2026-11-27 09:19 | Opus labelled 120 real findings blind. Qwen p2 agreement: outcome 51.7%, response 44.2%. Opus vs Opus: 85–90%. |
| 2026-11-27 09:27 | Own harness defect: a scratch file named dis.py shadowed the standard module; renamed. Findings first paired by position; re-scored by summary match. |
| 2026-11-27 09:43 | p3 (prose rules) did not improve; the adoption rule was then fixed in advance; p4 rejected by it; p5 (worked examples) adopted: outcome 56.7%, response 52.5% (D-024, docs/annotation_result.md). |
| 2026-11-27 09:47 | Full reclassification with p5 started (5,581 threads, widen chain). Final report generator: scripts/final_report.py. |

## Results

| Measure | Value |
|---|---|
| Tests | 259 (unit, integration over HTTP, e2e in Chromium), plus document drift checks |
| Line coverage | 99.1% (gate 99%) |
| Mutation score | 626/730 = 85.8% (gate 80%) |
| Synthetic fixture | 6 projects (2 skipped), 148 MRs, 401 threads, 305 substantive (incl. 21 bot reviews) |
| Live LLM agreement with truth (text outcome) | p2: 275/278 = 98.9%; p1: 251/278 = 90.3% |
| Real focus run | 26 projects, 1,637 MRs, 4,071 threads classified (4,060 valid), ~2.4 s per thread |
| Real widened run (all active projects) | 76 of 706 visible projects, 3,274 MRs, 5,578 threads (5,574 valid); outcomes: 1,822 implemented, 898 justified no change, 1,420 open, 454 optional declined, 217 declined without reason, 176 deferred |

## Profiling (14:20, real data, 4,071 threads)

| Stage | Time | Bottleneck | Action |
|---|---|---|---|
| collect | ~0.8 s per MR (1,637 MRs: 25 min) | GitLab round trips, one MR after another | Possible: fetch MRs in parallel (2-4 workers). Not done: the server is shared. |
| evidence | 1,955 compare calls in ~2 min | none | — |
| analyze | ~2.4 s per thread (4,071: 2 h 40 min) | the single GPU of the Ollama box | Focus-first and newest-first order; 1-hour chunks. Larger batches need server changes (not ours). |
| evaluate | 0.4 s | none | — |
| report | did not finish in 1 h, now **8 s** | name masking compiled ~200 regexes per text | One compiled pattern per name set; mask only the shown part. |

## Resume here (state at 2026-11-27 09:50)

The widen chain reclassifies all threads with prompt p5 (started 09:47, about 4 h). All stages are idempotent; restart with the command in step 2 below.
After it ends: `uv run python scripts/final_report.py out/real/mrreview.sqlite3 docs/final_report_inputs.json out/real/final_report.html`.

1. Close unused Firefox tabs. Check that `free -h` shows several GiB available.
2. Restart the chain:
   `systemd-inhibit --what=sleep:idle --why="mrreview scope widening" env MRREVIEW_GITLAB_URL=https://git.data-modul.com MRREVIEW_FOCUS_USER=MPetrick scripts/widen.sh >> out/widen.stdout 2>&1`
3. Look at `tail out/widen.log`. Step 1 is skipped quickly; step 2 continues at the open threads.

## Earlier resume point (state at 12:26, usage limit reached)

Done since the plan update: steps 11 to 13, step 15 (reviewBranch: 9 findings, open, `docs/review_20261126_branch.md`),
step 18 (database portability: migration backups, `db-pack`, `db-export`, `db-import`, pinned migration checksums).
Open, in this order:
1. Fix the reviewBranch findings 1 and 2 **before** `scripts/widen.sh` runs (outages must not be booked as results).
2. Step 14 (document review: restart the subagent), step 16 (clean-clone self-review), step 17 (profiling: script in WORKLOG history, real-DB copy via `db-pack`).
3. After the focus run ends (log line "report:"): `evidence`, `evaluate`, `report` with current code, then start `scripts/widen.sh`.
4. README screenshot of real data: only after the owner's explicit OK (public repository).


- State: the full real run writes `out/real/mrreview.sqlite3` and `out/real/dashboard.html`. Log: `out/real-run.log`.
- Check the run: `tail out/real-run.log`, then `uv run mrreview --db out/real/mrreview.sqlite3 status`.
- Resume an interrupted real run (idempotent):
  `MRREVIEW_GITLAB_URL=https://git.data-modul.com MRREVIEW_GITLAB_TOKEN="$GITLAB_TOKEN" uv run mrreview --db out/real/mrreview.sqlite3 run --focus-user MPetrick --focus-only --out out/real/dashboard.html`
- After the analysis: the running process ends with its own evaluate and report (older code). Then run
  `uv run mrreview --db out/real/mrreview.sqlite3 evidence`, `... evaluate`, `... report --out out/real/dashboard.html` with the current code.
- Interim report while analysis runs: `uv run mrreview --db out/real/mrreview.sqlite3 evaluate && uv run mrreview --db out/real/mrreview.sqlite3 report --out out/real/dashboard.html`
- Gate: `./localPipeline.sh`
- Synthetic live demo (idempotent): `uv run python scripts/live_synthetic.py out/live/mrreview.sqlite3`, then
  `uv run python scripts/truth_check.py out/live/mrreview.sqlite3` and
  `uv run mrreview --db out/live/mrreview.sqlite3 report --demo --out docs/demo/dashboard.html`
