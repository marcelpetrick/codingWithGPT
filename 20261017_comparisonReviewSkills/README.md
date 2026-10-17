# Review skills compared: built-in `/code-review` vs own `/reviewBranch`

Living document for this task. Started 2026-10-17.

## Verdict

**Keep `/reviewBranch` as the default; run `/code-review` as a second pass before a merge that
matters.** By the rule fixed beforehand: cost is a tie (`/code-review` is 16–23% cheaper per
fixture, below the 25% bar), `/code-review` finds more real defects (11 vs 5 unique) but fails the
50% precision gate (47% vs 88%), so `/reviewBranch` stays the default. The margin is narrow:
neither skill reported a false finding, both found the one MEDIUM bug in all 4 of its runs, and
every extra real defect from `/code-review` was LOW (docs drift, duplication, a mislabelled
toggle). `/code-review` surfaces more, `/reviewBranch` decides more (base header, severity,
merge verdict).

## Question

Which review skill should be the default for branch reviews: the one built into Claude Code
(`/code-review`, Claude Code 2.1.302) or the self-written `~/.claude/skills/reviewBranch/SKILL.md`?
Compare on cost (tokens, turns, USD, wall time), outcome (findings, how many are real, how
precise), and form (output, ergonomics). Deliverable: an A4 one-page PDF for a C-level reader,
built from a broad HTML comparison and then condensed.

## Method

- Test repo: `~/repos/AlliumAssault` (TypeScript/Babylon.js game). The original is never touched:
  every run works in its own local clone under the session scratchpad, with `origin` removed so
  only the local `master` can serve as the base.
- Fixtures (each a branch `review/<name>` on top of a reset `master`):
  - **F1 `gource`** — the real current branch `mpe/gource` vs `master` (2 commits, 15 files,
    +389/−8; mostly a shell render script + media). A low-code branch.
  - **F2 `factions`** — commit `99fbe2e` "feat(core): add named tag-team factions and shared
    victory" replayed as a branch on its parent (21 files, +423/−34, game logic + tests). A
    code-heavy branch.
- Arms: `RB` = `/reviewBranch`, `CR` = `/code-review` (no level given, i.e. its default).
- Each run: `claude -p "<skill>" --model claude-opus-5-5 --output-format stream-json --verbose
  --dangerously-skip-permissions --no-session-persistence`, fresh clone, `node_modules` symlinked
  so both arms can run tests equally. Same client version, same model, same machine state.
- n = 2 per arm and fixture (8 runs). One run is not a result.
- Measured per run from the final `result` event: turns, input/output/cache tokens (all models,
  including subagents, from `modelUsage`), `total_cost_usd`, wall time. Findings extracted from
  the transcript (final text for RB, `ReportFindings` tool input for CR).
- Every finding is then verified by hand against the code: **real** (confirmed defect), **weak**
  (true but trivial / taste), **false** (wrong or already handled).

## Decision rule (fixed before the data)

- "Cheaper" = median cost ≥ 25% lower **and** non-overlapping ranges across the runs. Otherwise a
  tie.
- "Better outcome" = more **real** findings across both fixtures, ties broken by fewer false ones.
  A difference of one finding is a tie.
- Precision = real / reported. A skill whose precision is below 50% fails, whatever it finds.
- Default recommendation = the better outcome; if outcome ties, the cheaper one; if both tie, the
  one with the better output form for the owner's workflow.

## Status

| Time  | Step                                                    | State |
|-------|---------------------------------------------------------|-------|
| 22:50 | Plan, decision rule, fixtures defined                   | done  |
| 22:49 | 8 runs launched in parallel, one clone each             | done  |
| 22:52 | All 8 finished (101–166 s each), 0 errors               | done  |
| 22:55 | Harness defect: extractor booked CR's findings as 0 (`num_turns`=0, prose list); fixed, re-extracted | done |
| 23:10 | All 49 reported findings verified against the code      | done  |
| —     | Broad HTML comparison                                   | open  |
| —     | A4 one-pager HTML → PDF                                 | open  |

## Results

Model `claude-opus-5-5`, Claude Code 2.1.302, n = 2 per cell. `/code-review` with no level runs
its **high** recipe (8 inline angles, dedup, no verify pass, "target at least 5 findings"); the
captured prompt is in `skills/`.

| Fixture | Arm | USD (runs) | Tokens total (median) | Output tok | Turns | Wall s | Reported | Real | Weak | Pre |
|---|---|---|---:|---:|---|---|---:|---:|---:|---:|
| gource   | RB | 0.61 / 0.60 | 440 k | 8.4–8.7 k | 11 / 9  | 101 / 109 | 1 / 3  | 1 / 2 | 0 / 1 | 0 / 0 |
| gource   | CR | 0.51 / 0.50 | 337 k | 10.4–10.5 k | 9 / 9 | 112 / 109 | 10 / 10 | 5 / 6 | 5 / 4 | 0 / 0 |
| factions | RB | 0.84 / 0.81 | 944 k | 8.4–9.6 k | 18 / 20 | 166 / 113 | 2 / 2  | 2 / 2 | 0 / 0 | 0 / 0 |
| factions | CR | 0.64 / 0.64 | 730 k | 9.3–11.4 k | 17 / 14 | 141 / 123 | 9 / 9  | 4 / 3 | 4 / 3 | 1 / 3 |

- Totals: RB $2.86 for 7 real of 8 reported ($0.41 per real finding); CR $2.29 for 18 real of 38
  ($0.13 per real finding). Tokens are >90% cache reads in both arms.
- Unique real defects: RB 5, CR 11; CR's set contains all of RB's. Detail per finding:
  `results/verification.md`. Raw numbers: `results/metrics.json`. Transcripts: `runs/`.
- The only MEDIUM defect (f1: faction falls back to team index, so removing a team silently
  changes alliances) was found in 4/4 runs. RB rated it LOW once and MEDIUM once; CR ranked it 2nd
  and 4th, below a pre-existing kill-credit quirk.
- CR-only real finds: missing refresh recipe for the new media (g6), duplicated pacing (g7),
  tasks table order (g10), swallowed git stderr (g11), stale MEDIA.md format line (g12), `Off | on`
  toggle label (f4). CR also reported 3 pre-existing AI/stats gaps that RB's scope rules exclude.
- RB-only behaviour: states base branch + merge-base; checked claims empirically (pulled video
  frames, ran Prettier/markdownlint) and wrote what it ruled out; ends with a merge verdict.

Caveats: one repo, two already-merged fixtures, n = 2, headless mode, only CR's default level
(high); `low`, `max` and `ultra` were not measured. CR's diff fallback (`@{upstream}` → `main` →
`HEAD~1`) has no `master`/merge-base logic; here the model adapted (`HEAD~2` / `HEAD~1` happened
to be right), on a longer branch it may not.

## Resume here

State: runs, verification and results done; deliverables `comparison.html` (broad) and
`onepager.html` → `onepager.pdf` (A4, STE style).

```sh
cd ~/repos/codingWithGPT/20261017_comparisonReviewSkills
./run_all.sh                      # idempotent: skips runs whose transcript has a result event
python3 extract.py                # -> results/metrics.json, runs/*/findings.md
rm -rf runs/<run> && ./run_review.sh <gource|factions> <RB|CR> <rep>   # redo one run
chromium --headless --no-pdf-header-footer --print-to-pdf=onepager.pdf onepager.html
```

Clones live in `/tmp/claude-1000/reviewcmp/` (RAM disk, disposable).
