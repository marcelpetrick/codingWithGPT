# WORKLOG: mrreview build (living document)

This is the one living document for this task. Read it first.

## Verdict so far

**MVP done and green (v0.2.0, 2026-11-26 10:20).** The pipeline runs end to end on synthetic GitLab data,
with the stub and with the real LLM on `.67`. A live run on real GitLab data is blocked: there is no token
and no organisational authorization (VISION.md section 8, D-006).

Live LLM result on synthetic data (prompt p1, `qwen3.6:35b-a3b-q4_K_M-agentic`, Ollama 0.40.11):
284/284 schema-valid, about 2.3 s per thread, **251/278 = 90.3% text-outcome agreement with the fixture truth**.
Weak spots: declined nits (0/13 as `optional_declined`), partly done test requests (12/24 as `partial_claimed`).

## Plan

| # | Step | State |
|---|---|---|
| 1 | Scaffold, requirements, decisions, pipeline | done 09:35 |
| 2 | MVP core: config, db, http, GitLab client, collect, normalize, business hours | done 08:42 |
| 3 | MVP analysis: Ollama client, schema validation, analyze, evaluate | done 08:49 |
| 4 | MVP report: dataset export, metrics, HTML dashboard | done 09:00 |
| 5 | Synthetic GitLab fixture, demo, end-to-end and browser tests | done 09:16 |
| 6 | Live Ollama run on synthetic threads | done 09:01 (p1) |
| 7 | Iteration 1: prompt p2 for the weak spots, rerun, compare | open |
| 8 | Iteration 2: independent review (subagents), fixes, mutation testing | open |
| 9 | Final check against VISION.md section 10, push | open |

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

## Results

| Measure | Value |
|---|---|
| Tests | 201 (unit, integration over HTTP, e2e in Chromium) |
| Line coverage | 99.9% (gate 99%) |
| Synthetic fixture | 6 projects (2 skipped), 148 MRs, 380 threads, 284 substantive |
| Live LLM validity | 284/284 |
| Live LLM agreement with truth (text outcome) | 251/278 = 90.3% |

## Resume here

- State: MVP committed. Next is step 7 (prompt p2).
- Check: `./localPipeline.sh`
- Stub demo: `uv run mrreview demo --out out/demo`
- Live synthetic run (idempotent, about 12 min): `uv run python scripts/live_synthetic.py out/live/mrreview.sqlite3`
- Truth comparison: see the script in step 7 (to be added as `scripts/truth_check.py`).
- Rebuild the committed demo: `uv run mrreview --db out/live/mrreview.sqlite3 report --demo --out docs/demo/dashboard.html`
