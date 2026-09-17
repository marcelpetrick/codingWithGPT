# Terminal-Bench round — prepared 2026-09-17, ready for "go"

Tomorrow: **`./GO_terminalbench.sh`**. Everything below is already built, validated and committed.
This document is the reasoning and the assumptions, so the "go" is informed, not blind.

## What this is, and the one honest caveat

Terminal-Bench measures what the `ledger` fixture cannot: **operating a shell end to end** —
configure, compile, read the compiler error, fix, re-run, debug a crash. That is the actual inner
loop of agentic coding, and it is far more discriminating than editing one Python file. It is also
the axis your work is in — the tasks are **C / CMake / Make**, matching the embedded domain and
your own `tiel_test` task.

**The caveat, stated plainly:** this is a **Terminal-Bench-*style* suite of our own tasks**, run
through this project's sandbox, **not the official Terminal-Bench harness**. I chose that on
purpose — see "Why not the official harness". So the report will say "Terminal-Bench-style
(local)", and it will **not** quote or compare against published Terminal-Bench leaderboard
numbers. It measures our models against each other on real terminal work, which is the question
that matters for choosing what runs on this box.

## The tasks (`terminalbench/tasks/`)

Each is a real build/debug task with a **deterministic** verifier. All four are validated: the
broken seed fails the verifier and the reference solution passes it, inside the isolated container
(`tb-validate.sh`, run automatically by `GO`).

| task | what the agent gets | what it must do | why it discriminates |
|---|---|---|---|
| `cmake-options` | an empty dir + your `tiel_test` spec | write a C11 CMake project with 3 `option()`-gated features that change runtime output | from-scratch build authoring; `option()` + `target_compile_definitions()`; must configure+build 3 ways |
| `fix-segfault` | a C program that segfaults | find the off-by-one that returns NULL, fix it, print the right price | read a crash, reason about a pointer, not just edit text |
| `broken-build` | a 2-file project + Makefile that won't compile | fix **two** faults (a Makefile typo + a missing `#include`) and build clean | compiler-error literacy; more than one root cause |
| `failing-unit-test` | a Roman-numeral converter with a logic bug + a test suite | fix the source so the hidden-behaviour tests pass, **without editing the tests** | the "fix the spec, not the test" axis, on C |

Deliberately C/systems, not Python: it is the harder, more relevant loop, and it exercises the
toolchain (`gcc`, `cmake`, `make`, `gdb`) the `v4-tb-sandbox` image adds.

## How it runs (`tb-run.sh`), and why this shape

Same isolation and one-model-at-a-time discipline as the rest of v4:

- **Model-outer, task-inner.** The box holds one model, so each model loads once (`keep_alive 2h`),
  runs all tasks, unloads. Never interleaved.
- **Agent phase, per task:** `v4-tb-sandbox` container on a Docker `--internal` network whose only
  egress is the `socat` relay to `.67:11434`. No host mounts — the task seeds in as a base64 tar,
  the finished tree comes back on stdout. Non-root, read-only rootfs, dropped caps, memory/pids
  capped. The model drives real `claude -p` with the full toolchain.
- **Verify phase, per task:** a **separate** `--network none` container with no model. It extracts
  the agent's tree and runs the task's `verify.sh`. Kept apart so the agent can never read or game
  the verifier, and so the compile-and-run scoring is deterministic and offline.
- **Thinking OFF by default** (`<|think_off|>`): v4 showed 2.3× faster with equal-or-better
  correctness. A thinking-ON arm runs for the two Tiel builds only, to keep that comparison alive.

Scored per task: **SOLVED / FAIL** from the verifier exit code, plus turns, tool calls, wall
clock, output and thinking tokens from the transcript (`cc-analyse.py`). n=2 per model so a
single flaky run is visible.

## Assumptions I made (so "go" needs no decisions)

1. **Field = the six still in play** (both Tiel builds, north-mini, qwen3.6 control, ornith,
   gemma4). cascade-2 and qwen3.8 stay cut. Override by passing models to `GO_terminalbench.sh`.
2. **CyberTiel runs in the same sandbox as everyone else** — the isolation is already mandatory
   for it and harness-parity was proven in v4 (host 83 s vs sandbox 84 s), so no separate path.
3. **n=2, thinking off**, with a thinking-on arm for the Tiel pair only. Enough signal without a
   multi-day run.
4. **4 GB container memory** (up from 2 GB) because a CMake build + gcc needs more than a Python
   edit. Still a hard cap.
5. **30-minute per-task timeout.** A terminal task that isn't done in 30 min is a FAIL, which is
   the honest verdict.
6. **The report auto-regenerates** at the end; the Terminal-Bench section appears once the TSV has
   rows (the generator already tolerates missing stages).

## Runtime estimate

Per task ≈ 3–10 min (a build loop is a handful of turns; prefix caching makes re-reads cheap).
Four tasks × 6 models × 2 runs + a 2-model thinking-on arm ≈ **~5–7 hours**, unattended, one model
resident at a time. It yields to a colleague (`idle.sh` waits, never evicts), so realistically an
overnight run. Container image is already built; first-run pulls are done.

## Why not the official Terminal-Bench harness

Three reasons, each a v4 lesson:

1. **It would not be validated by morning.** The official harness needs an agent adapter wired to
   Ollama, large task-image pulls, and version pinning I cannot smoke-test tonight against a busy
   shared box. v4's rule is "a measurement that cannot fail loudly is not a measurement" — I will
   not hand you a "go" that might silently run against nothing (which is exactly how the sandbox
   and the localhost-needle bugs happened).
2. **Reuse beats rebuild.** The sandbox topology, the egress allowlist, the transcript accounting
   and the scoring-from-state are already built and proven this round. The local suite is a
   200-line runner on top of them, fully under our control and already validated.
3. **The question is comparative, on this box.** We need "which local model best drives a terminal
   loop here", not a leaderboard number. Our-tasks-same-harness answers that cleanly. If an
   official leaderboard number is later wanted, it is a separate, larger effort — noted, not done.

## What "go" does, in order

1. preflight: server reachable, image present (builds it if not)
2. `tb-validate.sh`: re-confirm every seed fails and every solution passes — aborts if a fixture
   broke
3. `tb-run.sh --runs 2 --thinking off` across the field
4. thinking-on arm for the two Tiel builds
5. regenerate `report.html` + `report.pdf`
6. print `GO-TERMINALBENCH-DONE`

## Extending it later

Add a task: drop a directory in `terminalbench/tasks/` with `task.md`, `seed/`, `solution/`,
`verify.sh` (must `cd "$(dirname "$0")/work"`, exit 0 = solved), then run `tb-validate.sh`. The
runner picks it up automatically. Good next tasks for the embedded angle: a `gdb`-driven
root-cause task, a cross-compile/flags task, a race-condition fix under `valgrind`/`helgrind`, a
linker-error task.
