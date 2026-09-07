# Remaining steps

Agent While True 0.27.2 is built, installed, tested, pushed, and released. The
code, Claude quota bridge, provider detection, quota readers, TUI, event
history, local pipeline, and GitHub workflows are working. These are the
remaining machine-level acceptance steps.

## 1. Restart Konsole safely

- [ ] Finish, save, or deliberately stop the work in every currently open
  Konsole session.
- [ ] Close every running Konsole window, then start Konsole again.

The required setting is already stored in `konsolerc`:

```bash
kwriteconfig6 --file konsolerc --group KonsoleWindow \
  --key EnableSecuritySensitiveDBusAPI true
```

Konsole reads this security-sensitive setting when its process starts. All six
processes tested on 2026-09-06 still rejected an empty `sendText`, so automatic
continuation cannot work in those old processes. Do not kill them merely to
complete this checklist; restart only after their current work is safe.

## 2. Verify the restarted environment

- [ ] Run the doctor:

  ```bash
  agent-while-true doctor
  ```

- [ ] Require both of these results before enabling automation:

  ```text
  Konsole input          OK    sendText permitted
  Auto mode              OK    SAFE
  ```

- [ ] If either still fails, fully exit every Konsole process, re-run the
  `kwriteconfig6` command above, reopen Konsole, and run the doctor again.

## 3. Confirm live provider state

- [ ] Start one Codex and/or Claude Code session in the restarted Konsole.
- [ ] Confirm classification and quota reads:

  ```bash
  agent-while-true status
  agent-while-true quota
  ```

Codex may appear as `node` in Konsole because its launcher is a Node.js shim.
Agent While True should classify its native child and display the session as
`Codex`. Claude should report `claude-statusline`; Codex should report
`codex-rollout`. `UNKNOWN`, `STALE`, and provider errors must never authorize
input.

## 4. Observe before enabling input

- [ ] Run the read-only dashboard for several scans:

  ```bash
  agent-while-true run --observe --all
  ```

- [ ] Confirm the correct sessions, provider names, states, quota values, and
  reset times are shown.
- [ ] Exercise `+`, `-`, `p`, `r`, `t`, `e`, `l`, `h`, and `q`.

## 5. Start automatic babysitting

- [ ] For safe Claude automation with Codex text injection disabled, run:

  ```bash
  agent-while-true run --auto --all --no-fzf
  ```

- [ ] To explicitly allow Codex continuation text as well, run:

  ```bash
  AGENT_WATCH_ALLOW_CODEX_AUTO_RESUME=true \
    agent-while-true run --auto --all --no-fzf
  ```

The Codex option is deliberately explicit because Codex has no provider-owned
“press Enter to continue” affordance: resuming it types continuation text into
the composer. Paid credits, purchases, upgrades, reset-credit redemption, and
model downgrades remain forbidden regardless of this option.

## 6. Verify history after a real reset

- [ ] After the next genuine limit/reset cycle, inspect the recorded actions:

  ```bash
  agent-while-true logs -n 50
  ```

- [ ] Confirm the history contains the relevant state changes and, when an
  action occurred, its `PLANNED`, `SENT`, and `VERIFIED` or `FAILED` lifecycle.
- [ ] Confirm no terminal text, prompt content, credentials, or environment
  values were persisted.

The structured history is stored at
`~/.local/state/agent-watch/agent-watch.log`. Service lifecycle and output can
also be followed with:

```bash
journalctl --user -u agent-watch.service -f
```

## Acceptance criteria

The remaining work is complete when the restarted Konsole passes `doctor`, an
observe run identifies the intended sessions, auto mode survives a genuine
quota reset, the expected session continues exactly once, and the event log
records the action without recording terminal content.
