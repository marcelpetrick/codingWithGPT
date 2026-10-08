# Flutter repositories under `~/repos`: timeline

All dates and times are Europe/Berlin (CEST, UTC+02:00). Inventory date:
2026-10-08.

## Verdict

Of 145 top-level Git repositories directly under `/home/mpetrick/repos`, exactly three currently
track a Flutter application:

1. **CroLingo** — offline-first Croatian learning for German-speaking families; Android and Linux.
2. **DividendenDackel** — local-first dividend and portfolio-event companion; Android and Linux.
3. **Raumfreund** — child-friendly room-noise traffic light; Android.

The other 142 top-level repositories do not contain a tracked `pubspec.yaml` whose current `HEAD`
declares `sdk: flutter`. A second audit of every object reachable from every local branch and tag
also found no deleted or historical Flutter project among those 142 repositories. Nested SDK
checkouts, generated build trees, caches, submodules and agent worktrees are not counted as the
owner's top-level repositories.

## At a glance

| Repository | GitHub created | First commit | Flutter since | Latest local commit | Commits | Current version | Targets | Release state |
|---|---|---|---|---|---:|---|---|---|
| [CroLingo](https://github.com/marcelpetrick/CroLingo) | 2026-08-07 10:00 | 2026-08-07 10:09 | 2026-08-07 10:47 | 2026-09-13 22:47 | 94 | `0.0.83+84` | Android, Linux | Latest GitHub release `v0.0.83`, published 2026-09-14 22:55 |
| [DividendenDackel](https://github.com/marcelpetrick/DividendenDackel) | 2026-08-22 19:39 | 2026-08-22 19:53 | From first commit | 2026-09-16 11:38 | 130 | `0.65.9+129` | Android, Linux | Latest GitHub release `v0.65.9`, published 2026-09-16 12:55 |
| [Raumfreund](https://github.com/marcelpetrick/Raumfreund) | 2026-10-03 19:10 | 2026-10-03 19:12 | 2026-10-03 19:19 | 2026-10-08 11:01 | 78 | `0.6.29+74` | Android | Latest public artifact is debug APK `0.6.25+70`; production release still blocked on signing and physical-device acceptance |

All three working trees were clean and their checked-out branches matched their local
`origin/<branch>` tracking refs at inspection time. CroLingo and DividendenDackel use `master`;
Raumfreund uses `main`. All three clones contain full, non-shallow history.

## Combined chronological timeline

| Date | Repository | Event |
|---|---|---|
| 2026-08-07 10:00 | CroLingo | GitHub repository created. |
| 2026-08-07 10:09 | CroLingo | Project history begins with `edd6722` (`initial commit`). |
| 2026-08-07 10:47 | CroLingo | Flutter Android/Linux targets bootstrapped in `3e4c85f`. |
| 2026-08-07 11:09–12:21 | CroLingo | Navigation shell, starter course, lesson player, SQLite progress, FSRS reviews and local statistics land. |
| 2026-08-07 19:18 | CroLingo | First GitHub release published: pre-release `v0.0.32`. |
| 2026-08-22 19:39 | DividendenDackel | GitHub repository created. |
| 2026-08-22 19:53 | DividendenDackel | First commit (`e148013`) scaffolds Flutter for Android and Linux; there is no pre-Flutter phase. |
| 2026-08-24 13:27 | DividendenDackel | First chronologically published GitHub release still listed, `v0.51.0`, adds live English, German and Croatian localization. |
| 2026-08-27 16:34 | DividendenDackel | The older `v0.45.2` tag (pointing to a 2026-08-23 commit) is published retrospectively. |
| 2026-08-28 | DividendenDackel | `v0.56.0`, `v0.58.0`, and `v0.60.2` releases advance networking and release/changelog behavior. |
| 2026-09-13 22:23 | DividendenDackel | `v0.61.8` published after the Android settings journey was hardened. |
| 2026-09-13 22:47 | CroLingo | Latest source commit, `66ec395`, adds accessible motion and celebrations; current version becomes `0.0.83+84`. |
| 2026-09-14 22:55 | CroLingo | Current latest release `v0.0.83` published. |
| 2026-09-16 12:55 | DividendenDackel | Current latest release `v0.65.9` published. Its source history ends the same day with release-safety documentation. |
| 2026-10-03 19:10 | Raumfreund | GitHub repository created. |
| 2026-10-03 19:12 | Raumfreund | Project history begins with vision and an unvalidated prototype archive (`30e1774`). |
| 2026-10-03 19:19 | Raumfreund | Pinned Flutter toolchain and Android skeleton added in `b3b2c96`. |
| 2026-10-04 16:13 | Raumfreund | Android noise-monitor release candidate lands. |
| 2026-10-04 17:18 | Raumfreund | First public debug APK release, `0.1.1+13`, published. |
| 2026-10-04–07 | Raumfreund | Rapid debug releases progress through `0.3.0`, `0.5.x`, and `0.6.x`; microphone, alarm, demo and release-readiness work continues. |
| 2026-10-08 10:24 | Raumfreund | Latest public debug APK, `0.6.25+70`, published. |
| 2026-10-08 11:01 | Raumfreund | Latest source commit, `e80ba82`; repository is at `0.6.29+74` and describes itself as a code-complete release candidate. |

## Per-project interpretation

### CroLingo

- GitHub creation preceded the root commit by about 9 minutes and Flutter by about 47 minutes.
- Recorded development span from first to latest commit: about **37.5 days**.
- Current source and latest release agree on `0.0.83`; the pubspec build number is 84.
- As of the inventory date, the last source commit was about **25 days** old.

### DividendenDackel

- GitHub creation preceded the first commit by about 14 minutes.
- It was a Flutter project from its first commit, making it the only one of the three with no
  separate pre-Flutter bootstrap period.
- Recorded development span from first to latest commit: about **24.7 days**, with 130 commits—the
  largest history of the three.
- Current source and latest GitHub release agree on `0.65.9`; the pubspec build number is 129.
- As of the inventory date, the last source commit was about **22 days** old.

### Raumfreund

- GitHub creation preceded the root commit by about 2 minutes and Flutter by about 8 minutes.
- Recorded development span from first to latest commit: about **4.7 days**, with 78 commits and 13
  public debug releases/tags—by far the most compressed development timeline.
- Current source (`0.6.29+74`) is four commits/builds ahead of the latest public debug APK
  (`0.6.25+70`).
- It is the only Android-only Flutter repo and the only one without a production release; its README
  requires production signing and physical-device acceptance evidence first.

## Method and evidence rules

- **Scope:** immediate child directories of `/home/mpetrick/repos` containing `.git`; 145 were found.
- **Flutter:** a `pubspec.yaml` tracked at `HEAD` contains an SDK dependency matching
  `sdk: flutter`. This avoids false positives from documentation mentions and untracked SDK/build
  output.
- **Historical Flutter:** every `pubspec.yaml` blob reachable through `--all` local refs was also
  inspected for `sdk: flutter`. The same three repositories matched; there was no historical-only
  match.
- **GitHub created:** GitHub API `createdAt`, queried with `gh repo view`. This is distinct from the
  project's first commit.
- **First commit:** root commit reachable from the checked-out `HEAD`, using
  `git rev-list --max-parents=0 HEAD`; all three repositories are non-shallow.
- **Flutter since:** earliest commit affecting `pubspec.yaml`, verified as the Flutter bootstrap
  commit. In all three histories that file began as Flutter, so no later conversion search was
  needed.
- **Latest activity:** checked-out `HEAD` commit. Working-tree timestamps are not substituted for
  version-control history.
- **Releases:** GitHub release publication dates from `gh release list`; local annotated tag dates
  are not treated as publication dates.

The local Git history proves project history, not when an idea was first conceived or when an
uncommitted prototype was made. GitHub `createdAt` proves repository creation on GitHub, not a
possibly earlier local directory creation.

## Plan and completion

| Step | State | Actual |
|---|---|---:|
| Inventory Git repositories and Flutter project markers | Done | 3 min |
| Derive creation, first Flutter, release, and latest-activity dates | Done | 6 min |
| Cross-check local history against GitHub metadata | Done | 4 min |
| Review definitions, counts, branches, cleanliness and shallow-clone risk | Done | 3 min |
| Audit all reachable branches, tags and deleted file versions for historical Flutter use | Done | 2 min |

## Chronological status

| Time (Europe/Berlin) | Status |
|---|---|
| 2026-10-08 | Started the repository inventory and fixed the definitions of “Flutter” and “created”. |
| 2026-10-08 | Found 145 top-level Git repositories and classified 3 as current Flutter projects. |
| 2026-10-08 | Reconstructed root commits, Flutter bootstrap commits, versions, tags and latest commits. |
| 2026-10-08 | Cross-checked GitHub repository creation and published release dates. |
| 2026-10-08 | Verified all three clones are full, clean, and aligned with their local tracking refs. |
| 2026-10-08 | Confirmed no additional current or historical Flutter repo exists in any reachable local ref. |

## Resume here

State: complete. The inventory found CroLingo, DividendenDackel and Raumfreund; no remaining analysis
step is open.

Check commands:

```bash
rg -l --hidden 'sdk:[[:space:]]*flutter' /home/mpetrick/repos \
  -g pubspec.yaml -g '!**/.dart_tool/**' -g '!**/build/**' -g '!**/.pub-cache/**'
git -C /home/mpetrick/repos/CroLingo log --reverse --follow -- pubspec.yaml
git -C /home/mpetrick/repos/DividendenDackel log --reverse --follow -- pubspec.yaml
git -C /home/mpetrick/repos/Raumfreund log --reverse --follow -- pubspec.yaml
gh release list --repo marcelpetrick/CroLingo
gh release list --repo marcelpetrick/DividendenDackel
gh release list --repo marcelpetrick/Raumfreund
```

Restart command:

```bash
cd /home/mpetrick/repos/codingWithGPT
```
