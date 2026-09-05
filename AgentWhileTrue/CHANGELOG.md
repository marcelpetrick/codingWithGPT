# Changelog

All notable changes to `agent-budget-watch` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the major version is `0`, the minor version is bumped for every feature
increment and the patch version for fixes.

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
