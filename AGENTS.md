# AGENTS.md: how to work in this repository

This repository is a collection of small, independent projects, one per directory. A project's own
`AGENTS.md` / `agents.md` / `CLAUDE.md` takes precedence over this file where they differ
(`tipkickHelper/`, `boldemort_markdownToUnicodeConverter/`, `claudeCodeInit/` have one).

These rules are the owner's working style, written down from the 2026-09-24/25 benchmark round
(`ollamaClaudeCode_v4_tielCoder/ROUND_2026-09-24.md`). They apply to any multi-step task here.

## Working style

- **Results over narration.** Short status lines, then act. No thinking out loud, no apologies, no
  restating the plan in every message. When asked "where are we", answer with a table: done / running
  / left, with times.
- **Plan, then execute, then keep going.** Write the plan down (in the living document, see below),
  run it without waiting for approval of each step, and continue until done. Ask only when a decision
  is genuinely the owner's: an irreversible action, a change on shared infrastructure, or a real
  trade-off between goals.
- **One living document per task, and say its name.** Keep it current after every step. It holds the
  verdict so far, the plan with times, a chronological status table, the results, and a
  **"Resume here"** section with the state, the check commands and the exact restart commands, so
  the work can be picked up on another day.
- **Atomic commits.** One logical change per commit, and commit as you go, not at the end. The
  message says why, not just what. Commit on the current branch unless told otherwise, and never
  push without being asked.
- **Dashboards follow the data.** If there is a dashboard, it is generated from the result files
  (never hand-edited), regenerated after every stage, sortable, and every column and every
  model/entity has an (i) explanation of up to five sentences.
- **Keep the owner's shared resources intact.** Do not upgrade, reconfigure or restart shared
  servers mid-measurement. Record such changes as "after the round" items.

## Evaluating things (models, tools, libraries)

- **Pre-evaluate on the web before spending compute.** Check the card, the community tab, independent
  measurements and issue trackers, and treat vendor numbers as claims. Do not test weak candidates
  ("don't even test crap"): keep a register with three lists (testable, known but not fitting, and
  blocked with a recheck condition), each entry with its evidence and date. Check the register before
  pulling anything.
- **Best first, one at a time.** Rank the testable candidates, run the most promising first, and
  update the document and dashboard and commit after each one. If a result changes the ranking,
  re-rank before the next run.
- **Fix the decision rule before the results.** Every threshold is a number ("clearly faster" =
  median ≥ 25% lower and non-overlapping ranges), written down and committed before the data exists.
  Overlapping confidence intervals are a tie, not a ranking.
- **Suspect the harness first.** Every failure is analysed before it is believed. A result that
  looks like a model scoring badly has repeatedly been our own defect: a dead session booked as
  3/18, a failed load booked as a spill, an empty read booked as a wrong file, a stale log line
  read as "done", a pattern matching its own wrapper. Read the transcript, then decide.
- **Control the confounds.** Same client version, same sampler policy, same server state for every
  compared model. Record versions per row. Label A/B arms so they never pool with the main data.
- **Review your own work.** At the end of a round, run an independent review (code, method,
  documents; pedantic), verify every finding, record it as `review_YYYYMMDD.md` with a status per
  finding (fixed with commit / scheduled / open), and fix what is real.

## Long-running jobs

- Launch them detached (`setsid nohup … & disown`), under `systemd-inhibit` so the laptop cannot
  sleep, and make every step **idempotent**, so re-running resumes rather than repeats.
- Run dependent jobs as **one sequential chain**. `pgrep` polling is not a lock, and anchored
  patterns (`^bash \./script`) are the minimum.
- Never edit a script that is executing (bash reads it by byte offset). Replace it by rename
  (write `.new`, then `os.replace`).
- A server that is unreachable, or a read that comes back empty, **stops** a job. It must never be
  booked as a result, and never trigger a delete.
- Get notified when background work finishes, instead of polling in the foreground.

## Local LLM benchmarking specifics

For the `ollamaClaudeCode_v*` projects, `ollamaClaudeCode_v4_tielCoder/BENCHMARK_HARNESS.md` holds the
rules, `CANDIDATE_REGISTER.md` every model decided, and `README.md` the current verdict. The box
(`192.168.100.67`, Ollama 0.33.3, ~35.5 GB usable VRAM) runs one model at a time, and the model must
be 100% GPU-resident.
