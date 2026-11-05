# Public releases

Verdict: Work is in progress. Release one repository at a time.

Started: 2026-11-05, Europe/Berlin.

## Plan

1. Inspect the default branch, release instructions, version, and existing tags.
2. Prepare and verify the release according to the repository rules.
3. Publish the release and verify its release workflows and assets.
4. Record its URL and remove task-created temporary copies.
5. Continue with the next repository.

## Status

| Repository | State | Release |
| --- | --- | --- |
| AlliumAssault | Running | Tag v1.83.7 pushed. Release and Pages workflows are running. |
| recognizer | Waiting | — |
| GermanDubI | Waiting | — |
| androidCatEars | Waiting | — |
| myLastFmPlayer | Waiting | — |
| DividendenDackel | Waiting | — |
| Raumfreund | Blocked | Production signing secrets are missing from the release environment. |
| CroLingo | Blocked | A real target is required for integration tests before release. |
| GitLabTeamPulse | Waiting | — |

## Chronological log

| Date | Step | Result |
| --- | --- | --- |
| 2026-11-05 | Start release task | The owner requested public releases and a committed local record. |
| 2026-11-05 | Start AlliumAssault release | Default branch version 1.83.7 passed CI. Pushed tag v1.83.7. |
| 2026-11-05 | Check release prerequisites | CroLingo needs a real target. Raumfreund needs release signing secrets. Asked the owner for both. |

## Resume here

1. Check `gh run list -R marcelpetrick/AlliumAssault --limit 10` for tag v1.83.7.
2. Verify the release, its assets, and the Release and Pages workflows.
3. Record the release URL and continue with recognizer.

The owner authorized public releases and the required pushes. Keep unrelated local work intact.
