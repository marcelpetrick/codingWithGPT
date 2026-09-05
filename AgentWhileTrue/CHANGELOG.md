# Changelog

All notable changes to `agent-budget-watch` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the major version is `0`, the minor version is bumped for every feature
increment and the patch version for fixes.

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
