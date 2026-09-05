# Changelog

All notable changes to `agent-budget-watch` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the major version is `0`, the minor version is bumped for every feature
increment and the patch version for fixes.

## [0.15.0] - 2026-09-05

### Added

- `agent_watch.simulate` and `agent-watch simulate`: twelve runnable safety
  scenarios covering the situations section 40 of the vision requires - reset
  and resume, the agent exiting first, PID reuse, suspend across a reset, a
  scrolled-away banner, a still-spent weekly limit, an unavailable provider, the
  self-healing provider, a duplicated prompt, crash recovery, the Codex opt-in
  and observe mode.
- Each scenario prints the steps it took and the decision made at each one, so a
  person can watch a specific danger play out rather than take the safety
  argument on trust.
- The test suite asserts every scenario, including that the happy path really
  does send a keystroke - a suite that passed by never typing would prove
  nothing.

## [0.14.0] - 2026-09-05

### Added

- `agent_watch.cli`: `run`, `status`, `doctor`, `init`, `config` and `logs`,
  with `--observe` / `--ask` / `--auto`, `--all`, `--once` and `--no-fzf`.
  Running bare runs.
- Running under `sudo` aborts with an explanation unless `--allow-root` is
  given: root is unnecessary, breaks access to the user's session bus, and makes
  an incorrect keystroke more expensive.
- The single-instance lock is taken only by modes that can send input, so a
  read-only watcher can always be started alongside an automatic one.
- `init` writes a commented config; a test asserts the tool can parse back what
  it just wrote.
- `SIGINT` and `SIGTERM` end the loop cleanly and release the lock.

## [0.13.0] - 2026-09-05

### Added

- `agent_watch.ui`: the running status table and the one-line observe-mode
  output. Plain text, no curses - pipe-able, greppable, and readable inside a
  test failure.
- A reset more than a day out renders as `+3d` rather than a bare clock time,
  which would be actively misleading.
- `agent_watch.doctor`: diagnostics for the platform, desktop, privileges,
  qdbus, Konsole D-Bus and session enumeration, both agent CLIs, optional tools,
  the three directories and the single-instance lock - ending with a straight
  answer to the question the user actually has: whether auto mode is safe here.
- Optional tools are reported, never failed; a missing `fzf` is information.

## [0.12.0] - 2026-09-05

### Added

- `agent_watch.picker`: discovery, a built-in numbered multi-select picker, and
  optional `fzf` support that degrades cleanly when `fzf` is absent.
- Only high-confidence agent sessions are preselected, and an ineligible session
  cannot be toggled on at all - with the reason shown next to it, so a refusal
  is visible to the person making the choice.
- A closed stdin ends the picker rather than accepting the preselection;
  silence is not consent.
- Discovery, toggling and rendering are pure functions, so the decision logic is
  tested without a terminal.

## [0.11.0] - 2026-09-05

### Added

- `agent_watch.fsm`: the supervisor - observe, decide, act, verify - and the
  per-session state machine.
- Revalidation before input: `act()` treats the decision as a proposal, re-reads
  the foreground process, identity, session reference and screen, re-runs the
  recognizer and the gate, and cancels on any drift.
- Verification is a state with a deadline rather than a sleep, so one wedged
  session cannot stall the others.
- Suspend and clock-change detection by comparing wall-clock against monotonic
  elapsed time across a tick; a divergence discards every pending schedule and
  forces full revalidation.
- A per-session attempt budget alongside the per-prompt one, so a screen that
  keeps changing cannot mint a fresh budget on every tick.
- A session marked unsafe stays unsafe; a later screen reading cannot quietly
  promote it back.
- `tests/harness.py`: a fake terminal, a fake process table and a clock whose
  wall and monotonic hands move independently, so suspend, PID reuse, process
  swap, wedged terminals and crash recovery are all covered in milliseconds.

## [0.10.0] - 2026-09-05

### Added

- `agent_watch.lock`: an advisory `flock` under `$XDG_RUNTIME_DIR`, so two
  supervisors cannot each correctly decide to press Enter once and between them
  press it twice. Observe mode does not take the lock, so a read-only watcher
  can run alongside an automatic one.
- `agent_watch.state_store`: the action lifecycle
  `PLANNED -> SENT -> VERIFIED|FAILED`, persisted atomically. The record is
  written *before* the keystroke, so a crash in between is read back as "may
  already have been typed" and refuses rather than repeating.
- Writes go through a temporary file, `fsync` and `os.replace`; a half-written
  state file would read back as "nothing has been done yet", which is worse than
  no file at all.
- A corrupt or future-versioned state file starts empty instead of refusing to
  run, and records older than 24 hours are dropped on load.

## [0.9.0] - 2026-09-05

### Added

- `agent_watch.policy`: the resume gate. Fourteen named preconditions, each
  returning a refusal *reason* rather than a bare false, so a log reader can act
  on a refusal instead of guessing at it.
- `Authorization`, grading how strongly the evidence says usage returned:
  `PROVIDER_CONFIRMED` (a fresh quota snapshot, or the provider's own "usage
  limit has reset" affordance) outranks `TIME_ONLY` (a wall-clock reset plus the
  grace period). Auto mode requires the former; ask mode will offer the latter;
  observe mode acts on neither.
- `idempotency_key()`: provider, session, process start time and screen
  fingerprint, so one logical prompt yields at most one action and a restarted
  agent in the same tab counts as a new prompt.
- Every refusal carries `retry_at` when a reset time is known, so a session
  blocked for four hours is not polled every two seconds.
- The gate is handed a `ResumeRequest` and cannot fetch anything itself, so it
  cannot depend on state the caller did not revalidate.

## [0.8.0] - 2026-09-05

### Added

- `agent_watch.quota`: provider quota state, kept separate from terminal state.
- `CodexRolloutSource`: Codex keeps its session rollout `.jsonl` open, so the
  file for a given PID can be located through `/proc/<pid>/fd`; each
  `token_count` event carries a `rate_limits` object with the five-hour window,
  the weekly window and credits. Machine-readable provider state, no TUI
  parsing.
- `ClaudeStatuslineSource`: reads the small document written by the status-line
  proxy, carrying Claude Code's `five_hour` and `seven_day` usage and resets.
- `Availability.UNKNOWN` for anything missing, stale, malformed or broken.
  Unknown never means available.
- Sources are failure-isolated by contract - `snapshot()` never raises - so a
  broken Codex source cannot stop Claude monitoring.
- `next_reset` returns the *last* exhausted window to clear, so a five-hour
  reset cannot unblock a session whose weekly limit is still spent.

## [0.7.0] - 2026-09-05

### Added

- `agent_watch.states`: the `SessionState` and `ActionState` vocabularies.
- `agent_watch.providers`: versioned, data-driven prompt recognizers for Claude
  Code and Codex CLI. Every pattern records the provider version it was verified
  against, so a future wording change is a table edit and a version bump rather
  than a hunt through code.
- `providers.timeparse`: parses the three reset shapes the CLIs actually emit -
  `resets 8:10pm (Europe/Berlin)`, `resets Mon 12:00am` and `resets in 4h51m`.
  Anything it cannot parse confidently returns `None`, which means "wait for a
  provider signal", never "resume now".
- Recognition of Claude Code's self-healing banner. Since 2.1.234 Claude resumes
  itself, and the supervisor stands down rather than racing it; the case it
  genuinely covers is Claude's own "will not resume on its own".
- Paid, credit-purchase, reset-credit-redemption and model-downgrade prompts are
  recognised specifically so they can be refused.
- Patterns match against both a line-joined and a reflowed rendering of the
  screen, so a provider sentence broken across a terminal soft wrap is still
  recognised.

## [0.6.0] - 2026-09-05

### Added

- `agent_watch.logging_setup`: a key/value event log with size-based rotation
  (10 MB, 5 backups) and owner-only permissions on both the file and its
  directory.
- `fingerprint()`, the only sanctioned way for screen content to influence a log
  line: it returns a 12-character SHA-256 prefix, never the text. `EventLogger`
  deliberately has no free-text method, so "log events, not content" is enforced
  by the API rather than by reviewer discipline.

## [0.5.0] - 2026-09-05

### Added

- `agent_watch.config`: layered configuration with the precedence the vision
  specifies - defaults, then the config file, then the environment, then CLI
  arguments.
- The `KEY=VALUE` config file is *parsed*, never sourced. Sourcing it would hand
  arbitrary code execution to anything that can write it, which is a poor trade
  for a tool whose job is typing into terminals.
- An unknown or malformed setting is an error rather than a silent fallback, so
  a misspelled `RESET_GRACE` cannot quietly become 60 seconds.
- Only `AGENT_WATCH_*` environment variables are honoured, so an unrelated
  `MODE` in the environment cannot reconfigure the supervisor.
- `Policy`, holding the money- and quality-affecting switches. All of them
  default to off, including Codex auto-resume.

## [0.4.0] - 2026-09-05

### Added

- `agent_watch.terminal`: the `TerminalAdapter` protocol, so the supervisor is
  not welded to one emulator and the state machine can be tested end to end.
- `KonsoleAdapter`, driven through Konsole's per-session D-Bus interface
  (`processId`, `foregroundProcessId`, `getAllDisplayedTextList`, `sendText`).
  This is what makes the tool work under Wayland without `xdotool`, `ydotool`,
  screen coordinates or OCR.
- `FakeAdapter`, a scriptable in-memory terminal that records everything sent,
  so idempotency and the danger scenarios can be asserted in milliseconds
  instead of waiting hours for a real quota reset.
- Scrollback is deliberately absent from the adapter interface: only a bounded
  tail of the current screen can be read.

## [0.3.0] - 2026-09-05

### Added

- `agent_watch.classify`: foreground-process classification into CODEX, CLAUDE,
  SHELL, SSH, TMUX, SCREEN, CONTAINER, EDITOR or UNKNOWN.
- A CODEX or CLAUDE verdict needs at least two independent signals before it may
  drive automation, because wrappers change: Codex ships as a Node shim whose
  `comm` is `node` and whose real binary is a child process.
- Blockers (container, SSH, tmux/screen, and multiplexer or SSH *ancestors*) are
  evaluated before agent detection, so Claude running inside tmux is reported as
  unsupported rather than as an automatable agent.
- Contradictory provider evidence fails closed instead of picking a winner.

## [0.2.0] - 2026-09-05

### Added

- `agent_watch.proc`: `/proc` inspection and `ProcessIdentity`, which pairs a
  PID with the kernel start-time counter so a recycled PID can never be
  mistaken for the process the supervisor selected (vision DANGER 1).
- `still_the_same()`, the revalidation primitive used immediately before any
  input is injected.
- `/proc/<pid>/stat` is parsed after the last `)` so a command name containing
  spaces or parentheses cannot shift the field offsets.
- Only environment variable *names* are read, never their values, so tokens in
  the environment are structurally unable to reach a log.

## [0.1.0] - 2026-09-05

### Added

- Project scaffold: `src/`-layout package `agent_watch`, PEP 621 packaging with
  the version read dynamically from `agent_watch.version`, and the
  `agent-watch` console-script entry point.
- Ruff, pytest and coverage configuration.
- A test that fails the build when `CHANGELOG.md` and `__version__` disagree.

## [0.0.1] - 2026-09-05

### Added

- `vision.md`: the product vision for `agent-budget-watch`.
- `PLAN.md`: the implementation plan, including the prompt strings extracted
  from Claude Code 2.1.261 and Codex CLI 0.153.2 and the verified Konsole D-Bus
  capabilities they rely on.
