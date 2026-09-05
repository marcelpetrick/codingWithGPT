# Agent Budget Watch contributor instructions

These instructions apply to every file below `AgentWhileTrue/`.

## Purpose and priorities

Build a conservative supervisor for Codex CLI and Claude Code sessions in KDE
Konsole. Correct refusal is more important than eager automation. Keep provider
quota state separate from terminal prompt state, revalidate immediately before
input, and fail closed on ambiguity.

Read `vision.md`, `PLAN.md`, and `README.md` before changing runtime behavior.
The real prompt captures in `media/` are evidence; transcribe them into fixtures
when recognizer behavior changes.

## Scope

- Work only on this subproject.
- GitHub Actions must live at the monorepo root `.github/workflows/`; those
  workflows must be path-filtered to `AgentWhileTrue/**` and package or release
  only this subproject.
- Preserve unrelated changes elsewhere in the monorepo.
- Do not change terminal, provider, account, subscription, or paid settings as
  a side effect of development.

## Safety invariants

- Observe mode never sends input.
- Unknown, missing, stale, or malformed quota data never means available.
- A reset timestamp alone does not authorize auto mode.
- Bind a selection to Konsole service/session plus PID, process start time, and
  TTY; never transfer an interactive selection to a replacement process.
- Re-read session identity, process class, visible prompt, and policy directly
  before `sendText`.
- Never automate upgrades, purchases, paid credits, reset credits, or model
  downgrades.
- Select Claude's automatic-wait item only for the exact tested menu with the
  cursor visibly on item 1, safe item 2, fresh exhausted quota, and
  `allow_claude_auto_wait`; every variation fails closed.
- Codex resume types into its composer and therefore remains opt-in.
- Never log terminal contents, environment values, credentials, or prompt text.
- Preserve the persisted action lifecycle and single-instance lock.
- Treat SSH, containers, tmux/screen, conflicting classification signals, and
  unsupported prompts as non-automatable.

Live Konsole sessions may be used for read-only inspection. Do not send input to
a real session unless the user has explicitly authorized that validation and
the normal policy/revalidation gate allows the exact action. Never use a paid or
quality-changing choice as a test.

## Working style

- Make one logical change per commit.
- Every feature or fix commit bumps `src/agent_watch/version.py` and adds the
  matching newest section to `CHANGELOG.md`.
- Use commit subjects in the existing style, for example
  `feat(AgentWhileTrue): ...` or `fix(AgentWhileTrue): ...`.
- Do not amend or rewrite commits that are not yours.
- Preserve uncommitted user work and inspect the worktree before staging.
- Keep runtime dependencies empty unless there is a compelling documented
  reason; Python 3.11+ standard library is the baseline.
- Keep shell limited to deployment/integration jobs and ShellCheck-clean.
- Prefer deterministic fake-terminal tests over waiting for a real quota reset.
- When a bug is found from a live prompt, add a regression fixture before the
  fix.

## Required verification

Before every commit:

```bash
ruff check .
ruff format --check .
shellcheck --severity=style scripts/*.sh
python3 -m pytest -q
git diff --check
```

Before pushing or tagging:

```bash
scripts/quality.sh
PYTHONPATH=src python3 -m agent_watch.cli simulate --all
PYTHONPATH=src python3 -m agent_watch.cli doctor
PYTHONPATH=src python3 -m agent_watch.cli status
PYTHONPATH=src python3 -m agent_watch.cli quota
```

Run the opt-in live test where KDE Konsole is available:

```bash
AGENT_WATCH_LIVE_KONSOLE=1 python3 -m pytest -q -m konsole
```

Build a wheel and install it into an isolated environment before a release.
Confirm that the installed `agent-watch --version`, `doctor`, `quota`, and
`simulate --all` commands work without `PYTHONPATH`.

## Release procedure

1. Ensure the worktree contains only intended changes.
2. Run all required verification and package smoke tests.
3. Push the atomic commits to `origin/master` only when requested.
4. Create an annotated `agentwhiletrue-vX.Y.Z` tag only for a fully verified
   version and push that tag to trigger the release workflow.
5. Verify the GitHub Actions quality and release results.

Do not tag merely because a version was bumped; intermediate versioned commits
remain normal development versions.
