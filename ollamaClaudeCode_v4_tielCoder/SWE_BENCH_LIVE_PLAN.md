# Plan — running SWE-bench-Live locally, and orchestrating it for every model

Written 2026-09-17. **Nothing here has run yet** — this is the design for a v5 stage that
replaces the `ledger` proxy with real repository issues.

## Why

v4's ranking axis #2 is "does the model fix the *specification* or just the visible tests?" The
`ledger` fixture answers that with 18 held-out tests on a **synthetic** three-module bug. It is a
good proxy and it separated the field — but it is one hand-written task. **SWE-bench-Live is the
ground truth**: real GitHub issues, real repositories, hidden regression tests written by the
projects themselves. CyberTiel's headline "13.7/25" is a SWE-bench-Live number, so this is also
the only way to check a vendor claim on our own hardware (harness §8: measure, never quote).

The pieces already exist. `cc-session-sandboxed.sh` is 80% of a SWE-bench runner: per-task Docker
container, no host mounts, egress allowlisted to `.67`, patch scored from the repository rather
than the transcript. SWE-bench-Live is that pattern, scaled to real tasks with an official
evaluator instead of a `pytest` we wrote.

## What SWE-bench-Live is, exactly

Each task = a repo at a specific commit + an issue text + a **gold** patch + a **test patch**.
The agent sees the repo and the issue, not the tests. It produces a patch. Scoring applies the
task's `test_patch` and runs two test sets in the task's own Docker image:

- **FAIL_TO_PASS** — tests the fix must make pass (were failing at the base commit)
- **PASS_TO_PASS** — tests that must stay passing (the regression guard)

A task is **resolved** only if every FAIL_TO_PASS passes and no PASS_TO_PASS regresses. This is
the same "spec vs test" distinction as the `ledger` hidden tests, but the model cannot even see
the test file, so it cannot chase it.

> **Pin the dataset and the evaluator version in the provenance block.** SWE-bench-Live is a
> *rolling* set — it grows with new issues to resist training leakage. "SWE-bench-Live" without a
> snapshot date is not a result, exactly like an Ollama version without a number (harness §2).

## The constraint that shapes everything: one model at a time

`.67` holds one ~30 GB model. So the orchestration is **model-outer, task-inner**: load a model
once, run all N tasks against it sequentially, unload, load the next. Never interleave models —
a reload between every task would dominate the wall clock and, on a shared box, thrash a
colleague. This is the same rule as every other stage, and it makes the run a long unattended
chain (see the runtime budget) rather than anything interactive.

## Architecture

```
 for each MODEL (loaded once, resident, keep_alive 2h):
   for each TASK in the pinned subset:
     ┌─ per-task Docker container ───────────────────────────────┐
     │  the task's own SWE-bench image (its repo @ base commit)   │
     │  + git, python, the agent (Claude Code), NO test_patch     │
     │  network: --internal, egress ONLY to the .67 relay         │
     │  the model drives via ANTHROPIC_BASE_URL -> relay -> .67    │
     └───────────────────────────────────────────────────────────┘
     -> collect the container's `git diff` as the prediction
   score all predictions for MODEL with the official evaluator
```

Two containers, deliberately separated:

1. **the agent run** — the model, in the task repo, egress-allowlisted to `.67` only. It cannot
   reach PyPI or GitHub, so the fix must come from the model, not from `pip install`-ing the
   answer. This reuses the v4 sandbox topology unchanged.
2. **the evaluation** — the official SWE-bench harness applies `test_patch` and runs the tests in
   the task's pristine image. Kept separate so the agent never sees the tests and cannot corrupt
   the scorer. Scoring is offline and needs no model, so it can run after the box is freed.

The model talks to `.67` the same way the sandbox already proves works: `ANTHROPIC_BASE_URL` →
`socat` relay → `.67:11434`, all four model slots pinned to the tag,
`CLAUDE_CODE_MAX_CONTEXT_TOKENS` under the baked window, `--append-system-prompt <|think_off|>`
for the Sharp-template models (v4: 2.3× faster, no correctness loss).

## Orchestration — `swebench-run.sh` (to build)

```
swebench-run.sh --model M --subset tasks.txt --iters 20 --timeout 1800
  loads M (warm, keep_alive 2h)
  for each task_id:
      docker run --rm --network v4-egress-none <task image> ...
        install the agent, drop the model an ANTHROPIC_BASE_URL to the relay
        run:  claude -p "<issue text>" --permission-mode bypassPermissions
              --output-format stream-json  (iteration cap = --iters)
        emit: git diff > /out/<task_id>.patch, and the stamped transcript
  write predictions.jsonl  (one {instance_id, model, prediction} per task)
  ./idle.sh --mine M
```

Then, separately and model-agnostic:

```
swebench-score.sh predictions.jsonl  ->  run the official evaluator in each task
  image, produce results.json (resolved / applied / errored per task) + a run log
```

Both are thin wrappers: the agent side is `cc-session-sandboxed.sh` with the fixture swapped for
a real task image; the scoring side is the upstream SWE-bench evaluator, unmodified, so our
numbers are comparable to published ones.

## What is recorded per task

Beyond resolved/not, the same accounting `cc-analyse.py` already does, because it is what
separated models in v4:

- **resolved** (FAIL_TO_PASS all pass, PASS_TO_PASS intact) — the headline
- **patch applied?** — did the diff even apply cleanly (distinct from "resolved")
- **turns, tool calls, wall clock, input/output/thinking tokens** — turn economy (axis #4)
- **failure mode** — no patch / patch didn't apply / FAIL_TO_PASS still red / PASS_TO_PASS
  regressed (the "fixed one thing, broke another" case the held-out tests exist to catch)
- **egress self-check** — proof the container stayed isolated on every task

Report **resolved rate per model with n≥2 seeds** (SWE-bench-Live runs at non-zero temperature;
v4 §8 showed single samples flip), median time per attempt, and the per-task grid so a model that
resolves *different* tasks than another is visible, not just a count.

## Comparability rules (fixed before the run, harness §5)

Every model gets the **identical** harness: same task subset, same iteration cap, same context
budget, same tools, same timeout, same evaluator, same seeds where meaningful. Change one of
those and the comparison is void. And the control (`qwen3.6:35b-a3b`) runs the subset too, so v5
can be tied back to the base everyone derives from.

## Runtime budget

An agent SWE task is ~15–25 turns; on a 35B-A3B at ~110 tok/s with prefix caching (0.33.3), call
it **8–14 min per task**, plus one-off container image pulls (cached after first use).

| scope | tasks | per model | 5 models (toTest A/A2) | + 2 seeds |
|---|---|---|---|---|
| smoke | 1 | ~15 min | — | — |
| pinned subset | 25 | ~4–6 h | ~1–1.5 days wall | ~2–3 days |
| stretch | 50 | ~8–12 h | — | — |

This is a **days-long unattended chain**, not an afternoon. It runs on the shared box, so it must
yield to a colleague (`idle.sh` waits, never evicts) — realistically it runs overnight in
model-sized blocks. Scoring is offline and adds little.

## Phased rollout

1. **Plumbing smoke (1 task, 1 model).** Prove the task image runs, the agent reaches `.67`
   through the relay, the diff is captured, and the official evaluator scores it. This is where
   the integration bugs are — expect a day on it alone (v4's lesson: the sandbox took three tries
   to deliver a fixture at all).
2. **Pinned 25-task subset, Tiel pp0 + control.** Establish our number for CyberTiel's "13.7/25"
   claim and the base. Freeze the subset (`tasks.txt`) and the evaluator commit into provenance.
3. **The rest of the field** from `toTest.md` A/A2 — Tiel-MTP, KAT-Coder, Occamy — same subset.
4. **Report** — fold resolved-rate into `report.html` beside the `ledger` hidden-test column, so
   the proxy and the real thing sit side by side and we can say how well `ledger` predicted it.

## Risks and gotchas

- **Leakage.** A model trained on GitHub may have seen an issue's real fix. SWE-bench-Live's
  rolling design mitigates it; pin a recent snapshot and note it.
- **Flaky tests.** Some FAIL_TO_PASS are timing- or network-dependent. Run the gold patch through
  the scorer first per task to confirm it resolves cleanly — a task whose own gold patch fails is
  dropped, exactly as the `ledger` fixture was validated before use.
- **Container disk.** SWE-bench images are large. This box has no `df` over the API and no SSH;
  stage images deliberately and prune, or run the agent side on the laptop against `.67` for
  inference if `.67`'s disk is the colleague's.
- **The agent needs its dependencies offline.** The egress allowlist blocks PyPI, which is the
  point — but the task image must already contain the repo's build/test deps. SWE-bench images do;
  a hand-rolled image would not.
- **Cost of the wrong metric.** Do not let a high SWE-bench number override a reproducible tool
  gate failure (harness §1). cascade-2 would still be rejected.

## Not this project's job

Running MATH-500 / AIME / GPQA / ARC-AGI / Terminal-Bench (the "problem-solving" suite from the
research dump) is a different exercise — general reasoning, not "drive Claude Code on this box".
If that is wanted it belongs in its own repo with its own harness; this plan is scoped to the one
question v1–v4 have always asked: **which local model best drives Claude Code here.**
