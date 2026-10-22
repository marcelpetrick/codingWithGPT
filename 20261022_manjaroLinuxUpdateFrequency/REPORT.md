# Manjaro stable update frequency (2026-10-22)

## Verdict

Manjaro stable is paused, not slower. The last announced stable update came on 2026-09-07, 45 days ago.
Before the pause, the rhythm did not slow down. The median gap is 15 d in 2026 and 13 d over all gaps since 2025-02.
The cause is Manjaro, not Linux or Arch. The 2026-09-07 announcement starts a "frozen state".
The freeze lasts until the move from GitLab to Forgejo is done. No end date is announced.
Unstable follows Arch. Testing is 2–4 weeks behind. Stable is 6–7 weeks behind.
Stable still gets unannounced security fixes, for example Firefox, nss and CA certificates.

Action for this laptop: `linux71` 7.1.13 is end of life. Move to `linux72`, or keep `linux618` (LTS).

`make_onepager.py` generates the A4 one-pager `onepager.pdf` from `data/`.

## Plan and status

| Time (2026-10-22) | Step | Status |
|---|---|---|
| start | Two research agents: stable announcement history; measurement sources and Arch lag | done |
| start | Local measurement from `/var/log/pacman.log` (`measure_local_waves.sh`) | done |
| +15 min | Branch lag script (`measure_branch_lag.sh`), output in `data/` | done |
| +25 min | A4 one-pager (`make_onepager.py` → `onepager.html`, `onepager.pdf`) | done |
| +35 min | Independent review: 15 findings, see `review_20261022.md` | done |
| +60 min | Fix the review findings, then generate the page again | done |

## Results

- Forum announcements since 2025-02: 36 stable updates and 35 gaps (`data/stable_announcements.csv`).
  Only one gap is longer than the current 45 d: 73 d, from 2025-09-26 to 2025-12-08.
- Local update waves are days with 200 or more upgrades. Their median gap is 20 d over 15 gaps since 2025-08.
  Earlier long pauses on this laptop: 73 d, 53 d and 41 d. See `data/local_waves_20261022.txt`.
- Branch lag on 2026-10-22 is in `data/branch_lag_20261022.txt`.
  Example: systemd is 262.1 in Arch and unstable, 261.3 in testing and 261.2 in stable (built 07-24).
- Stable builds per week since the last announcement: W38 4, W39 1, W40 5, W41 3, W42 68, W43 141.
  W42 and W43 are unannounced security fixes.
- We cannot compare Arch week counts over time with this data. The repo keeps only current versions.
  To measure Arch activity, use dated snapshots from archive.archlinux.org.

Reasons in the forum:

1. The freeze lasts until the move from GitLab to Forgejo is done (2026-09-07, topic 189985).
2. GitLab was slow and broke kernel builds (2026-09-04, topic 189954).
3. GitLab now needs a sign-in to view (topic 189954).
4. The maintainer has "super limited time" (topic 189985).
5. The "Manjaro 2.0 Manifesto" (2026-03-09, topic 186171) claims a loss of contributors and funds.
   One side of a conflict wrote it.

The next stable update will be large: Plasma 6.8, systemd 262 and kernel 7.2/7.3.
With Plasma 6.8 in unstable, Manjaro's SDDM theme breaks. KDE recommends plasma-login-manager (topic 190649).

## Sources

- https://forum.manjaro.org/c/announcements/stable-updates/12.json (also testing-updates/13 and unstable-updates)
- https://forum.manjaro.org/t/189985 (freeze), https://forum.manjaro.org/t/190447 (linux71 EOL)
- https://mirror.init7.net/manjaro/{stable,testing,unstable}/state and the repo `.db` files
- https://geo.mirror.pkgbuild.com/{core,extra}/os/x86_64/ (Arch repo databases)
- https://www.kernel.org/releases.json, https://community.kde.org/Schedules/Plasma_6,
  https://docs.mesa3d.org/release-calendar.html, https://whattrainisitnow.com/
- Repology (manjaro_stable) returns HTTP 403. We do not use it.

## Resume here

State: all data for 2026-10-22 is in `data/`. The page and this report are current.

Check commands:

1. `curl -s https://forum.manjaro.org/c/announcements/stable-updates/12.rss | grep -m3 '<title>'`
2. `curl -s https://mirror.init7.net/manjaro/stable/state`

Refresh on a later day:

1. Add new stable announcements to `data/stable_announcements.csv`.
2. Check each entry in `data/status.json` against its forum topic. Remove `freeze` when it ends.
3. Run `./measure_local_waves.sh > data/local_waves_$(date +%Y%m%d).txt`.
4. Run `./measure_branch_lag.sh > data/branch_lag_$(date +%Y%m%d).txt`.
5. Update `data/upstream_calendar.csv` for new releases.
6. Run `python3 make_onepager.py`. It uses the newest `data/*_YYYYMMDD.txt` files.
