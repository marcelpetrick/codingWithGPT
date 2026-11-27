# Acceptance check against VISION.md section 10

State: 2026-11-26 17:40, v0.2.38. Evidence is a test name, a command or a run record. "Met" means shown by evidence;
"partly" names what is missing.

| # | Criterion (VISION 10) | Status | Evidence |
|---|---|---|---|
| 1 | Discover projects without a list; prioritise active projects in the 12-month window; full history for selected projects | met | `test_discover_selects_and_skips`, `test_collect_full_history`; real run: 706 projects visible, 26 selected (focus), 1,637 MRs of full history; widening done: all 77 active projects, 3,281 MRs |
| 2 | Collect and link MRs, discussions, participants, code evidence; record gaps and coverage | met | `test_gaps_recorded`, `test_bounded_sample_is_recorded`; Methodology → Coverage |
| 3 | Separate substantive discussion from approval; findings, responses, decisions, outcomes independently | met | `tests/unit/test_textutil.py`, `test_normalize.py`, codebook in `llm.py`; p2: 98.9% agreement with the synthetic truth |
| 4 | Verified change vs promise vs resolution vs unknown; reasoned disagreement as legitimate | met | `test_decide`, `test_evaluate_on_fixture_truth`; clues "resolved, no code", "promised, not confirmed", "legitimate no-change" |
| 5 | Auditable business-hour and wall-clock metrics; unanswered never zero | met | `tests/unit/test_bizhours.py` (DST, holidays, foreign timezone), `test_timings_pending_is_never_zero`, `test_first_response_skips_routine_notes` |
| 6 | Batches through the configurable Ollama endpoint; schema-validated, evidence-linked results | met | `tests/integration/test_analyze.py`; live: 305/305 synthetic threads valid; real focus run 4,060/4,071 valid (11 invalid, retried); widened run 5,574/5,578 valid (p2); p5 rerun 5,590/5,595 valid |
| 7 | Resume after interruption without loss, duplicates or needless reprocessing | met | `test_resume_after_interruption`, `test_interrupted_analysis_resumes_without_rework`, `test_old_classification_key_is_upgraded`; the real run was stopped and resumed twice on 2026-11-26 (one stop for low laptop memory), with all earlier results reused |
| 8 | One offline, polished HTML dashboard with charts, filters, backlinks, default-pseudonymous toggle | met | `tests/e2e/test_dashboard_browser.py` (no network request, toggle, tooltips, drill-down, injection) |
| 9 | Verify aggregates, drill-down, identity display, browser rendering; report coverage and limits | met | KPI = Python metrics in Chromium (`test_kpis_match_python_metrics`); coverage states with reasons |
| 10 | Ruff, Black, pytest and integration/report checks pass; review and test evidence kept | met | `./localPipeline.sh` (283 tests, 99.1% lines, mutation 646/750 = 86.1%, v0.3.x), CI `mr-review-analytics`, `docs/review_20261126.md`, `docs/review_20261126_branch.md`, `docs/review_20261127.md` |

## Open items

| Item | Why open | Next step |
|---|---|---|
| Manual annotation sample on real data | Done with Opus instead of a person (D-023); Opus is a second model, not human truth | See docs/annotation_result.md |
| Organisational authorization (VISION 8) | Not needed for pseudonymised views (owner decision D-021); the real-name view stays confidential | — |
| Exact company brand values | Owner accepts the approximation (D-022) | — |
| Public holidays | Owner accepts the approximation (D-022) | `holidays` in the configuration file if needed |
