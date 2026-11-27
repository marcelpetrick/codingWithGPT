# Requirements

Each requirement has a stable ID. Commits that implement or change one name the ID.
Source: `VISION.md` (section in brackets) and owner inputs in `docs/decisions.md`.
The acceptance check column names the test or command that shows the requirement is met.

| ID | Requirement | Acceptance check |
|---|---|---|
| REQ-COL-1 | Discover all projects the token can see, without a project list. Use read-only REST GET calls with pagination. [3] | `tests/integration/test_collect.py::test_discover_*` |
| REQ-COL-2 | Rank projects by MR activity in a rolling window (12 months default). Skip inactive projects for deep analysis, keep their metadata and the skip reason. [3] | `test_discover_selects_and_skips` |
| REQ-COL-3 | For selected projects, collect the full MR history: all states, discussions, notes, approvals, versions, version diffs, commits. [3] | `test_collect_full_history` |
| REQ-COL-4 | Keep project ID, name, full path, web URL, MR and note IDs, source links, original timestamps. Record API gaps and partial imports. [3] | `test_gaps_recorded`, `test_dataset_masks_names_in_text` (note links) |
| REQ-COL-5 | Separate human, bot, system and deleted-user activity. Do not count a note, discussion or approval twice. [3] | `tests/unit/test_identity.py`, `test_rerun_no_duplicates_and_no_refetch` |
| REQ-COL-6 | Retry with backoff, obey rate limits (429, Retry-After), checkpoint, refresh incrementally. Never write the token to logs or reports. [3] | `tests/unit/test_http.py`, `test_token_never_logged` |
| REQ-UNIT-1 | The unit is the review thread and the findings in it. A thread is substantive when a human note adds more than routine approval. Single comments without a reply count. [4] | `tests/unit/test_textutil.py`, `tests/unit/test_normalize.py` |
| REQ-UNIT-2 | Separate the review giver, the recipient, the responders and the implementer. Do not assume the MR author answers every comment. [4] | `test_roles_*` |
| REQ-CLS-1 | Classify intent, actionability and validity. The model can abstain. [4.1] | `tests/unit/test_llm.py::test_validate_*` |
| REQ-CLS-2 | Classify response acts and tone, with an uncertain category, an evidence reference and a short rationale. [4.2] | `test_validate_*` |
| REQ-OUT-1 | Keep acknowledgement, decision, implementation, thread resolution, merge and verified remediation apart. Grade verification: direct, indirect, textual only, unavailable. [4.3] | `tests/unit/test_evaluate.py` |
| REQ-OUT-2 | Judge outcomes against an observation cutoff. Mark recent open cases as censored. Keep deferral links. [4.3] | `test_censoring_*` |
| REQ-TIME-1 | Measure wall-clock and estimated business time (Mon-Fri 08:00-18:00, Europe/Berlin default, optional holidays). Handle DST. Never book an unanswered case as zero. [4.4] | `tests/unit/test_bizhours.py`, `test_timings_*` |
| REQ-LLM-1 | Use the existing Ollama REST API. URL, model, timeout, concurrency and options are configurable. [5] | `tests/unit/test_config.py`, `tests/integration/test_analyze.py` |
| REQ-LLM-2 | Treat GitLab content as untrusted data. Model output never starts commands, API writes or disclosures. [5] | `test_prompt_injection_is_data`, `test_client_is_read_only` |
| REQ-LLM-3 | Validate model output against a schema. Store provenance (model, digest, prompt and schema version, input hash, time). Reprocess only what changed. [5] | `tests/integration/test_analyze.py` |
| REQ-LLM-4 | Measure classification quality on a manually reviewed sample with a rubric and agreement figures. [5] | `mrreview sample` + `mrreview agreement`, `docs/annotation_rubric.md` |
| REQ-DB-1 | Store everything in local SQLite with migrations, transactions and stable IDs. [6] | `tests/unit/test_db.py` |
| REQ-DB-2 | Every stage resumes after an interruption without loss or duplicates. Work states are explicit: pending, done, stale, failed. [6] | `test_resume_after_interruption`, `test_interrupted_analysis_resumes_without_rework`, `test_rerun_no_duplicates_and_no_refetch`, `test_changed_thread_is_reclassified_only`, `test_failing_project_does_not_stop_the_others` |
| REQ-DB-3 | A report from partial data shows its coverage and the pending and failed work. [6] | `test_report_discloses_partial` |
| REQ-UI-1 | One self-contained static HTML file. No server, no CDN, no external fonts, no tracking. [7] | `tests/e2e/test_dashboard_browser.py::test_offline_and_no_errors` |
| REQ-UI-2 | Spectrum 2.0-inspired identity: white, deep blue headings, RGB gradient accents, semantic colours with text labels. [7.1] | browser screenshot in `docs/img/` |
| REQ-UI-3 | Sections: overview, projects, review effectiveness, participants, evidence, methodology. Filters for project, period, person and role. Drill-down to source links. A tooltip on every element that shows a number or a term (owner input D-003). Insight hints that point to patterns (owner input D-004). [7.2] | `test_dashboard_browser.py` |
| REQ-UI-4 | Every ratio shows numerator, denominator and unknowns. Use medians and percentiles. Guard small samples. No ranking, no score. [7.2] | `tests/unit/test_metrics.py`, browser cross-check |
| REQ-UI-5 | Pseudonymous labels by default. A toggle shows real names everywhere, including excerpts. [7.3] | `test_identity_toggle` |
| REQ-SEC-1 | No GitLab writes. No secrets in files, logs or reports. Escape all content in the HTML. [8] | `test_client_is_read_only`, `test_html_injection` |
| REQ-ENG-1 | Ruff, Black, mypy strict, pytest; at least 99% line coverage; mutation score at least 80% on the decision modules; CI runs the local pipeline. [9] | `./localPipeline.sh` |
| REQ-OPS-1 | A bounded live smoke test against GitLab and Ollama, gated by an explicit authorization flag. [9] | `mrreview smoke --authorized` |
| REQ-FOC-1 | Optional focus user: rank projects by the user's MRs as author or assigned reviewer; optionally analyse only those; open the dashboard on that person (owner input D-012). | `test_focus_user_ranks_and_filters`, `test_focus_flags` |
| REQ-UI-6 | The identity switch also covers projects: stable project pseudonyms by default in every view, and project paths and names in free text masked, so that screenshots of the default view can be shared (owner input D-014). Bot accounts get a pseudonym too, because a bot name can carry a project name (D-019). | `test_project_labels_are_stable_and_unique`, `test_mask_projects_in_text`, `test_project_names_follow_the_toggle`, `test_bot_names_follow_the_identity_toggle` |
| REQ-OPS-2 | Widen the scope step by step with Ollama work in chunks of one hour; every chunk resumes without loss (owner input D-015). | `test_time_budget_stops_cleanly_and_resumes`, `test_time_budget_exit_code`, `test_discovery_is_reused_within_a_day`, `scripts/widen.sh` |
