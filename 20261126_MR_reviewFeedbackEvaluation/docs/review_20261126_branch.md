# reviewBranch 2026-11-26 (fa0fcf0..2f5747c, whole project)

Independent subagent review with the reviewBranch rules. All findings are verified by the reviewer. Status: **all fixed** (2026-11-26 14:31), tests in `tests/integration/test_review_fixes.py` and `test_server_dies_mid_run_stops_job`.

| # | Sev. | Where | Finding | Fix |
|---|---|---|---|---|
| 1 | HIGH | analyze.py, `_store_failure` on TransportError | Outages and timeouts count as attempts; after 3 a thread is dropped for good. Breaks "unreachable stops, never books". | Do not count transport errors; stop without a failure row. |
| 2 | MED | evidence.py | A temporary HttpError is booked as final "unavailable" and never retried; TransportError gives a raw traceback. | Only NotAccessible is final; others failed and retried; TransportError to StopRun. |
| 3 | MED | collect.py discovery reuse | Projects that are no longer visible keep their old rows and are selected again. | Mark rows not found as "not visible", or store the ranked list in meta. |
| 4 | MED | evaluate.py `run_evaluate` | Findings mix models and prompts; "current" is defined in three places. | One currency function, used by analyze, dataset and evaluate. |
| 5 | MED | gitlab.py `merge_requests` | Offset pagination sorted by updated_at can skip MRs updated during the listing. | Sort by id or created_at, or use keyset pagination. |
| 6 | LOW | analyze.py StopRun | Stop waits for running futures and discards their results. | Store finished results; cancel the rest. |
| 7 | LOW | analyze.py `cache_key` | The model digest is not in the key. | Add the digest. |
| 8 | LOW | collect.py `_ts` | A missing timestamp raises IntegrityError and stops collection. | Catch it per MR, book a gap. |
| 9 | LOW | cli.py `_budget` | `--max-minutes 0` means "no limit". | Test `is not None`. |
