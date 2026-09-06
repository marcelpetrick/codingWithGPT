# Agent While True

[![Quality](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/agentwhiletrue-quality.yml/badge.svg?branch=master)](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/agentwhiletrue-quality.yml)
[![Release](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/agentwhiletrue-release.yml/badge.svg)](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/agentwhiletrue-release.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)](../LICENSE)

**Agent While True** is an agent budget watch and babysitter for Codex CLI and
Claude Code sessions in KDE Konsole. It reports provider quota health and can
resume a blocked session after usage becomes available again—only when the
terminal, process identity, prompt, quota source, and policy all agree.

The primary command is `agent-while-true`. The shorter `agent-watch` command is
kept as a compatible alias, so existing scripts and the examples below continue
to work.

The current target is Manjaro/Arch Linux, KDE Plasma, Konsole, Wayland or X11,
and Python 3.12 or newer. Runtime code uses only the Python standard library.

![Claude Code session-limit menu](media/claude_out_of_quota.png)

This real prompt is handled narrowly. With fresh quota confirming the session is
exhausted, auto mode may move from the visibly selected first item to the exact
“continue automatically” item and confirm it. It never selects “upgrade your
plan.” Any different menu, cursor position, or unknown quota fails closed.

## Install

From this directory, use `pipx` so the CLI is isolated while remaining available
at `~/.local/bin/agent-while-true`:

```bash
pipx install .
agent-while-true --version
agent-while-true doctor
```

For development:

```bash
python3 -m pip install --user -e '.[dev]'
./localPipeline.sh
```

## See what is running

```bash
agent-while-true status
agent-while-true quota
```

`status` classifies visible Konsole sessions. `quota` is read-only and reports
provider availability, failures, usage percentages, and the reset time for each
known window:

```text
Claude pts/4 PID 769257
  availability: EXHAUSTED
  source:       claude-statusline
  session       100.0%  reset 03:20
```

Provider state and terminal state are intentionally separate. A quota may be
available while a terminal is active, or a terminal may show an old limit while
provider data is unavailable. Unknown or stale quota data never authorizes input.

## Watch sessions

Konsole disables input-capable D-Bus calls by default on current releases.
Enable the setting once, then restart Konsole before using ask or auto mode:

```bash
kwriteconfig6 --file konsolerc --group KonsoleWindow \
  --key EnableSecuritySensitiveDBusAPI true
```

This permission lets programs running as your desktop user type into Konsole,
which is why Agent While True layers process identity, exact prompt recognition,
policy, idempotency and immediate revalidation on top. `agent-while-true doctor`
probes the permission with an empty string and blocks auto mode if it is off.

The setting is read when a Konsole process starts. Existing windows therefore
remain input-disabled until Konsole is restarted; keep the current sessions
open until their work is safe, then restart Konsole once and require
`agent-while-true doctor` to report both `Konsole input OK` and `Auto mode OK`.
Agent While True cannot bypass this Konsole boundary, and intentionally does not
kill or replace existing terminal sessions.

Start with observe mode. It runs the complete detection path but cannot type:

```bash
agent-while-true run --observe --all
```

On an interactive terminal this opens a color dashboard inspired by btop and
ollamaFarm. Colors carry meaning: green is available/healthy, yellow is waiting
or unknown, and red is exhausted or unsafe. `NO_COLOR=1` or `--no-color`
produces plain output.

| Key | Effect |
| --- | --- |
| `-` / `+` | Refresh faster / slower across `0.25 0.5 1 2 3 5 10 30 60` seconds |
| `p` | Pause/resume; pause performs no terminal or quota polling |
| `r` | Rediscover Konsole sessions immediately |
| `t` | Cycle dark, vivid, and plain themes |
| `e` | Show or hide persisted action/state history |
| `l` | Cycle the history length through 5, 10, 20, and 50 rows |
| `h` or `?` | Toggle the in-dashboard help |
| `q` | Quit and restore the terminal |

Like btop, `+` makes the interval number larger and therefore refreshes more
slowly. Non-interactive observe output stays ANSI-free and separates scans with
a blank line for readable logs.

Other modes are:

```bash
agent-while-true run --ask       # select sessions and confirm each action
agent-while-true run --auto      # select sessions; resume policy-approved prompts
agent-while-true simulate --all  # exercise the built-in danger scenarios
```

Claude continuation is normally a bare Enter only when Claude explicitly asks
for it. Its exact three-choice menu may also be armed so Claude itself continues
at reset; set `ALLOW_CLAUDE_AUTO_WAIT=false` to disable that behavior. Codex has
no equivalent affordance, so Codex auto-resume remains disabled unless
`ALLOW_CODEX_AUTO_RESUME=true` is intentionally configured. Model downgrades,
paid credits, purchases, upgrades, and reset-credit redemption are never enabled
by the supplied configuration.

Create and inspect the default configuration with:

```bash
agent-while-true init
agent-while-true config
```

The file is `~/.config/agent-watch/config`. It is parsed as data and never
sourced as shell code. Logs and state live under
`~/.local/state/agent-watch/`; terminal contents are not logged. Agent While
True records structured state transitions and actions in
`~/.local/state/agent-watch/agent-watch.log`, including when an action was
planned, sent, verified, refused, retried, or failed. Inspect recent history
with:

```bash
agent-while-true logs -n 40
journalctl --user -u agent-watch.service -f  # service lifecycle/output
```

The dashboard's `HISTORY` panel reads the same privacy-preserving event file.
It records fingerprints and pattern IDs, never terminal text, prompts,
credentials, or environment values.

Codex is launched through a Node.js shim on current installations, so Konsole
may label its tab or foreground command `node`. Agent While True walks the child
process tree, classifies the native Codex process, reads quota from that process,
and presents the session as `Codex` in its own dashboard.

## Claude quota bridge

The bridge is the supplied `scripts/claude-statusline-proxy.sh`, not another
package, daemon, plugin, or network service. Claude Code exposes quota data only
to its configured status-line command. The bridge receives that JSON, copies
only the usage windows and reset timestamps to Agent While True's state directory,
and then runs your existing status line with the original JSON.

Without it, `agent-while-true quota` honestly reports Claude as `UNKNOWN` with
`no-statusline-file`. Prompt detection still works, but automatic mode will not
guess that quota is available.

Install and safely chain the supplied file in one command:

```bash
scripts/install-claude-bridge.sh
```

The installer copies the proxy, backs up `~/.claude/settings.json`, and preserves
the existing status-line command through the chain. To do those steps manually,
install the one supplied file:

```bash
install -Dm755 scripts/claude-statusline-proxy.sh \
  ~/.local/share/agent-watch/claude-statusline-proxy.sh
```

Configure it as Claude's `statusLine` command in `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.local/share/agent-watch/claude-statusline-proxy.sh"
  }
}
```

If a status line already exists, preserve it through
`AGENT_WATCH_STATUSLINE_CHAIN`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "AGENT_WATCH_STATUSLINE_CHAIN=~/.claude/my-statusline.sh ~/.local/share/agent-watch/claude-statusline-proxy.sh"
  }
}
```

For example, if the current command is
`~/.claude/abtop-combined-statusline.sh`, the replacement is:

```json
{
  "statusLine": {
    "type": "command",
    "command": "AGENT_WATCH_STATUSLINE_CHAIN=~/.claude/abtop-combined-statusline.sh ~/.local/share/agent-watch/claude-statusline-proxy.sh"
  }
}
```

Restart Claude Code if it does not reload the setting, wait for one status-line
render, then verify the bridge without enabling automation:

```bash
agent-while-true quota
ls -l ~/.local/state/agent-watch/quota/claude.json
```

The bridge writes an owner-only, atomically replaced quota document at
`~/.local/state/agent-watch/quota/claude.json`. Failures do not prevent the
existing status line from running.

## Background service

Install the supplied user service from this checkout:

```bash
scripts/install-user-service.sh
systemctl --user enable --now agent-watch.service
systemctl --user status agent-watch.service
```

The shipped service is observe-only. It may discover new agent tabs, but it can
never send input. After validating `doctor`, `quota`, observe mode, and the
simulations, auto mode can be explicitly enabled with:

```bash
systemctl --user edit agent-watch.service
```

```ini
[Service]
ExecStart=
ExecStart=%h/.local/bin/agent-while-true run --auto --all --no-fzf
```

Then run `systemctl --user restart agent-watch.service`. Remove the service with
`scripts/install-user-service.sh --uninstall`.

## Safety model

Immediately before any input, Agent While True re-reads and verifies:

- the explicitly selected Konsole session;
- PID, process start time, TTY, and provider classification;
- a current, known prompt and its permitted action;
- fresh provider quota with no other exhausted window;
- the persisted prompt fingerprint and retry budget.

SSH, containers, tmux/screen, unknown prompts, stale quota, provider errors,
process replacement, and paid or quality-changing choices all fail closed. A
single-instance lock and persisted `PLANNED -> SENT -> VERIFIED|FAILED` action
lifecycle prevent duplicate input across concurrent processes and crashes.

See [vision.md](vision.md) for product intent and [PLAN.md](PLAN.md) for the
original implementation sequence.

## Development and release

```bash
./localPipeline.sh
python3 -m pytest -m konsole  # set AGENT_WATCH_LIVE_KONSOLE=1 for the live test
```

The local pipeline is the canonical release gate. It checks Python 3.12+, Ruff
lint and formatting, every tracked shell script with ShellCheck, pytest with an
85% coverage floor, all built-in danger simulations, sdist/wheel construction,
and an isolated install using both `agent-while-true` and the compatibility
alias. GitHub Actions runs this same script on Python 3.12, 3.13, and 3.14.

Pushes and pull requests that touch `AgentWhileTrue/**` run the quality
workflow. A tag named `agentwhiletrue-vX.Y.Z` additionally verifies the tag
against the package version and changelog, reruns the pipeline, and publishes
the built wheel and source distribution as a GitHub release.

Release tags use `agentwhiletrue-vX.Y.Z`. The project follows semantic
versioning while major version zero denotes an alpha interface.

## License

This subproject is covered by the repository's GNU General Public License v3.
