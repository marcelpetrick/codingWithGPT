# Implementation Plan — Agent While True

Derived from [vision.md](vision.md). This plan records the decisions taken before
implementation, the evidence they rest on, and the commit sequence.

## Current execution plan

This checklist is updated in every commit so the next useful action is visible
without reconstructing history.

- [x] v0.15.0: runnable safety scenarios and end-to-end supervisor baseline.
- [x] v0.16.0: live provider availability, errors, usage and reset query.
- [x] v0.17.0: concurrent-safe Claude capture and observe-only user service.
- [x] v0.18.0: README, package build and project-local contributor guidance.
- [x] v0.19.0: find live Codex quota through its Node launcher.
- [x] v0.20.0: backup-preserving Claude bridge installer.
- [x] v0.21.0: safely arm Claude's exact provider-owned automatic-wait menu.
- [x] v0.22.0: rename the product to Agent While True while preserving compatibility.
- [x] v0.24.0: add the btop-inspired color TUI, help, pause, rescan, themes and
  refresh keys; separate non-interactive observe scans with a blank line.
- [x] v0.25.0: survive disappearing `/proc` threads and transient incomplete
  Codex quota events without terminating or erasing valid state.
- [x] v0.26.0: show provider-aware session names instead of Codex's Node shim
  title and expose recent persisted action history in the dashboard.
- [x] v0.23.0: make Python 3.12 the documented and linted baseline; CI will test
  3.12 through 3.14 in its pipeline milestone.
- [ ] Add `localPipeline.sh`, path-filtered GitHub quality/release workflows and
  README badges.
- [ ] Run the full local pipeline, installed-wheel smoke test, live Konsole
  validation and safety simulations.
- [ ] Push `master`, create the verified release tag, and confirm GitHub Actions.

## 0. Evidence gathered before planning

All of the following was verified on the target machine (Manjaro, KDE Plasma,
Wayland, Konsole), not assumed:

| Fact | Evidence |
| --- | --- |
| Konsole exposes per-session D-Bus objects | `qdbus6` lists `org.kde.konsole-<pid>` services, each with `/Sessions/N` |
| Foreground process is readable | `org.kde.konsole.Session.foregroundProcessId()` |
| Bounded screen text is readable | `Session.getDisplayedText(start, end)`, `Session.getAllDisplayedTextList(bool)` |
| Input can be injected | `Session.sendText(QString)` |
| Works under Wayland | The above ran successfully with `XDG_SESSION_TYPE=wayland` |
| Codex runs behind a Node shim | foreground `cmdline` is `node .../bin/codex …`, with a native `codex` child |
| Claude Code version tested | 2.1.261 |
| Codex CLI version tested | 0.153.2 |

### Prompt strings extracted from the shipped binaries

Rather than guessing wording, the recognizer patterns were extracted from the
installed executables (`strings`) and cross-checked against a real screenshot of
a 5-hour limit event.

**Claude Code 2.1.261**

- Blocking: `You've hit your session limit`, `You've hit your weekly limit`,
  `You've hit your Opus limit`, `You've hit your Sonnet limit`,
  `You've hit your fast limit`, `Usage limit reached`
- Reset time is rendered inline: `· resets 8:10pm (Europe/Berlin)`
- Ready to resume: `Usage limit has reset · press enter to continue`,
  `Your usage limit has reset`, `Usage limit available again`
- Self-healing: `Continuing automatically when your limit resets`,
  `Continue automatically at usage limit` — Claude Code resumes itself since
  2.1.234, so agent-watch **must stand down** when this is on screen.
- The gap agent-watch actually fills: `the usage limit now resets more than 24
  hours out, so this task will not resume on its own`, and
  `this session moved to the background, so the task will not resume on its own`.
- Never automated: `You've hit your monthly spend limit`, `/upgrade`,
  `/usage-credits`, `Switch to another model`.

**Codex CLI 0.153.2**

- Blocking: `You've hit your usage limit.`, `You've hit your usage limit for `,
  `Usage limit reached`, `Try again at `, `You're out of credits.`,
  `You've reached your workspace credit limit`
- Warning: `Approaching rate limits`
- Never automated: `purchase more credits`, `Upgrade to Plus`, `Upgrade to Pro`,
  `Redeem usage limit reset`, `Request a limit increase`, and the model-downgrade
  prompt (`rate-limit-switch-prompt` / `Keep current model`).
- Codex has **no** "press enter to continue" affordance; it returns to the
  composer. Resuming therefore means typing text, which is strictly more
  dangerous than pressing Enter — so Codex auto-resume is opt-in (§4).

**Provider quota sources confirmed to exist**

- Claude Code status-line JSON carries `five_hour`, `seven_day`,
  `seven_day_opus`, `utilization`, `resets_at` (§23 of the vision).
- Codex app-server exposes rate-limit fields `used_percent`, `window_minutes`,
  `reset_after_seconds`, `rate_limit_reached_type`, `credits_depleted`,
  and secondary windows (§22 of the vision).

## 1. Language and shape

- **Python 3.11+, standard library only at runtime.** The vision allows Bash for
  the MVP but flags that Bash gets hard fast; the state machine, identity
  revalidation and idempotency logic here are exactly that case. Python is the
  user's stated preference where it fits.
- **Shell only where shell is the right tool**: the quality gate, the systemd
  user unit installer, and the Claude status-line proxy (which must be a fast,
  dependency-free hook). All shell is `sh`/`bash`-portable and `shellcheck`-clean.
- The supervised shell stays Zsh; nothing here requires the tool's own shell to
  match.
- No third-party runtime dependencies keeps `pip install --user` viable and
  removes a whole class of breakage on a rolling-release distro.

## 2. Module layout

```
agent_watch/
  version.py        single source of truth for the semver string
  config.py         defaults < config file < environment < CLI
  logging_setup.py  key=value event log, size-based rotation, content redaction
  proc.py           /proc inspection, composite process identity
  classify.py       process class (CODEX/CLAUDE/SHELL/SSH/TMUX/…)
  terminal/
    base.py         TerminalAdapter protocol + TerminalSession
    konsole.py      qdbus/qdbus6 adapter
    fake.py         scriptable in-memory adapter (tests + simulation)
  providers/
    base.py         ProviderAdapter, PromptMatch, Recognition
    patterns.py     versioned prompt definitions (the table above, as data)
    claude.py       Claude Code recognizer + resume action
    codex.py        Codex recognizer + resume action
  quota.py          QuotaSource protocol, statusline + app-server sources
  states.py         SessionState / ActionState enums
  policy.py         the §17 resume gate, expressed as named preconditions
  fsm.py            per-session state machine, grace, retry, revalidation
  lock.py           flock single-instance guard
  state_store.py    atomic JSON state under $XDG_STATE_HOME
  picker.py         ANSI multi-select picker (fzf optional)
  ui.py             live status table
  doctor.py         environment diagnostics
  simulate.py       scenario harness for the §40 danger list
  cli.py            argparse: run/status/doctor/init/logs/config/version/simulate
```

## 3. Safety model

The resume gate is the whole point of the project, so it is a single, testable
function returning a *named reason* for every refusal — never a bare boolean:

1. session was explicitly selected by the user;
2. same Konsole service + session object as at selection time;
3. same composite process identity (PID **and** `/proc` start time **and** TTY);
4. foreground process classifies as Codex or Claude;
5. the current screen matches a *known* blocking prompt of that provider;
6. the prompt's action is permitted by policy (mode, paid/downgrade opt-ins);
7. quota state says usage is available — never inferred from provider silence;
8. no other limit window is still exhausted;
9. this prompt fingerprint has not already been actioned;
10. session is not marked UNSAFE.

Immediately before `sendText`, conditions 2–5 are re-read from live state and the
action is cancelled on any drift (vision DANGER 2, 3, 18).

Idempotency key: `provider | konsole service | session | process start time |
prompt fingerprint`. Persisted with an action lifecycle
`PLANNED → SENT → VERIFIED|FAILED` so a crash between send and persist cannot
double-fire (DANGER 13, 17).

Clocks: wall-clock for provider reset instants, `time.monotonic()` for retry and
grace intervals; a large divergence between the two across a tick is treated as
suspend/resume and forces full revalidation (DANGER 9, 10).

Logging: events only. Screen text is never written to the log; only its SHA-256
fingerprint and the matched pattern id (DANGER 15).

Fail-closed defaults: unknown prompt, unknown provider state, missing quota
source, nested terminal, SSH, container ⇒ log and do nothing.

## 4. Policy defaults

| Action | Default |
| --- | --- |
| Claude: press Enter on `Usage limit has reset · press enter to continue` | allowed in `auto` |
| Claude: anything while `Continuing automatically…` is shown | refused (Claude self-resumes) |
| Codex: type continuation text into the composer | `ask` only; `auto` requires `--allow-codex-auto-resume` |
| Model downgrade | never |
| Paid credits / purchase / upgrade | never |
| Redeem usage-limit reset | never |

## 5. Versioning

Semver in `agent_watch/version.py`, consumed dynamically by `pyproject.toml`.
Every commit bumps the version and adds a `CHANGELOG.md` entry; a test asserts
the newest changelog heading equals `__version__`, so the two cannot drift.
Release tags are `agentwhiletrue-vX.Y.Z` (this project lives inside a monorepo).

## 6. Quality gate

`scripts/quality.sh` — the same entry point locally and in CI:

- `ruff check` and `ruff format --check`
- `shellcheck` over every tracked `*.sh`
- `pytest` with coverage
- version/changelog consistency

## 7. CI/CD

Workflows live at the repository root (GitHub Actions requires that) and are
path-filtered to `AgentWhileTrue/**`:

- `agentwhiletrue-quality.yml` — push/PR, Python 3.11–3.13 matrix, runs the gate.
- `agentwhiletrue-release.yml` — on `agentwhiletrue-v*` tags: re-runs the gate,
  verifies the tag matches `__version__`, builds sdist+wheel, publishes a GitHub
  release with the matching changelog section.

## 8. Commit sequence

| # | Version | Commit |
| --- | --- | --- |
| 1 | 0.0.1 | vision + this plan + changelog |
| 2 | 0.1.0 | project scaffold, packaging, tooling config |
| 3 | 0.2.0 | `proc`: composite process identity |
| 4 | 0.3.0 | `classify`: process classification |
| 5 | 0.4.0 | `terminal`: adapter protocol, Konsole, fake |
| 6 | 0.5.0 | `config`: layered configuration |
| 7 | 0.6.0 | `logging_setup`: redacting event log |
| 8 | 0.7.0 | `providers`: versioned recognizers |
| 9 | 0.8.0 | `quota`: quota sources |
| 10 | 0.9.0 | `policy`: the resume gate |
| 11 | 0.10.0 | `state_store` + `lock`: persistence and single instance |
| 12 | 0.11.0 | `fsm`: the supervisor state machine |
| 13 | 0.12.0 | `picker`: interactive selection |
| 14 | 0.13.0 | `ui` + `doctor` |
| 15 | 0.14.0 | `cli`: wiring |
| 16 | 0.15.0 | `simulate`: danger-case scenarios |
| 17 | 0.16.0 | shell scripts: quality gate, statusline proxy, systemd unit |
| 18 | 0.17.0 | GitHub Actions workflows |
| 19 | 0.18.0 | README |

## 9. Out of scope, per vision §3

tmux/screen panes, SSH, containers, OCR, screenshots, generic desktop input,
buying credits, non-Konsole terminals. Each is *detected* and refused, not
silently mishandled.
