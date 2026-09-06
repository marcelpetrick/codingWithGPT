# Changelog

All notable changes to Agent While True are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the major version is `0`, the minor version is bumped for every feature
increment and the patch version for fixes.

## [0.27.0] - 2026-09-06

### Added

- A canonical `localPipeline.sh` runs the Python baseline check, Ruff,
  formatting, ShellCheck, coverage gate, every safety simulation, distribution
  build, isolated wheel install, and both CLI smoke tests.
- Path-filtered GitHub Actions quality and release workflows test Python 3.12
  through 3.14 and publish verified `agentwhiletrue-v*` tags.
- README quality, release, Python baseline, and license badges.

### Changed

- The supplied systemd unit and installation guidance use the primary
  `agent-while-true` command while retaining `agent-watch` compatibility.

## [0.26.0] - 2026-09-06

### Added

- The dashboard can show the recent persisted state/action history. Press `e`
  to hide it and `l` to cycle through 5, 10, 20, or 50 rows.
- The README documents the history file, `logs` command, journal view, and the
  privacy boundary: terminal content is never persisted.

### Changed

- Codex sessions launched through the Node.js shim are presented as `Codex` in
  the dashboard once the child process has been classified.
- Remaining project documentation now consistently uses the Agent While True
  product name.

## [0.25.0] - 2026-09-06

### Fixed

- A thread disappearing between `/proc/<pid>/task` enumeration and reading its
  `children` file no longer crashes long-running discovery. Child inspection
  and per-session classification isolate the same expected process churn.
- Transient empty Codex rate-limit objects no longer replace the most recent
  usable event with `unrecognised-rate-limit-shape`.

## [0.24.0] - 2026-09-05

### Added

- A btop/ollamaFarm-inspired interactive dashboard with semantic colors,
  responsive `+`/`-` refresh control, pause, immediate rescan, theme cycling,
  help overlay and clean quit/cursor restoration.
- Dark, vivid and plain themes; `NO_COLOR` and `--no-color` disable ANSI.

### Changed

- Paused dashboards perform no terminal or quota polling.
- Non-interactive observe mode separates successive scans with a blank line.

## [0.23.0] - 2026-09-05

### Changed

- Python 3.12 is now the explicit minimum in package metadata, contributor
  guidance and Ruff's syntax target. CI covers Python 3.12 through 3.14.

## [0.22.0] - 2026-09-05

### Changed

- The product is now consistently named **Agent While True**, described as an
  agent budget watch and babysitter. The primary installed command is
  `agent-while-true`; `agent-watch` remains a fully compatible alias and the
  established config/state paths remain unchanged.

## [0.21.0] - 2026-09-05

### Added

- Auto mode can arm Claude Code's own `Wait here, then continue automatically`
  choice when the exact tested menu has item 1 visibly selected and fresh quota
  confirms the session window is exhausted.
- The action sends one Down sequence and Enter, revalidates the complete screen
  and process identity first, persists idempotency before sending, and verifies
  Claude's self-healing state afterwards.

### Safety

- Unknown/stale quota, a changed cursor or menu, disabled
  `ALLOW_CLAUDE_AUTO_WAIT`, and every non-exact prompt refuse the menu action.
  The adjacent paid upgrade remains forbidden.

## [0.20.0] - 2026-09-05

### Added

- `scripts/install-claude-bridge.sh` installs the local quota proxy, backs up
  Claude's settings, and safely chains any existing status-line command. It is
  idempotent and never replaces the user's status-line behavior.

## [0.19.0] - 2026-09-05

### Fixed

- Codex quota discovery now walks from Konsole's foreground Node launcher to
  its native child, which is the process that actually owns the session rollout
  descriptor. Live Codex sessions therefore report their real five-hour and
  weekly availability instead of `no-rollout-file`.

## [0.18.0] - 2026-09-05

### Added

- A complete README covering isolated installation, live quota queries, modes,
  Claude status-line integration, the safe background service, troubleshooting,
  simulations and the pre-input safety gate.
- The real Claude limit-menu screenshot documents the prompt the recognizer's
  regression fixture protects.

### Fixed

- Package metadata now identifies GPL-3.0-only, matching the enclosing
  repository license instead of incorrectly claiming MIT.

## [0.17.0] - 2026-09-05

### Added

- Explicit `--all` watchers stay alive with no initial sessions and safely add
  eligible Codex and Claude processes discovered later.
- An observe-only systemd user unit and installer. Automatic terminal input is
  never enabled merely by installing the service.
- Subprocess coverage for Claude quota capture, command chaining, malformed
  input and concurrent status-line writers.

### Fixed

- Claude status-line writes now use unique owner-only temporary files before an
  atomic replace, preventing multiple Claude sessions from racing over one
  shared temporary path.
- The status view no longer advertises unimplemented keyboard shortcuts.

## [0.16.0] - 2026-09-05

### Added

- `agent-watch quota` reports live Codex and Claude availability, source errors,
  usage percentages and reset times without sending terminal input.
- The running status table and observe output show provider quota state beside
  the independently recognised terminal prompt state.
- A regression fixture transcribed from `media/claude_out_of_quota.png` covers
  Claude Code's three-choice limit menu.

### Safety

- The menu's automatic-wait option is not mistaken for an already enabled
  self-resume, and the paid upgrade choice is an explicit automation veto.

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
