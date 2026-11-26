# Acceptance check against VISION.md section 10

State: 2026-11-26, v0.2.31. Evidence is a test name, a command or a run record. "Met" means shown by evidence;
"partly" names what is missing.

| # | Criterion (VISION 10) | Status | Evidence |
|---|---|---|---|
| 1 | Discover projects without a list; prioritise active projects in the 12-month window; full history for selected projects | met | `test_discover_selects_and_skips`, `test_collect_full_history`; real run: 706 projects visible, 26 selected (focus), 1,637 MRs of full history; widening to all active projects runs in 1-hour chunks |
| 2 | Collect and link MRs, discussions, participants, code evidence; record gaps and coverage | met | `test_gaps_recorded`, `test_bounded_sample_is_recorded`; Methodology → Coverage |
| 3 | Separate substantive discussion from approval; findings, responses, decisions, outcomes independently | met | `tests/unit/test_textutil.py`, `test_normalize.py`, codebook in `llm.py`; p2: 98.9% agreement with the synthetic truth |
| 4 | Verified change vs promise vs resolution vs unknown; reasoned disagreement as legitimate | met | `test_decide`, `test_evaluate_on_fixture_truth`; clues "resolved, no code", "promised, not confirmed", "legitimate no-change" |
| 5 | Auditable business-hour and wall-clock metrics; unanswered never zero | met | `tests/unit/test_bizhours.py` (DST, holidays, foreign timezone), `test_timings_pending_is_never_zero`, `test_first_response_skips_routine_notes` |
| 6 | Batches through the configurable Ollama endpoint; schema-validated, evidence-linked results | met | `tests/integration/test_analyze.py`; live: 305/305 synthetic threads valid; real focus run 4,060/4,071 valid (11 invalid, retried) |
| 7 | Resume after interruption without loss, duplicates or needless reprocessing | met | `test_resume_after_interruption`, `test_interrupted_analysis_resumes_without_rework`, `test_old_classification_key_is_upgraded`; the real run was stopped and resumed on 2026-11-26 |
| 8 | One offline, polished HTML dashboard with charts, filters, backlinks, default-pseudonymous toggle | met | `tests/e2e/test_dashboard_browser.py` (no network request, toggle, tooltips, drill-down, injection) |
| 9 | Verify aggregates, drill-down, identity display, browser rendering; report coverage and limits | met | KPI = Python metrics in Chromium (`test_kpis_match_python_metrics`); coverage states with reasons |
| 10 | Ruff, Black, pytest and integration/report checks pass; review and test evidence kept | met | `./localPipeline.sh` (259 tests, 99.1% lines, mutation 85.8%), CI `mr-review-analytics`, `docs/review_20261126.md`, `docs/review_20261126_branch.md` |

## Open items

| Item | Why open | Next step |
|---|---|---|
| Manual annotation sample on real data | Needs a human annotator with GitLab access | `mrreview sample`, rubric in `docs/annotation_rubric.md`, then `mrreview agreement` |
| Organisational authorization (VISION 8) | The owner started the real run (D-012) and holds this responsibility | Confirm with works council and data protection before the report is shared |
| Exact DATA MODUL brand values | Palette is an approximation (VISION 7.1) | Compare with the official Spectrum 2.0 design |
| Public holidays | Not excluded by default | Set `holidays` in the configuration file |
