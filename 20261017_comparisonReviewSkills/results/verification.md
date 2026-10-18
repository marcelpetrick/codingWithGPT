# Finding verification (2026-10-17)

Every finding of the 8 runs, merged into unique defects and checked by hand against the code at
the fixture's head (`git show <sha>:<path>`), plus `ffprobe` for the media claims.

Classes, as fixed in README before the runs: **real** = confirmed defect · **weak** = true, but
trivial, latent or taste · **false** = wrong or already handled. No finding was false.

Annotation **old**: a real defect whose behaviour already existed before the branch. It counts as
real (correction 2026-10-18, review finding 1: a first draft booked these as a fourth, not-real
class that was not in the pre-committed rule, and every such item was a `/code-review` finding).
`/reviewBranch` excludes such defects by its own scope rule; `/code-review` includes them ("bugs in
unchanged lines of a touched function are in scope").

## F1 `gource` (bac0bbb vs ed5235a: render script, legend helper, docs, 34 MB MP4s)

| ID  | Defect | Class | Sev | RB1 | RB2 | CR1 | CR2 | Evidence |
|-----|--------|-------|-----|-----|-----|-----|-----|----------|
| g1  | Noto font path hard-coded to Arch layout (`render-gource.sh:20`, `gource-legend.py:15`) | real | LOW | ✔ | ✔ | ✔ | ✔ | path literal; Debian uses `/usr/share/fonts/truetype/noto` |
| g9  | ~34 MB of MP4s committed to git, stale after every commit | real | LOW | | ✔ | ✔ | | 6 clips in `linkedin/`, no LFS |
| g6  | Gource family missing from `refresh-media` and MEDIA.md refresh recipe | real | LOW | | | ✔ | ✔ | MEDIA.md:70-76 lists no `render-gource.sh`; AGENTS.md:57 says "every media family" |
| g7  | Commit pacing implemented twice (two git log pipelines) | real | LOW | | | ✔ | ✔ | `render-gource.sh:31` and `coloured_log` |
| g10 | `docs/tasks.md` rows T165/T166 inserted above T164 | real | LOW | | | ✔ | ✔ | tasks.md:179-181 |
| g11 | `git log … 2>/dev/null` under `pipefail`: silent exit on git failure | real | LOW | | | | ✔ | `render-gource.sh:29-30` |
| g12 | MEDIA.md still says social videos are 1080×1350 H.264/AAC; new clips are 1920×1080 / 1080×1080, no audio | weak | — | | | | ✔ | true, but MEDIA.md:101 describes the capture-clip videos, not the new family |
| g2  | Needs bash ≥ 4.4 (`mapfile`, empty array under `set -u`) | weak | — | | | ✔ | ✔ | true; offline tool run on Linux |
| g3  | `-t 10` may cut the clip before the tree finishes; unchecked | weak | — | | | ✔ | ✔ | speculative; no evidence of a cut clip (RB2 checked one frame at 9.5 s only) |
| g4  | Custom log trusts A/M/D, no `|` in names, unquoted paths | weak | — | | | ✔ | ✔ | latent; RB1 checked history: only A/M/D, no quoted paths |
| g5a | `git ls-files` quoting puts non-ASCII names in wrong legend group | weak | — | | | ✔ | | latent; no such file exists |
| g5b | Legend counts from index, video from HEAD | weak | — | | ✔ | | | only differs with a dirty index |
| g8  | Two extension classifiers (awk colours, grep legend) can drift — CR2 #5 | real | LOW | | | | ✔ | same drift argument as g7 |
| g8b | `git ls-files` run 7× per render — CR1 #8 | weak | — | | | ✔ | | milliseconds |

## F2 `factions` (99fbe2e vs 9683621: tag-team factions in core, AI, UI, tests)

| ID  | Defect | Class | Sev | RB1 | RB2 | CR1 | CR2 | Evidence |
|-----|--------|-------|-----|-----|-----|-----|-----|----------|
| f1  | Unset faction falls back to team index; removing a team silently changes alliances | real | MED | ✔ | ✔ | ✔ | ✔ | `game.ts:291-293` `: team`; `menu.ts:611` splice re-indexes |
| f2  | "Custom name else `Faction n`" written three times (app, hud, menu) | real | LOW | ✔ | ✔ | ✔ | ✔ | app.ts:293, hud.ts:203, menu.ts:146 |
| f9  | Faction limit `4` repeated in game, settings, menu | real | LOW | | ✔ | ✔ | ✔ | game.ts:293, settings.ts:142/184, menu.ts:211 |
| f4  | Tag-team toggle shows `Off \| on`: pairs `opt.off` with `title.on` (sound-status key) | real | LOW | | | ✔ | | menu.ts:217-218; i18n.ts:32 vs :175; no `opt.on` key exists |
| f5  | Test hook gives `''` instead of `null` for an unnamed faction | weak | — | | | ✔ | ✔ | true; no consumer relies on null |
| f6  | `enemyWeight` allocates arrays + a Set per call in the AI hot loop | weak | — | | | ✔ | ✔ | true, unmeasured |
| f7  | HUD formats a faction name every update even with tag teams off | weak | — | | | ✔ | ✔* | trivial (*CR2 merged into its f2 item) |
| f8  | Friendly-fire condition in `stats.ts` longer than needed | weak | — | | | ✔ | ✔ | equivalent shorter form exists |
| f3  | `died()` credits a kill for killing an ally while damage is booked friendly | real, old | LOW | | | ✔ | ✔ | identical for own-team kills before the branch (`99fbe2e^:stats.ts:215`) |
| f10 | AI melee scoring ignores allies in reach | real, old | LOW | | | | ✔ | melee block unchanged by the branch (ai.ts:461-468) and never weighed teammates |
| f11 | AI torch/drill plans ignore allies on the path | real, old | LOW | | | | ✔ | same, ai.ts:406-425 |

## Per run (reported items, as each skill numbered them)

| Run | Reported | Real (of which old) | Weak | False | Found f1 (the MEDIUM bug) |
|-----|---------:|--------------------:|-----:|------:|:-------------------------:|
| gource_RB_1   | 1  | 1     | 0 | 0 | n/a |
| gource_RB_2   | 3  | 2     | 1 | 0 | n/a |
| gource_CR_1   | 10 | 5     | 5 | 0 | n/a |
| gource_CR_2   | 10 | 6     | 4 | 0 | n/a |
| factions_RB_1 | 2  | 2     | 0 | 0 | yes, rank 1 (as LOW) |
| factions_RB_2 | 2  | 2     | 0 | 0 | yes, rank 1 (as MEDIUM) |
| factions_CR_1 | 9  | 5 (1) | 4 | 0 | yes, rank 2 |
| factions_CR_2 | 9  | 6 (3) | 3 | 0 | yes, rank 4 |

Totals AlliumAssault: **RB** 8 reported, 7 real → precision **88%**; 5 unique real defects (g1, g9,
f1, f2, f9). **CR** 38 reported, 22 real → precision **58%**; 14 unique real defects (g1, g6, g7,
g8, g9, g10, g11, f1, f2, f3, f4, f9, f10, f11), a superset of RB's. Both: 0 false.
Scope-strict view (old defects left out of both numerator and denominator): CR 18/34 = 53%.
Judgement calls that move CR's precision by about ±5 points: g11 (marginal), f3, g12.
