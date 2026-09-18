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

## Results — 2026-09-18, round complete

120 trials, **0 VOID**, box released at 15:29. Phase 1 ran all six models at n=1; phase 2 gave
Tiel, CyberTiel and the control a further n=2, so those three are summarised over 30 trials.

| model | resolved | trials | median agent |
|---|---|---|---|
| **qwen3.6 35b-a3b** *(control)* | **53 %** | 30 | 186 s |
| north-mini-code-1.0 | 50 % | 10 | 152 s |
| Tiel · pp0 | 37 % | 30 | 132 s |
| gemma4 26b | 30 % | 10 | 134 s |
| ornith 1.0 | 30 % | 10 | 88 s |
| CyberTiel · pp0 | 27 % | 30 | 148 s |

### The incumbent wins, and wins twice

**The control was not displaced.** `qwen3.6:35b-a3b` leads on resolved rate, and the Tiel pair
sits 16 and 26 points behind it. On this benchmark neither subject model justifies replacing it.

The second win matters more than the first: **qwen3.6 is dramatically more reproducible.**
Counting tasks that land the same way in all three samples —

| model | stable solve | stable fail | **flips** |
|---|---|---|---|
| qwen3.6 | 5 | 4 | **1** |
| Tiel | 2 | 5 | **3** |
| CyberTiel | 1 | 6 | **3** |

qwen3.6 is decided on 9 of 10 tasks; both Tiel builds are coin-flipping on three. A single
sample would have reported Tiel anywhere from 30 % to 50 %. This is v4 §8's warning landing
exactly where it was aimed, and it is why phase 2 existed.

**Tiel vs CyberTiel is a wash, not the 20-point gap phase 1 showed** (37 % vs 27 %, with three
flipping tasks each). The n=1 numbers — 40 % and 20 % — were both off in opposite directions.

### Two tasks beat the entire field

`polyglot-c-py` **0/12** and `nginx-request-logging` **0/12**. `nginx` is the near-miss: models
routinely pass 7 of its 8 tests and fail on config settings. `polyglot-c-py` is the field's most
expensive failure — it times out four different models at their full budget.

### `oom`: the failure that reads like a success

The finding of the round, and it is a *behavioural* one that the score alone hides. The test
loads with `local_files_only=True`, so the model must end up in the **default** cache path.
Three strategies appear across 12 trials (`./analyse-task.py oom`):

- **remove the cause** — delete the planted 75 MB file, download in place → CyberTiel, 2 solves
- **work around, then reconcile** — relocate to `/tmp`, then copy the files back into the
  default snapshot directory → qwen3.6, 1 solve
- **work around and stop** — relocate to `/tmp` and declare victory → 7 of the 9 failures

> **left the default cache populated: 3/3 of the solves, 2/9 of the failures.**

Relocating is not the error; leaving the default path empty is. Every one of the nine failures
ends with a confident, technically accurate report of success — Tiel's even lists a caveat that
`/tmp` may be wiped on reboot. Each satisfies the user's literal request while missing the
environment's actual contract. **That is the failure mode least likely to survive a human review
of the agent's own output**, and the reason the transcript analysis is committed alongside the
scores rather than left as a one-off grep.

### Why the failures failed — the post-round investigation

All 123 transcripts were read before any conclusion was drawn about model weakness. The
failures are **not one thing**, and roughly a third of them are ours.

**`nginx-request-logging` (0/12) is a defective task; no model could have passed it.** Its
instruction says *"Place the configuration in `/etc/nginx/conf.d/benchmark-site.conf`"*. Its
tests read `/etc/nginx/nginx.conf` and require a `log_format` named literally `detailed` —
a file and a name the instruction never states. All 12 trials fail the identical assertion, and
the config dumped in every failure message begins `user www-data;`, i.e. the stock, untouched
`nginx.conf`. qwen3.6 meanwhile wrote a complete and correct format into the file it was told to
use: `log_format benchmark '$time_local | $request_method | $status | …'`. Every model passed 7
of the 8 sub-tests. It is now **run but not scored** (`DEFECTIVE` in `summarise.py`,
`DEFECT` in the report grid).

**`fibonacci-server` (3/12) measures scaffold persistence, not Fibonacci.** qwen3.6 passed 3/3;
every other model failed identically on *"Server is not running on port 3000"*. The difference
is one character:

| launch | survives the agent session? |
|---|---|
| `node server.js &` — shell background (qwen3.6) | yes → passes |
| Claude Code's `run_in_background` tool (everyone else) | no, the harness reaps it → fails |

Tiel's own closing message names the mechanism: *"The server runs in the background (task
`b36gk066o`). Stop it with `task stop b36gk066o`."* That task dies with the session; the tests
then run in a separate shell and find nothing. The task is **kept and scored** — a server that
dies when your agent exits is not running — but it is recorded as measuring agent-scaffold
awareness, which is worth knowing and is not what the task name suggests.

**`polyglot-c-py` (0/12) is genuine difficulty.** One file that is valid C *and* valid Python.
`gcc` works, the toolchain is present, and one run alone issued **179 compile attempts** with
real linker errors and explicit reasoning (*"gcc ignores the extension, I need a real polyglot
structure"*). The models iterated hard against the full 360 s budget and could not do it. 8 of
12 trials are timeouts.

**No systematic harness fault exists.** Across all 123 transcripts: 0 API errors, 0 context-limit
hits, 0 connection failures, 0 model-not-found 404s, thinking confirmed off as configured. (Apparent
"404" matches were hex inside UUIDs; "rate limit" was the nginx task's own requirement.)

**Effect on the standings — the ordering does not change**, because the defects cost every model
about the same:

| model | n | −nginx (now reported) | −nginx, −fibonacci |
|---|---|---|---|
| qwen3.6 | 3 | **59 %** | **54 %** |
| north-mini | 3 | 41 % | 46 % |
| Tiel | 3 | 41 % | 46 % |
| gemma4 | 1 | 33 % | 38 % |
| ornith | 1 | 33 % | 38 % |
| CyberTiel | 3 | 30 % | 33 % |

Absolute scores were depressed about 6 points by the broken task, and the ordering is unchanged.

**A correction, recorded rather than quietly fixed.** On the n=1 data this table showed north-mini
at 56 %/62 % and concluded it *overtakes qwen3.6 once the scaffold task is removed*. Its owed n=2
pass then landed and put it at **41 %**, level with Tiel. The overtake was an artefact of a single
lucky sample — the same trap this round documents twice elsewhere, walked into a third time while
writing up the round. qwen3.6 leads on every cut of the data. north-mini keeps its slot in the
standing field on **speed**, which is measured and stable, not on capability.

**One confound this round cannot resolve.** Thinking was off, on v4's 2.3×-for-free finding —
which was measured on the *ledger* fixture, never on hard puzzle tasks. A thinking-on arm over
`polyglot-c-py` and `git-multibranch` is the honest next test, and it is not run yet.

### The model comparison is INVALID — we disabled thinking on the subjects only

Found 2026-09-18 while checking this round against published results. **It invalidates the
model-vs-model conclusion of the whole round**, and it was our error, not the models'.

`<|think_off|>` is a **Sharp-template token**. The adapter appended it to every model's system
prompt. Only Tiel and CyberTiel parse it; for everyone else it sat there as inert text. Reasoning
blocks actually emitted:

| model | trials | trials that reasoned | blocks |
|---|---|---|---|
| tiel-coder | 30 | **0** | **0** |
| cyber-tiel | 30 | **0** | **0** |
| qwen3.6 | 30 | 27 | 287 |
| north-mini | 30 | 30 | 373 |
| ornith | 10 | 10 | 95 |
| gemma4 | 10 | 9 | 83 |

**The two subject models ran with reasoning disabled and every comparator ran with it enabled.**
The adapter's own docstring said the marker was "for the Sharp-template models" — the intent was
Tiel-only; the code applied it to all, and the effect was Tiel-only suppression. Nothing flagged
it because a model that ignores the marker fails silently, which is the same shape as every other
defect this round turned up.

**What tipped us off was an outside result, not our own data.** Published Terminal-Bench 2.1
numbers put Ornith-1.5 — Tiel's base — at 67.8 against Qwen3.6-35B's 52.5. This round found the
reverse ordering. A disagreement that large against the public ranking is the signature of a
configuration error, and it was.

**What survives and what does not:**

- **Void:** every model-vs-model claim. Tiel 41 % vs qwen3.6 59 % compares a silenced model to a
  thinking one. The "contenders did not displace the incumbent" verdict is **unproven**, not
  disproven — it may still be true, it is simply not evidence yet.
- **Survives:** the harness findings, which do not depend on the comparison — the `nginx`
  task defect, the `fibonacci-server` scaffold-persistence effect, the `oom` workaround-vs-
  root-cause behaviour, the n=1 jitter measurements (those compare a model to *itself*), and
  every per-task transcript reading.

**The fix, applied:** the adapter now refuses `thinking=off` unless **every** model in the run
honours the marker, and raises with the reason rather than running. The default is `on`, the only
setting this harness can guarantee is symmetric, and `GO_official_tb.sh` passes
`TB_THINKING=${TB_THINKING:-on}`.

**The re-run is owed and is not done.** The field must be re-measured at thinking parity before
any model is ranked against another. Until then the standing field's slot rationales that rest on
Terminal-Bench capability are provisional — slot 1 (qwen3.6 "the default") most of all.

This also gives v4's own "thinking off is 2.3× faster for no loss" finding a boundary: it was
measured on the ledger fixture, on Tiel, and it does not license disabling reasoning on a mixed
field.

### Before a subset is ever frozen again

`validate-subset.py` was written out of this and is now a gate: it parses each task's tests with
`ast` and reports the literals they **compare against** — never their failure messages — that the
instruction does not mention. Run on the round-1 subset it flags `/etc/nginx/nginx.conf` for
nginx, which is exactly the defect, three hours of compute after the fact.

A hit is a question, not a verdict. The rule is that every hit gets answered, and the oracle
scores 100 %, **before** the set is frozen — because afterwards the comparison is already spent.

### What is not settled

**~~north-mini is tied for the lead on a single sample.~~ Settled 2026-09-18.** The n=2 pass
ran: north-mini is **41 %** (11/27 excluding the defective task), tied with Tiel, not with the
leader — and with **4 flipping tasks** it is the least stable model in the round. Its 50 % was a
lucky single sample. It still owns `git-multibranch` (2/3; nothing else solves it at all) and it
is still the fastest generator on the box, which is what its slot in the standing field rests on.

What is now open instead: **thinking was off for every trial**, on a v4 finding measured on the
ledger fixture and never on hard puzzle tasks. A thinking-on arm over `polyglot-c-py` and
`git-multibranch` is the next honest test, and gemma4 and ornith still stand at n=1.

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
