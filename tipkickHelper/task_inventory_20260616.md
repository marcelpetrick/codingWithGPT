# Task Inventory — 2026-06-16 Review Loop

Objective: run the repository review workflow on the active FIFA World
Cup 2026 prediction pool documents, using current match results through
15 June 2026 and preserving locked Strategy A.

## Master Tasks

| # | Title | Description | Expected deliverables | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | Initialize review loop | Convert the user workflow into an auditable task list and record execution order. | This task inventory; README/AGENTS file index updates. | User workflow paste; `AGENTS.md`, `pool_rules.md`, `strategy.md`. |
| 2 | Collect match results | Verify World Cup results played through 15 June 2026 and record scorers / material events. | Updated sources; prediction timeline with result and scoring audit. | Task 1; current authoritative match reports. |
| 3 | Review prediction performance | Compare submitted picks in `my_picks.md` against actual results and identify recurring errors. | Dated strategy review report with metrics, findings, and recommendations. | Task 2; Kicktipp 2/3/4 scoring rules. |
| 4 | Reconcile pick documents | Check `model_picks.md` and `my_picks.md` for necessary Strategy A changes after the results. | Pick-file updates only if favorites materially change; explicit note if `my_picks.md` changes. | Task 3; Strategy A lock. |
| 5 | Repository-wide verification | Validate formatting, links, dates, and unresolved inconsistencies after edits. | Final status check and local commit. | Tasks 1-4. |

## Execution Log

| Task | Status | Notes |
| --- | --- | --- |
| 1 | Complete | Task inventory created and registered in `README.md` / `AGENTS.md`; committed as `cf2bf2f`. |
| 2 | Complete | Results through 15 June verified and collected into `prediction_timeline.md`; scorer conflict for Qatar–Switzerland resolved to FIFA's Muheim own goal credit. |
| 3 | Complete | `StrategyReview20260616.md` added with corrected 19/64 audit and Strategy A calibration findings. |
| 4 | Complete | `pick_adjustment_watchlist.md` created; no scoreline changes made in `my_picks.md`, only locked-strategy wording cleanup. |
| 5 | In progress | Final repo-wide check and final commit still outstanding. |

## Per-Task Breakdown

### Task 1 — Initialize review loop

- Objective: create the master task document requested by the workflow.
- Source documents: `AGENTS.md`, `pool_rules.md`, `strategy.md`, `README.md`.
- External sources: none.
- Expected output: this file plus file-index updates.
- Execution order: first.

### Task 2 — Collect match results

- Objective: gather complete results for matches played through
  15 June 2026.
- Source documents: `my_picks.md`, `StrategyReview20260613.md`,
  `sources.md`.
- External sources: FIFA/ESPN schedule, AP/ABC, Guardian, FOX Sports,
  SBS, RotoWire match recaps.
- Expected output: `prediction_timeline.md`, `sources.md`.
- Execution order: second.

### Task 3 — Review prediction performance

- Objective: calculate points and identify prediction errors.
- Source documents: `pool_rules.md`, `strategy.md`, `my_picks.md`,
  `prediction_timeline.md`.
- External sources: same verified result sources as Task 2.
- Expected output: `StrategyReview20260616.md`, plus any small
  correction notes needed in earlier review files.
- Execution order: third.

### Task 4 — Reconcile pick documents

- Objective: decide whether any default picks need changes inside
  locked Strategy A.
- Source documents: `model_picks.md`, `my_picks.md`, `groups.md`,
  `strategy.md`, `StrategyReview20260616.md`.
- External sources: current result/standings reports and injury notes.
- Expected output: updated pick files only if a favorite materially
  changes; otherwise a hold recommendation.
- Execution order: fourth.

### Task 5 — Repository-wide verification

- Objective: check modified files, formatting, dates, and git state.
- Source documents: all modified files.
- External sources: none unless a link fails during validation.
- Expected output: local final commit and concise completion summary.
- Execution order: fifth.
