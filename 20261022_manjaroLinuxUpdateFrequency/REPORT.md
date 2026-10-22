# Manjaro stable update frequency (2026-10-22)

## Verdict

Yes, Manjaro stable has slowed down. The last stable update came on 2026-09-07, 45 days ago.
The usual rhythm is one update every ~2 weeks (median gap 15 d in 2026).
The cause is Manjaro, not Linux or Arch. The 2026-09-07 announcement put Manjaro into a
"frozen state" until the move from GitLab to Forgejo is done. No end date has been announced.
Arch builds more packages than usual. Unstable follows Arch, testing is 2–3 weeks behind,
stable is 6–7 weeks behind. Security fixes (Firefox, CA certificates) still reach stable.

Action for this laptop: `linux71` 7.1.13 is end of life. Move to `linux72` or keep `linux618` (LTS).

The one-pager is `onepager.pdf` (A4). It is generated from `data/` by `make_onepager.py`.

## Plan and status

| Time (2026-10-22) | Step | Status |
|---|---|---|
| start | Two research agents: stable announcement history; measurement sources and Arch lag | done |
| start | Local measurement from `/var/log/pacman.log` (`measure_local_waves.sh`) | done |
| +15 min | Branch lag script (`measure_branch_lag.sh`), output in `data/` | done |
| +25 min | A4 one-pager (`make_onepager.py` → `onepager.html`, `onepager.pdf`) | done |
| +35 min | Independent review of data, method, page; record in `review_20261022.md` | running |

## Results

- Local waves (days with ≥ 200 upgrades): median gap 20 d over 15 gaps since 2025-08.
  Earlier long pauses: 73 d (2025-09-29 → 2025-12-11), 53 d, 40 d. See `data/local_waves_20261022.txt`.
- Forum announcements since 2025-02: 36 stable updates, see `data/stable_announcements.csv`.
  Only one gap (73 d) is longer than the current 45 d.
- Branch lag on 2026-10-22: see `data/branch_lag_20261022.txt`.
  Example: systemd is 262.1 in Arch and unstable, 261.3 in testing, 261.2 (built 07-24) in stable.
- Packages built per week: Arch 1,000–1,800 in W40–W43; Manjaro stable 1–5 in W37–W41.
- Reasons from the forum: slow GitLab (2026-09-04, topic 189954), freeze (2026-09-07, topic 189985),
  maintainer has "super limited time" (2026-09-07/10). The "Manjaro 2.0 Manifesto" (2026-03-09,
  topic 186171) claims a loss of contributors and funds. This is one side's claim.
- Next likely stable update is large: Plasma 6.8 (SDDM → plasma-login-manager, X11 sessions retired),
  systemd 262, kernel 7.2/7.3.

## Sources

- https://forum.manjaro.org/c/announcements/stable-updates/12.json (and testing-updates/13, unstable-updates)
- https://forum.manjaro.org/t/189985 (freeze announcement)
- https://mirror.init7.net/manjaro/{stable,testing,unstable}/state and repo `.db` files
- https://geo.mirror.pkgbuild.com/{core,extra}/os/x86_64/ (Arch repo databases)
- https://www.kernel.org/releases.json, https://community.kde.org/Schedules/Plasma_6,
  https://docs.mesa3d.org/release-calendar.html, https://whattrainisitnow.com/
- Repology (manjaro_stable) returned HTTP 403 and was not used.

## Resume here

State: all data for 2026-10-22 is in `data/`. The page and report are current.

Check commands:

1. `curl -s https://forum.manjaro.org/c/announcements/stable-updates/12.rss | grep -m3 '<title>'`
2. `curl -s https://mirror.init7.net/manjaro/stable/state`

Refresh on a later day:

1. Add new stable announcements to `data/stable_announcements.csv`.
2. Run `./measure_local_waves.sh > data/local_waves_$(date +%Y%m%d).txt`.
3. Run `./measure_branch_lag.sh > data/branch_lag_$(date +%Y%m%d).txt`.
4. Update `data/upstream_calendar.csv` if releases happened.
5. Run `python3 make_onepager.py`. It uses the newest `data/*_YYYYMMDD.txt` files.
