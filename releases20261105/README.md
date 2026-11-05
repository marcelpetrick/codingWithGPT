# Public releases

Verdict: All nine requested releases are public and verified. Raumfreund is a debug-signed release.

Started: 2026-11-05, Europe/Berlin.

## Plan

1. Inspect the default branch, release instructions, version, and existing tags.
2. Prepare and verify the release according to the repository rules.
3. Publish the release and verify its release workflows and assets.
4. Record each URL and remove task-created temporary copies.
5. Resolve any release blockers.

## Status

| Repository | State | Release |
| --- | --- | --- |
| AlliumAssault | Done | https://github.com/marcelpetrick/AlliumAssault/releases/tag/v1.83.7 |
| recognizer | Done | https://github.com/marcelpetrick/recognizer/releases/tag/v0.4.3 |
| GermanDubI | Done | https://github.com/marcelpetrick/GermanDubI/releases/tag/v0.5.6 |
| androidCatEars | Done | https://github.com/marcelpetrick/androidCatEars/releases/tag/v0.1.225 — unsigned AAB and debug APK. |
| myLastFmPlayer | Done | https://github.com/marcelpetrick/myLastFmPlayer/releases/tag/v0.0.200 |
| DividendenDackel | Done | https://github.com/marcelpetrick/DividendenDackel/releases/tag/v0.65.14 |
| Raumfreund | Done | https://github.com/marcelpetrick/Raumfreund/releases/tag/debug-v0.8.4-build91 — debug-signed APK. |
| CroLingo | Done | https://github.com/marcelpetrick/CroLingo/releases/tag/v0.0.87 |
| GitLabTeamPulse | Done | https://github.com/marcelpetrick/GitLabTeamPulse/releases/tag/v0.5.2 |

## Chronological log

| Date | Step | Result |
| --- | --- | --- |
| 2026-11-05 | Start release task | The owner requested public releases and a committed local record. |
| 2026-11-05 | Start AlliumAssault release | Default branch version 1.83.7 passed CI. Pushed tag v1.83.7. |
| 2026-11-05 | Check release prerequisites | CroLingo needs a real target. Raumfreund needs release signing secrets. Asked the owner for both. |
| 2026-11-05 | Publish recognizer | Published v0.4.3 from the verified default branch. This repository has no dedicated release workflow. |
| 2026-11-05 | Start release workflows | Started androidCatEars, myLastFmPlayer, and DividendenDackel. |
| 2026-11-05 | Publish myLastFmPlayer | Release v0.0.200 and its artifacts are public. Its release workflow passed. |
| 2026-11-05 | Verify CroLingo target | Found an active Linux desktop and audio device. Started integration tests with isolated documents. |
| 2026-11-05 | Prepare GermanDubI | `make check` passed. Pushed release notes commit 08e362b. |
| 2026-11-05 | Verify CroLingo | Five real Linux integration tests passed with isolated data. Started release workflow 42026421526. |
| 2026-11-05 | Prepare GitLabTeamPulse | Full local gate passed twice. Pushed release commit 0d7aa34. Restored the original Docker image tag. |
| 2026-11-05 | Publish GitLabTeamPulse | Main CI passed. Published v0.5.2 with wheel and source archive. The tag Docker workflow is running. |
| 2026-11-05 | Publish androidCatEars | The release workflow passed. Published v0.1.225 with its unsigned AAB, debug APK, and SBOMs. |
| 2026-11-05 | Finish GitLabTeamPulse | The tag Docker workflow passed. Removed its temporary worktree and build files. |
| 2026-11-05 | Fix DividendenDackel release | The workflow requires a dated changelog. Prepared v0.65.14 and started the full local gate. |
| 2026-11-05 | Tag GermanDubI | Main CI passed. Pushed annotated tag v0.5.6. |
| 2026-11-05 | Publish AlliumAssault | Release and Pages passed. Published v1.83.7 with web archive and checksum. Removed the temporary worktree. |
| 2026-11-05 | Publish GermanDubI | Published v0.5.6 with wheel and source archive. The container image builds are running. |
| 2026-11-05 | Retry DividendenDackel | Version 0.65.14 passed the local gate. A short commit ID caused checkout to fail. Restarted workflow 42029283775 with the full ID. |
| 2026-11-05 | Finish GermanDubI | The full release and container workflows passed. Removed its temporary worktree. |
| 2026-11-05 | Publish CroLingo | The signed release workflow passed. Published v0.0.87 with Android and Linux artifacts, SBOMs, and checksums. Removed its temporary worktree. |
| 2026-11-05 | Publish DividendenDackel | CI and release workflow passed. Published v0.65.14 with Android and Linux artifacts and checksums. Removed its temporary worktree. |
| 2026-11-05 | Check Raumfreund signing | The production release environment has no signing secrets. The local debug certificate matches the previous public debug release. |
| 2026-11-05 | Start Raumfreund debug release | The owner approved a debug-signed release. |
| 2026-11-05 | Publish Raumfreund | The dry run and release command passed. Published debug-v0.8.4-build91 with APK, checksum, and version file. Its certificate matches the prior release. Removed the temporary SDK and release files. |

## Resume here

The requested releases are complete. No release work remains in scope.

Check the final release with:

```sh
gh release view debug-v0.8.4-build91 -R marcelpetrick/Raumfreund
```

Raumfreund is debug-signed. AndroidCatEars includes an unsigned AAB and a debug APK. No task-created worktrees or SDK copies remain.
