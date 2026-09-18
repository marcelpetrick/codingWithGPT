# The official Terminal-Bench round — plan, 2026-09-18

**This supersedes the "Terminal-Bench-*style*" caveat in `../../TERMINAL_BENCH_PLAN.md`.**
That document chose a local look-alike suite because the official harness could not be
validated in the time available. It can be now, and it has been. This round runs the
**upstream harness on the upstream dataset**, so the numbers are comparable to the public
leaderboard instead of only to each other.

## Why the answer changed

Yesterday's three reasons not to use the official harness were all about risk, and each was
re-tested today rather than re-asserted:

| yesterday's blocker | today's measurement |
|---|---|
| `.67` unreachable (USB-ethernet adapter gone) | **up** — `192.168.100.54/24`, Ollama 0.33.3, Tiel resident |
| disk too tight (11 GB free on `/`) | Docker root is `/home/docker` → **112 GB free**. The 11 GB figure was the wrong filesystem |
| "an agent adapter, image pulls and version pinning I cannot smoke-test tonight" | installed it, pulled the dataset, **ran the oracle agent end to end: 100 %** |

The honest summary: **the objection was time, not feasibility, and the time now exists.**

## What was actually verified (2026-09-18, on this laptop)

1. `terminal-bench==0.2.18` installs clean into a 3.12 venv.
2. `tb datasets download -d terminal-bench-core==0.1.1` → **80 real tasks** in
   `~/.cache/terminal-bench/`.
3. `tb run -t hello-world -a oracle` → **Accuracy 100 %**. The oracle executes each task's
   reference `solution.sh`, so this proves build → run → test → score works without spending
   a single model token.
4. A default-bridge container reaches `192.168.100.67:11434` directly
   (`{"version":"0.33.3"}`). **No socat relay is needed** for this round — the task containers
   are upstream's, and they have normal egress by design.

### Three defects found and fixed on the way

- **`docker compose` was not installed at all** (`docker: unknown command: docker compose`;
  neither was `buildx`). The harness cannot build a single task without it. Now installed
  and pacman-managed (`docker-compose 5.5.1`, `docker-buildx 0.36.1`).
- **The stock `claude-code` agent never sets `ANTHROPIC_BASE_URL`.** Its `_env` passes only
  `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`, so every task would have been sent to
  `api.anthropic.com` — benchmarking the wrong thing entirely. Fixed by
  `ollama_claude_code_agent.py` (below).

- **Our own `--run-id` voided every `q4_K_M` model** (found mid-round, 10:44, after two
  passes had already completed normally). `GO_official_tb.sh` built the run-id from the model
  tag verbatim; terminal-bench derives the `docker compose -p <project>` name from it, and
  compose rejects uppercase:

      invalid project name "fix-permissions-1-of-1-qwen3-6_35b-a3b-q4_K_M-agentic":
      must consist only of lowercase alphanumeric characters, hyphens, and underscores

  A `q4_K_M` quant suffix carries uppercase `K`/`M`, so qwen3.6 and north-mini failed **every
  task in ~0.4 s, before a container existed** — reported as `Accuracy: 0.00 %`. gemma4 carries
  the same suffix and was next in the queue; the round was stopped before it ran. Tiel
  and CyberTiel (`q5`) and ornith (no quant in the tag) were unaffected, which is precisely why
  the first two passes looked healthy and concealed the fault. Fixed by folding the run-id to
  lowercase (the `-m` tag is untouched), proven both ways with the oracle before re-running
  (uppercase run-id → 0.0, lowercased → 1.0), and the voided passes are kept as evidence under
  `runs/void-compose-uppercase/`.

> All three defects share one shape, and it is the shape §0 of the harness exists for: **they do
> not announce themselves.** The compose failure surfaced as a tidy `Accuracy: 0.00 %`, which
> reads exactly like a model that solved nothing. `summarise.py` therefore separates
> infrastructure failures from model failures and counts the former as **VOID**, never as a
> zero. The third defect is the case in point: the harness classed those trials
> `unknown_agent_error`, which is already in the INFRA set, so they were booked as VOID rather
> than as two models' worth of zeroes. The guard worked before anyone looked at it.

## The agent adapter

`ollama_claude_code_agent.py` subclasses upstream's `ClaudeCodeAgent` and supplies the v4
environment contract — nothing else is modified, so the harness stays stock:

- `ANTHROPIC_BASE_URL` → `.67`
- **all four model slots pinned to the same tag** — Claude Code picks a "small fast model" for
  subagents and background calls; an unknown tag there 404s and corrupts the turn (v3's finding)
- `CLAUDE_CODE_MAX_CONTEXT_TOKENS=230000`, under the baked window, because Claude Code cannot
  send `num_ctx` and a silent half-window truncation would go unrecorded
- telemetry and the autoupdater off, so a container with internet cannot spend turns on itself
- `<|think_off|>` appended for the Sharp-template models (v4: 2.3× faster, no correctness loss)

## The run — "Tiel deep, n=2"

**Field (6):** Tiel, CyberTiel, qwen3.6 *(control)*, north-mini, ornith, gemma4.
cascade-2 and qwen3.8 stay cut (`plan.md` §4c).

| phase | who | tasks | n | ≈ |
|---|---|---|---|---|
| 1 | all 6 | the frozen 10 | 1 | ~2.0 h |
| 2 | Tiel + CyberTiel + control | the same 10 | 2 | ~1.5 h |

Phase 2 exists because v4 §8 showed single samples at the shipped temperature flip. The three
models the recommendation actually rests on get a stability read; the comparators get one
sample for context, which is enough to place them.

**Subset — frozen in `subset.txt`, 3 easy / 5 medium / 2 hard**, weighted toward
build/debug/git/systems work (the embedded use case) rather than sampled at random:

`modernize-fortran-build`, `csv-to-parquet`, `fix-permissions`, `fix-git`, `polyglot-c-py`,
`fibonacci-server`, `nginx-request-logging`, `openssl-selfsigned-cert`, `git-multibranch`, `oom`

**Every model runs this identical set.** Change the subset and the comparison is void
(harness §5). It is frozen in a committed file precisely so it cannot drift mid-round.

Why 10 and not 80: 80 tasks × 6 models does not fit four hours — it is roughly a two-day
chain. A 10-task subset run at n=2 on the subject models buys more than an 80-task subset run
once, because the failure we most need to avoid is mistaking variance for a ranking.

## One model at a time, and a shared box

`.67` holds one ~34 GB model. The runner is **model-outer, task-inner** (`--n-concurrent 1`),
and explicitly unloads each model (`keep_alive 0`) before the next loads. It **yields to a
colleague and never evicts** — the standing rule for this box.

## What is recorded

`summarise.py` → `results/terminal-bench-official.tsv`, one row per trial:

`run_id, model, task, trial, resolved, failure_mode, in_tok, out_tok, agent_sec`

Reported per model: resolved rate **with infra failures held out of the denominator**, the
per-task grid (so a model that solves *different* tasks is visible, not just a count), and
median agent seconds.

## How to run it

```shell
cd terminalbench/official
./setup.sh              # venv + harness + dataset + ORACLE self-check (aborts if plumbing broke)
./GO_official_tb.sh     # the planned 4-hour window
```

`setup.sh` refuses to hand over a working "go" unless the oracle scores 100 % on `hello-world`
first — the cheapest possible proof that a 0 % later means the model, not the harness.

## Why not SWE-bench Lite this window

It is the better *correctness* benchmark and it stays on the roadmap
(`../../SWE_BENCH_LIVE_PLAN.md`), but it does not fit four hours:

- **300 instances**, each with its own multi-GB Docker image to pull or build.
- The official `swebench` package is an **evaluator, not an agent** — it applies a `test_patch`
  and runs tests. Driving a model to produce the patch is a scaffold we would still have to
  write and debug; v4's lesson is that the sandbox alone took three tries to deliver a fixture.
- Terminal-Bench needed **one** adapter subclass and was provable in an hour, because upstream
  ships a Claude Code agent. SWE-bench ships no equivalent.

A meaningful SWE-bench round is a **pinned ~25-instance subset over a day or two**, not an
afternoon, and it should follow this one rather than compete with it.

## Relationship to the local C suite

`../tasks/` (our 4 hand-written CMake/gcc/gdb tasks) is **not retired** — it stays as the
embedded-domain supplement, and it tests things terminal-bench-core does not (CMake `option()`
authoring, a `-Werror` two-fault build). It is now clearly labelled as ours. The official round
is the headline number; the local suite is the domain check.
