# Review skills compared: built-in `/code-review` vs own `/reviewBranch`

Living document for this task. Started 2026-10-17.

## Verdict so far

Pending — runs not done yet.

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
| —     | Build clones, run 8 sessions                            | open  |
| —     | Verify findings, tabulate                               | open  |
| —     | Broad HTML comparison                                   | open  |
| —     | A4 one-pager HTML → PDF                                 | open  |

## Results

Pending.

## Resume here

Pending — filled once the runner exists.
