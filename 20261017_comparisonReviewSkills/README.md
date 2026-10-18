# Review skills compared: built-in `/code-review` vs own `/reviewBranch`

Living document for this task. Started 2026-10-17.

## Verdict (final, 16 runs on 4 fixtures)

**By the rule fixed beforehand, `/reviewBranch` stays the default:** cost is a tie (medians $0.86
vs $0.88) and `/code-review` fails the 50% precision gate (31 real of 71 reported = 44%, vs 10 of
11 = 91%, with 5 false findings vs 0). **But the rule did not weigh missed bugs, and that is where
`/reviewBranch` is weak.** On hr-doccontrol, where the owner's own later fixes (X23–X29) give a
ground truth, `/code-review` caught the high-severity error-dialog regression in 2/2 runs and a
safety-gate bug that let a document skip review in 4/4 runs. `/reviewBranch` caught the first in
1/2 and the second in 0/4 — it explicitly cleared that code three times and called the branch
mergeable.

**Recommendation:** keep `/reviewBranch` for everyday branches (short, verified, with a verdict),
but run `/code-review` as well on safety-relevant code and before a release, and triage its list.
Improve `/reviewBranch` with `/code-review`'s "removed-behaviour" angle (name the invariant each
deleted or bypassed check enforced and find where it is re-established): that angle is what
caught the safety-gate bug. Whether to change the decision rule itself to weigh recall of
high-impact defects is the owner's call for the next round.

## Question

Which review skill should be the default for branch reviews: the one built into Claude Code
(`/code-review`, Claude Code 2.1.302) or the self-written `~/.claude/skills/reviewBranch/SKILL.md`?
Compare on cost (tokens, turns, USD, wall time), outcome (findings, how many are real, how
precise), and form (output, ergonomics). Deliverable: an A4 PDF for a C-level reader (one page,
extended to two on 2026-10-17 at the owner's request), built from a broad HTML comparison and
then condensed.

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
- **Amendment 2026-10-17 22:57 (owner request, before any hr data):** a second repository,
  `~/repos/hr-doccontrol` (Python/Qt HR document-filing tool with a safety core; internal code on
  the company GitLab, so its transcripts and per-finding details stay local and git-ignored, only
  aggregates are published here), base branch `main`:
  - **F3 `hrsafety`** — commit `9dacfb1` "fix(safety): review findings of the safety core
    (X14-X21)" on its parent (18 files, +574/−48).
  - **F4 `hrsectionx`** — the 6-commit range `b026e3e..2dd0b80` (61 files, +2239/−177). The owner
    later reviewed this exact range and fixed X23–X29 in `ce6fdf8`; that list is the ground
    truth for recall.
- Arms: `RB` = `/reviewBranch`, `CR` = `/code-review` (no level given, i.e. its default).
- Each run: `claude -p "<skill>" --model claude-opus-5-5 --output-format stream-json --verbose
  --dangerously-skip-permissions --no-session-persistence`, fresh clone, `node_modules` symlinked
  so both arms can run tests equally. Same client version, same model, same machine state.
- n = 2 per arm and fixture (8 runs). One run is not a result.
- Measured per run from the final `result` event: turns, input/output/cache tokens (all models,
  including subagents, from `modelUsage`), `total_cost_usd`, wall time. Findings are parsed from
  the final report text of both arms (headless `/code-review` prints a numbered list; it does not
  call `ReportFindings`).
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

Times are commit times (`git log`), CEST.

| When        | Step                                                                 | State |
|-------------|----------------------------------------------------------------------|-------|
| 10-17 22:49 | Plan, decision rule, fixtures, runner committed                      | done  |
| 10-17 22:49 | AlliumAssault: 8 runs in parallel, one clone each (101–166 s)        | done  |
| 10-17 22:54 | Harness defect: extractor booked CR's findings as 0; fixed           | done  |
| 10-17 22:54 | AlliumAssault findings verified, first verdict, HTML, one-pager      | done  |
| 10-17 22:57 | hr-doccontrol: 2 fixtures × 2 skills × 2 runs launched               | done  |
| 10-17 23:00 | Independent review of the AlliumAssault round: 10 findings           | done  |
| 10-17 ~23:05| Usage limit hit: 2 hr runs (sectionx CR2, RB1) dead, quarantined     | done  |
| 10-18 03:42 | Review fixes: turn count, equal-TTL cost, `pre` class removed (CR now 58%) | done |
| 10-18 03:5x | Re-run of the 2 dead hr sessions, sequential                         | done  |
| 10-18 04:0x | hr findings verified (own + separate verifier agent, owner's X23–X29 as ground truth) | done |
| 10-18 04:1x | Final verdict over all 4 fixtures                                    | done  |
| —           | HTML and PDF (2 A4 pages) rebuilt from the final data                | open  |

## Results

Model `claude-opus-5-5`, Claude Code 2.1.302, n = 2 per cell, 16 valid runs. `/code-review` with
no level runs its **high** recipe (8 inline angles, dedup, no verify pass, "target at least 5
findings", "do not invent to hit the floor"); the captured prompt is in `skills/`.

| Fixture | Arm | USD (runs) | USD equal-TTL | Tokens k | Turns | Wall s | Reported | Real | Weak | False |
|---|---|---|---|---|---|---|---:|---:|---:|---:|
| gource     | RB | 0.61 / 0.60 | 0.48 / 0.46 | 498 / 383   | 11 / 9  | 101 / 109 | 1 / 3  | 1 / 2 | 0 / 1 | 0 |
| gource     | CR | 0.51 / 0.50 | 0.51 / 0.50 | 340 / 334   | 8 / 8   | 112 / 109 | 10 / 10 | 5 / 6 | 5 / 4 | 0 |
| factions   | RB | 0.84 / 0.81 | 0.66 / 0.64 | 878 / 1010  | 18 / 20 | 166 / 113 | 2 / 2  | 2 / 2 | 0 / 0 | 0 |
| factions   | CR | 0.64 / 0.64 | 0.64 / 0.64 | 768 / 691   | 16 / 13 | 141 / 123 | 9 / 9  | 5 / 6 | 4 / 3 | 0 |
| hrsafety   | RB | 0.92 / 0.88 | 0.71 / 0.68 | 980 / 1046  | 15 / 16 | 143 / 129 | 0 / 0  | 0 / 0 | 0 / 0 | 0 |
| hrsafety   | CR | 1.32 / 1.12 | 1.32 / 1.12 | 2549 / 2013 | 32 / 27 | 196 / 174 | 8 / 7  | 1 / 1 | 5 / 5 | 2 / 1 |
| hrsectionx | RB | 1.78 / 1.79 | 1.45 / 1.45 | 2857 / 2889 | 31 / 30 | 238 / 174 | 1 / 2  | 1 / 2 | 0 / 0 | 0 |
| hrsectionx | CR | 1.42 / 1.32 | 1.42 / 1.32 | 2511 / 2231 | 26 / 25 | 204 / 271 | 10 / 8 | 3 / 4 | 5 / 4 | 2 / 0 |

Totals: RB $8.23, 11 reported, 10 real (91%), 0 false. CR $7.46, 71 reported, 31 real (44%),
5 false. Medians per run: cost RB $0.86 / CR $0.88, wall time 136 s / 158 s, turns 17 / 20.5.

- **Cost is a tie.** CR is cheaper on the AlliumAssault fixtures and on hrsectionx, dearer on
  hrsafety. The raw gap on AlliumAssault is mostly a pricing artefact: RB runs in the main session,
  which writes 1-hour cache ($8/M), CR runs in a fork, which writes 5-minute cache ($5/M).
  Re-priced at the same rate ("equal-TTL"), RB is cheaper on 2 of 4 fixtures. Cache writes are
  42–60% of the cost on AlliumAssault, cache reads about 10%. Cache reads are 82–96% of the tokens.
- **Owner-known defects on hr-doccontrol** (ground truth `ce6fdf8`): the high-severity UI
  error-visibility regression — CR 2/2 (rank 1), RB 1/2; the medium OCR path defect — CR 2/2, RB
  2/2; the safety-gate defect (a set-aside naming rule drops its missing required fields, so a
  document can skip review; owner rated it low) — CR 4/4 runs on both fixtures that contain it, RB
  0/4. Four owner-known low items (packaging, exit wait, test log handler, facts refresh) were
  found by neither. RB matched the owner's severities exactly when it found the defect.
- **AlliumAssault**: the only MEDIUM defect (a faction falls back to the team index, so removing
  a team silently changes alliances) was found by both arms in 2/2 runs each. CR found every real
  defect RB found plus 9 more, all LOW (docs drift, duplication, a mislabelled toggle, three old
  AI/stats gaps). Detail: `results/verification.md`.
- **False findings**: 5, all from CR, all on hr-doccontrol (a separate verifier agent, spot-checked
  by hand: e.g. a "lost document at close" scenario that the GUI's cancel-before-close prevents).
- **Form**: RB states base + merge-base, gives severity and a merge verdict, and lists what it
  ruled out. Its verdict was wrong in 3 of 4 hr runs (mergeable while a known defect was present).
  CR gives no severity and no verdict; at the default level it does not verify (one run said so).

Caveats: two repositories, four fixtures, n = 2; the ground truth itself came from a later
AI-assisted review, so it is not independent; only CR's default level (high) was measured; the
two hr runs killed by the usage limit were re-run sequentially ~5 h later (`runs/dead/`); both
gource RB runs wrote frame grabs to the same `/tmp` path in parallel and may have read each
other's; real/weak is a judgement call (AlliumAssault CR precision moves about ±5 points on g11,
f3, g12). CR's diff fallback (`@{upstream}` → `main` → `HEAD~1`) has no `master` or merge-base
logic; on master-based AlliumAssault the model adapted, on a longer branch it may not.

## Resume here

State: runs, verification and results done; deliverables `comparison.html` (broad) and
`onepager.html` → `onepager.pdf` (A4, STE style).

```sh
cd ~/repos/codingWithGPT/20261017_comparisonReviewSkills
./run_all.sh; ./run_hr.sh        # idempotent: skips finished runs, re-runs usage-limit stops
python3 extract.py                # AlliumAssault -> results/metrics.json (public)
python3 extract.py --hr           # hr-doccontrol -> results/metrics_hr.json (git-ignored)
rm -rf runs/<run> && ./run_review.sh <gource|factions|hrsafety|hrsectionx> <RB|CR> <rep>
chromium --headless --no-pdf-header-footer --print-to-pdf=onepager.pdf onepager.html
```

Clones live in `/tmp/claude-1000/reviewcmp/` (RAM disk, disposable).
