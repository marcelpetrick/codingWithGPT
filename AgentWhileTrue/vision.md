# Agent While True — Vision

## 1. Purpose

Agent While True is a Linux-first agent budget watch and babysitter for interactive AI coding-agent sessions running inside KDE Konsole.

The first target environment is:

- Manjaro Linux
- KDE Plasma
- KDE Konsole
- Zsh as the user's interactive shell
- OpenAI Codex CLI
- Anthropic Claude Code

The tool is intended to detect when Codex or Claude Code has stopped because a usage window or subscription budget was exhausted, determine when that usage window becomes available again, wait for a configurable grace period, and then resume the blocked agent session automatically when it is safe to do so.

The tool must be conservative about terminal input. It should discover broadly, allow explicit user selection, observe continuously, act narrowly, and fail closed whenever state is ambiguous.

---

## 2. Primary Goals

The tool should:

1. discover all currently open KDE Konsole sessions;
2. determine which sessions are likely to be running Codex or Claude Code;
3. present those sessions in an interactive picker;
4. let the user explicitly select which sessions may be supervised;
5. watch selected sessions continuously;
6. detect supported usage-limit or wait-state prompts;
7. determine when the relevant provider budget or quota has reset;
8. wait an additional configurable safety delay after the nominal reset;
9. resume only the affected session;
10. verify that continuation actually succeeded;
11. avoid sending duplicate or stale terminal input;
12. log its decisions and actions locally;
13. operate without requiring root privileges;
14. work under Wayland by using Konsole's session interfaces instead of generic keyboard automation;
15. later support persistent background execution through a user-level service.

---

## 3. Non-Goals for the First Version

The first usable version should intentionally avoid unnecessary complexity.

Out of scope for v0:

- generic graphical terminal emulators other than Konsole;
- tmux pane control;
- GNU screen pane control;
- remote SSH sessions;
- containers and nested PID namespaces;
- OCR;
- screenshots;
- generic desktop keyboard injection;
- mouse automation;
- automatically purchasing credits;
- automatically switching subscriptions;
- automatically accepting paid usage;
- automatically consuming optional credits;
- arbitrary provider support;
- full daemonization as a hard requirement;
- perfect interpretation of every future Codex or Claude prompt.

These can be added later through adapters.

---

## 4. Product Philosophy

The central principle is:

> Use provider state to understand quota availability, and use terminal automation only to resume a session that has already been positively identified as blocked.

A second guiding principle is:

> Never type into a shell merely because terminal text resembles a quota message.

Automatic input should require multiple independent checks.

---

## 5. Initial User Experience

The simplest usable workflow should be:

```text
agent-watch
```

Startup flow:

```text
1. inspect environment
2. check dependencies
3. inspect Konsole D-Bus
4. enumerate Konsole sessions
5. inspect foreground processes
6. classify sessions
7. present interactive picker
8. let user choose observe / ask / auto mode
9. start monitoring
```

Example picker:

```text
Agent Watch

Select sessions to watch:

 [x] 1  Codex       pts/2   PID 14823   ~/project-alpha
 [x] 2  Claude      pts/3   PID 15102   ~/project-beta
 [ ] 3  zsh         pts/4   PID 15201   ~
 [ ] 4  Codex       pts/5   PID 15591   ~/experimental

SPACE = toggle
ENTER = start
A     = select all detected agents
R     = rescan
Q     = quit
```

Plain shell sessions should never be selected automatically.

---

## 6. Operating Modes

### 6.1 Observe Mode

```text
agent-watch --observe
```

No terminal input is ever sent.

Example:

```text
[22:13:04] Codex pts/2: ACTIVE
[22:17:32] Claude pts/3: LIMIT_BLOCKED
[22:17:32] Claude pts/3: WOULD WAIT UNTIL 23:42:00
[23:43:00] Claude pts/3: WOULD RESUME
```

This is the default development and validation mode.

---

### 6.2 Ask Mode

```text
agent-watch --ask
```

When a safe continuation is possible:

```text
Claude pts/3 is still blocked and usage is available again.

Resume this session? [Y/n]
```

---

### 6.3 Auto Mode

```text
agent-watch --auto
```

Only explicitly allowed safe actions are automated.

Default policy:

```text
normal continuation after reset = allowed
model downgrade                 = not allowed
paid credits                    = not allowed
purchase credits                = not allowed
reset credits                   = not allowed
```

---

## 7. Platform Scope

Required for the first complete Linux implementation:

- Linux
- Manjaro / Arch-family systems
- KDE Plasma
- KDE Konsole
- Wayland or X11
- Zsh as user shell
- Codex CLI
- Claude Code
- multiple Konsole windows
- multiple Konsole tabs
- multiple simultaneous Codex / Claude sessions

The program itself does not need to be written in Zsh. A Bash script is acceptable for v0 even if supervised sessions use Zsh.

---

## 8. Privilege Model

Normal operation must not require `sudo`.

Expected state:

```text
UID  = current desktop user
EUID = current desktop user
```

If the program is started through `sudo`, it should warn or abort by default.

Example:

```text
WARNING:
agent-watch should normally run as your KDE desktop user.

Running as root can:
- break access to the user's D-Bus session;
- change environment variables;
- increase the consequences of incorrect input;
- complicate process ownership checks.
```

Optional diagnostic override:

```text
--allow-root
```

Root execution is not part of normal operation.

---

## 9. Why Wayland Is Not a Primary Problem

The first implementation should not use:

```text
xdotool
ydotool
wtype
OCR
screen coordinates
mouse coordinates
global keyboard injection
```

Instead it should use KDE Konsole's per-session D-Bus interface.

This allows the tool to:

- enumerate sessions;
- inspect foreground process IDs;
- read displayed terminal text;
- send text or commands to a selected session.

Because the control path is through the terminal application rather than generic desktop input simulation, Wayland restrictions are largely avoided.

---

## 10. Konsole Discovery

The watcher should enumerate running Konsole D-Bus services.

Possible service forms include:

```text
org.kde.konsole
org.kde.konsole-<pid>
```

Every service should be checked for session objects such as:

```text
/Sessions/1
/Sessions/2
/Sessions/3
```

Each session should receive a stable internal identity for the current process lifetime.

Example:

```text
konsole-service=org.kde.konsole-4452
session=/Sessions/2
```

The watcher must periodically rediscover sessions because users may:

- open new Konsole windows;
- open new tabs;
- close tabs;
- restart Konsole;
- move between projects.

---

## 11. Process Inspection

For every Konsole session, inspect its foreground process.

Collect at least:

```text
PID
PPID
TTY
process start time
command line
executable
Konsole session
current working directory where available
```

Use `/proc` where appropriate:

```text
/proc/<pid>/cmdline
/proc/<pid>/exe
/proc/<pid>/status
/proc/<pid>/stat
```

Typical process trees:

```text
konsole
  └─ zsh
      └─ codex
```

```text
konsole
  └─ zsh
      └─ claude
```

The classifier must not rely only on one process field because wrappers and launchers may change.

---

## 12. Process Classification

Initial process classes:

```text
CODEX
CLAUDE
SHELL
SSH
TMUX
SCREEN
CONTAINER
UNKNOWN
```

Only positively identified Codex or Claude sessions should be eligible for automatic control.

If the foreground process is:

```text
zsh
bash
fish
ssh
sudo
vim
nvim
python
node
git
tmux
screen
```

automatic input should be disabled unless a future adapter specifically supports that environment.

---

## 13. Interactive Session Picker

The picker is a core safety mechanism, not just a convenience feature.

The tool should:

- discover plausible Codex / Claude sessions;
- display them with TTY, PID, project path, and provider;
- preselect only high-confidence agent sessions;
- allow user confirmation;
- remember selections for the current run;
- allow rescan while running.

If `fzf` is available, it may be used.

If not, a built-in numbered ANSI picker must exist.

`fzf` must remain optional.

---

## 14. Terminal State Inspection

The watcher should read only the currently relevant displayed terminal state.

It should not retain full scrollback.

The implementation should inspect bounded terminal text, for example:

- current screen;
- last N visible lines;
- limited recent displayed text.

Full terminal contents must not be logged.

---

## 15. Prompt Recognition

Prompt handling must use provider-specific recognizers.

Initial state classes:

```text
ACTIVE
LIMIT_WARNING
LIMIT_BLOCKED
WAITING_FOR_RESET
READY_TO_RESUME
CONTINUE_PROMPT
UNKNOWN_BLOCKING_PROMPT
PROCESS_GONE
UNSAFE
```

Recognizers may use:

- regex patterns;
- anchor text;
- provider identity;
- current TUI state;
- nearby menu choices;
- reset timestamp;
- provider version;
- expected prior state.

A single regex match must never authorize automatic input.

---

## 16. Initial Supported Prompt Types

The v0 implementation should support only a small number of tested conditions:

```text
LIMIT_REACHED
WAIT_UNTIL_RESET
CAN_CONTINUE
CONTINUE_MENU
```

Unknown state:

```text
UNKNOWN_BLOCKING_PROMPT
```

must result in:

```text
log
do nothing
```

The system should fail closed.

---

## 17. Resume Conditions

A continuation action is allowed only when all required conditions are true:

```text
session selected by user
AND
same Konsole session
AND
same process identity
AND
recognized Codex or Claude process
AND
recognized current blocking prompt
AND
quota/reset policy allows continuation
AND
no conflicting limit is still active
AND
action has not already been sent
AND
session is not marked unsafe
```

Only then may the watcher inject provider-specific input.

---

## 18. Resume Actions

The action depends on the exact provider prompt.

Possible actions:

```text
"continue" + Enter
Enter
"1" + Enter
specific arrow-key/menu sequence
```

The implementation must never assume that all prompts accept the literal word `continue`.

Each supported prompt should define its own action.

---

## 19. Verification After Resume

Sending terminal input is not equivalent to success.

After every action, verify one or more of:

- blocking prompt disappears;
- new output appears;
- provider state changes to active;
- process remains the same;
- provider reports ordinary usage is allowed;
- a new blocking prompt appears.

State transition:

```text
CONTINUE_SENT
   ├── success -> ACTIVE
   └── failure -> LIMIT_BLOCKED
```

---

## 20. Retry Policy

Example default:

```text
max_resume_attempts = 3
retry_delays        = 5s, 30s, 60s
```

Stop retrying if:

- process identity changes;
- session disappears;
- prompt becomes unknown;
- paid action is required;
- model downgrade is required;
- maximum attempts are reached.

---

## 21. Quota and Reset Model

There are two distinct sources of truth:

### Provider state

Used to determine:

```text
Is usage available?
When is the limit expected to reset?
Is another limit still exhausted?
```

### Terminal state

Used to determine:

```text
Is this exact session waiting?
What prompt is currently displayed?
What input is expected?
```

These must remain separate.

---

## 22. Codex Integration

Preferred long-term Codex integration:

```text
codex app-server --stdio
```

Use Codex app-server rate-limit information rather than repeatedly invoking interactive commands.

Relevant information may include:

```text
used percentage
window duration
reset timestamp
ordinary usage allowed
limit classification
reset credit state
```

The watcher should treat a provider-level authorization flag such as `ordinaryUsageAllowed` as stronger than merely checking whether a wall-clock reset time has passed.

Reason:

A nominal reset timestamp may pass while usage is not yet actually available.

---

## 23. Claude Code Integration

Preferred long-term Claude integration:

Use Claude Code's status-line data as a passive source of quota state.

Useful data may include:

```text
five-hour usage percentage
five-hour reset timestamp
seven-day usage percentage
seven-day reset timestamp
```

Conceptual integration:

```text
Claude Code
    |
    | status-line JSON
    v
agent-watch statusline proxy
    |
    +--> watcher state
    |
    +--> user's original status-line script
```

The proxy must preserve any pre-existing user status-line configuration.

---

## 24. Reset Grace Period

The watcher must never assume a quota becomes usable at the exact nominal timestamp.

Default:

```text
RESET_GRACE=60
```

Meaning:

```text
resume candidate time = provider reset time + 60 seconds
```

Configurable examples:

```text
--reset-grace 90s
```

or:

```text
RESET_GRACE=90
```

The watcher should re-check provider and terminal state after the grace period before acting.

---

## 25. Multiple Limits

The tool must not assume only one five-hour window exists.

Possible simultaneous constraints:

```text
short-window limit
five-hour/session limit
weekly limit
seven-day limit
spend/credit limit
provider-specific restriction
```

A reset of one limit must not trigger resume if another relevant limit remains exhausted.

---

## 26. Polling Model

Separate local monitoring from provider polling.

### Terminal scan

Suggested:

```text
2 seconds
```

Local work may include:

```text
D-Bus
/proc
process tree
displayed terminal state
```

### Provider usage refresh

Suggested fallback:

```text
60 seconds
```

Prefer event-driven provider updates when possible.

If a reset timestamp is known, schedule directly for:

```text
reset_at + grace
```

instead of continuously polling.

---

## 27. Runtime State Machine

Recommended per-session state machine:

```text
DISCOVERED
   |
   v
ACTIVE
   |
   v
LIMIT_WARNING
   |
   v
LIMIT_BLOCKED
   |
   v
WAITING_FOR_RESET
   |
   v
RESET_GRACE_PERIOD
   |
   v
READY_TO_RESUME
   |
   v
CONTINUE_SENT
   |
   v
VERIFYING
   | \
   |  \ failure
   |   \
   v    v
ACTIVE  LIMIT_BLOCKED
```

Additional terminal states:

```text
UNSAFE
UNKNOWN
PROCESS_GONE
UNSUPPORTED
```

These states must never trigger automatic input.

---

# 28. Dangerous Conditions That Must Be Considered

The following are safety-critical.

## DANGER 1 — PID Reuse

Linux can reuse process IDs.

A session must never be identified by PID alone.

Use a composite identity:

```text
PID
+
process start time
+
TTY
+
Konsole session
```

---

## DANGER 2 — Agent Returned to Zsh

Scenario:

```text
codex exits
↓
zsh becomes foreground
↓
old reset timer fires
↓
watcher types "continue"
```

This must never happen.

Immediately before every injected input:

```text
re-read foreground PID
re-read executable
re-read process start time
re-read TTY
re-read Konsole session
```

If anything changed, cancel the action.

---

## DANGER 3 — Historical Prompt Text

A visible message such as:

```text
You have reached your usage limit
```

may be old output.

Text presence alone cannot authorize action.

The watcher should combine:

```text
current displayed state
recent screen transition
known provider state
expected prior state
process identity
```

---

## DANGER 4 — Multiple Watcher Instances

Two watcher instances could send duplicate input.

Use a per-user lock, for example:

```text
$XDG_RUNTIME_DIR/agent-watch.lock
```

Possible implementation:

```text
flock()
```

Only one automatic controller should exist by default.

---

## DANGER 5 — Running as Root

Running as root is unnecessary for normal operation and makes bugs more dangerous.

The watcher should normally run as the KDE desktop user.

---

## DANGER 6 — tmux / screen

Example:

```text
Konsole
  └─ zsh
      └─ tmux
```

The visible Konsole session may contain several hidden panes.

v0 should classify this as:

```text
UNSUPPORTED_NESTED_TERMINAL
```

and never automate it.

---

## DANGER 7 — SSH

If Codex or Claude runs on a remote machine behind SSH, local PID and provider assumptions may become invalid.

v0 should detect SSH and refuse automatic control.

---

## DANGER 8 — Containers

Docker, Podman, Distrobox, chroot, and PID namespaces can alter process identity.

v0 should classify obvious container cases as unsupported unless explicitly handled.

---

## DANGER 9 — Suspend / Resume

Scenario:

```text
reset scheduled at 02:00
laptop sleeps at 01:30
laptop wakes at 08:00
```

Never replay stale pending actions.

On resume:

```text
rediscover sessions
revalidate process
reread prompt
refresh provider state
recalculate timers
decide again
```

---

## DANGER 10 — Clock Changes

NTP, manual time corrections, and timezone changes may affect wall-clock calculations.

Use:

- wall-clock timestamps for provider reset times;
- monotonic time for local retry and delay intervals.

---

## DANGER 11 — Provider UI Changes

Codex or Claude may change:

```text
wording
menu entries
keyboard behavior
layout
ANSI rendering
prompt ordering
```

Provider prompt definitions should be versioned.

Unknown layouts must result in:

```text
UNSUPPORTED_PROMPT
```

not a guessed action.

---

## DANGER 12 — Locale Changes

Different `LANG` / `LC_ALL` values may alter:

```text
date formatting
time formatting
translated strings
decimal separators
AM/PM behavior
```

Machine-readable provider APIs should be preferred over parsing human text.

---

## DANGER 13 — Crash Between Send and Persist

Scenario:

```text
watcher sends Enter
↓
watcher crashes
↓
watcher restarts
↓
same prompt still visible
↓
watcher sends Enter again
```

Actions should have a lifecycle:

```text
PLANNED
SENT
VERIFIED
FAILED
```

Persist enough state to avoid immediate duplicates.

---

## DANGER 14 — Insecure IPC

The watcher may eventually expose a local Unix socket.

Because the watcher can effectively type into terminals, all IPC must be restricted to the current UID.

Use:

```text
$XDG_RUNTIME_DIR
0600 or equivalent permissions
no TCP listener by default
```

---

## DANGER 15 — Logging Secrets

Terminal output may contain:

```text
API keys
passwords
source code
customer data
tokens
internal URLs
credentials
```

Full terminal output must not be logged by default.

Log events, not content.

---

## DANGER 16 — Wrong Shell Injection

The watcher must never inject a command into an idle shell.

Foreground process classes such as:

```text
zsh
bash
fish
sudo
ssh
vim
nvim
python
node
git
```

must disable automatic action.

---

## DANGER 17 — Duplicate Prompt Recognition

The same screen may be scanned many times.

Use a prompt fingerprint or prompt generation ID to ensure:

```text
one logical prompt
=
one possible action
```

---

## DANGER 18 — Process Restart With Same Project

A Codex or Claude process may restart inside the same tab and directory.

The watcher must treat the new process as a new identity even if the project path is unchanged.

---

## DANGER 19 — Provider Unavailable

If the quota API or provider integration becomes unavailable:

```text
do not infer that usage is allowed
```

Unknown provider state should result in:

```text
WAIT / ASK / FAIL CLOSED
```

depending on configured mode.

---

## DANGER 20 — Changed Session Selection

If a user closes a selected tab and creates a new tab with the same session number later, the old selection must not silently transfer.

Selections must be bound to current identities, not just visible numeric labels.

---

## 29. Reliability Requirements

### Idempotency

The same logical prompt must not receive multiple continuation actions.

Possible idempotency key:

```text
provider
Konsole service
Konsole session
process start time
prompt fingerprint
```

---

### Persistent State

Longer-term version should store minimal state under:

```text
$XDG_STATE_HOME/agent-watch/
```

normally:

```text
~/.local/state/agent-watch/
```

Possible state:

```text
selected sessions
known reset timestamps
last action
action result
retry count
provider state
prompt fingerprint
```

---

### D-Bus Reconnection

If Konsole or the KDE user session changes, the watcher should rediscover rather than permanently failing.

---

### Provider Failure Isolation

Codex adapter failure must not stop Claude monitoring.

Claude adapter failure must not stop Codex monitoring.

---

## 30. Logging

Default log:

```text
~/.local/state/agent-watch/agent-watch.log
```

Configurable:

```text
--log-file /path/to/file
```

Recommended fields:

```text
timestamp
level
provider
Konsole service
Konsole session
PID
TTY
event
previous state
new state
reset time
action
attempt
result
```

Example:

```text
2026-09-05T22:17:31+02:00 INFO provider=claude session=2 state=LIMIT_BLOCKED
2026-09-05T22:17:31+02:00 INFO provider=claude session=2 reset=2026-09-05T23:42:00+02:00
2026-09-05T23:43:00+02:00 INFO provider=claude session=2 action=continue
2026-09-05T23:43:03+02:00 INFO provider=claude session=2 result=resumed
```

Do not log arbitrary terminal contents.

---

## 31. Log Rotation

Suggested:

```text
max_log_size = 10 MB
log_backups  = 5
```

For a shell-script MVP this may initially be simplified.

---

## 32. Git Ignore Behavior

The default log path is outside repositories and therefore does not need `.gitignore`.

If the user chooses a repository-local log path, prefer adding it to:

```text
.git/info/exclude
```

because the log is a local development artifact.

Optional mode:

```text
--git-ignore-mode gitignore
```

may add it to the tracked `.gitignore`.

---

## 33. Configuration

Simple v0 configuration:

```text
~/.config/agent-watch/config
```

Example:

```text
SCAN_INTERVAL=2
USAGE_POLL_INTERVAL=60
RESET_GRACE=60
MODE=ask
LOG_FILE="$HOME/.local/state/agent-watch/agent-watch.log"
MAX_RESUME_ATTEMPTS=3
```

Later implementation may move to TOML.

Example future config:

```toml
reset_grace = "60s"
terminal_scan_interval = "2s"
usage_poll_interval = "60s"
max_resume_attempts = 3

log_file = "~/.local/state/agent-watch/agent-watch.log"

[providers.codex]
enabled = true

[providers.claude]
enabled = true
statusline_bridge = true

[policy]
resume_after_reset = true
auto_accept_model_downgrade = false
auto_use_paid_credits = false
auto_buy_credits = false
auto_consume_reset_credit = false
```

Configuration precedence:

```text
defaults
<
config file
<
environment
<
CLI arguments
```

---

## 34. Suggested CLI

```text
agent-watch
agent-watch run
agent-watch run --observe
agent-watch run --ask
agent-watch run --auto
agent-watch status
agent-watch doctor
agent-watch init
agent-watch logs
agent-watch config
```

Optional later:

```text
agent-watch run --daemon
```

---

## 35. `doctor` Command

`agent-watch doctor` should check:

```text
Linux distribution
KDE Plasma presence
Konsole D-Bus availability
Konsole session enumeration
qdbus / qdbus6
Codex executable
Codex version
Codex app-server support
Claude executable
Claude version
Claude status-line capability
state directory permissions
log directory permissions
runtime directory permissions
single-instance lock
```

Example:

```text
Agent Watch Doctor

Linux               OK
KDE Plasma          OK
Konsole D-Bus       OK
qdbus6              OK
Codex               0.x.x
Codex app-server    OK
Claude              2.x.x
Claude statusline   OK
Runtime dir         OK
State dir           OK
Auto mode           SAFE
```

---

## 36. TUI While Running

The MVP does not need a full TUI framework.

Simple ANSI output is enough:

```text
Agent Watch 0.1

Watching 3 sessions

 ID    TYPE     STATE               RESET       PID
 ---------------------------------------------------
 1     Codex    ACTIVE              -           14823
 2     Claude   WAITING_FOR_RESET   23:42       15102
 4     Codex    LIMIT_BLOCKED       checking    15591

 Last action:
 22:17:31 Claude pts/3 limit detected

 [r] rescan
 [s] sessions
 [l] log
 [p] pause
 [q] quit
```

---

## 37. Dependency Strategy

Required or commonly available:

```text
qdbus or qdbus6
ps
pgrep
pstree
readlink
awk
sed
grep
flock
```

Optional:

```text
jq
fzf
```

The MVP should degrade gracefully if optional tools are missing.

---

## 38. Background Operation

The first release may simply run in the foreground.

Longer-term preferred deployment:

```text
systemctl --user enable --now agent-watch.service
```

A user-level systemd service is preferred over a root service because it naturally runs with:

```text
the correct UID
the KDE user D-Bus environment
the user's home directory
the correct provider credentials
```

The standalone CLI must remain usable without systemd.

---

## 39. First Implementation Language

### MVP

A Bash script is acceptable.

Advantages:

```text
fast prototype
easy process inspection
easy qdbus integration
easy deployment
simple iteration
```

The supervised shell may still be Zsh.

---

### Production

Rust is the preferred long-term implementation.

Potential components:

```text
tokio
zbus
serde
toml
regex
tracing
tracing-appender
procfs or direct /proc parsing
```

Reasons:

```text
single binary
low idle overhead
strong state modeling
reliable async timers
D-Bus integration
JSON-RPC integration
better long-running daemon behavior
```

Python is a reasonable intermediate prototype if Bash becomes too complex.

---

## 40. Test and Simulation Mode

A real quota reset may take hours, so the implementation must eventually include simulation.

Required test scenarios:

```text
limit reached
reset after 30 seconds
reset delayed by 90 seconds
weekly limit still active
provider API unavailable
prompt changed
terminal closed
process restarted
PID reused
session replaced
laptop suspend
duplicate event
watcher crash
continue fails
continue succeeds
unknown menu
paid credits prompt
model downgrade prompt
```

Dry-run mode:

```text
agent-watch --observe
```

must execute all detection logic but never inject input.

---

## 41. Acceptance Criteria for v0

The first usable milestone is complete when:

1. Konsole sessions can be enumerated.
2. Foreground processes can be identified.
3. Obvious Codex sessions are classified.
4. Obvious Claude sessions are classified.
5. Plain Zsh sessions are not automatically controlled.
6. User can select multiple sessions.
7. Selected sessions can be monitored.
8. One known Codex/Claude blocking prompt can be detected.
9. Observe mode works.
10. Ask mode works.
11. One explicitly supported continuation action can be sent.
12. The process identity is revalidated immediately before input.
13. Duplicate action is prevented.
14. Logs are written.
15. Full terminal contents are not logged.
16. Tool works without sudo.
17. Tool works under KDE Wayland.
18. Closing one watched terminal does not break the others.
19. Unknown prompts fail closed.
20. Restarting the watcher does not immediately repeat stale input.

---

## 42. Acceptance Criteria for v1

A fuller v1 should additionally prove:

1. new Konsole tabs are discovered automatically;
2. multiple simultaneous Codex and Claude sessions are handled independently;
3. Codex provider rate-limit state is integrated;
4. Claude quota/reset state is integrated;
5. reset timestamp plus configurable grace period works;
6. five-hour reset does not override a weekly-limit block;
7. system suspend across reset is safe;
8. provider failure does not cause unsafe continuation;
9. crash recovery avoids duplicate input;
10. systemd user service works;
11. `doctor` explains unsupported states;
12. model downgrade and paid credits remain opt-in;
13. state survives watcher restart;
14. D-Bus reconnection works;
15. unsupported tmux/SSH/container cases are identified clearly.

---

## 43. Suggested Development Sequence

### Phase 1 — Konsole Proof of Concept

Implement:

```text
discover sessions
identify foreground PID
classify process
read displayed text
send controlled test input
```

---

### Phase 2 — Interactive Picker

Implement:

```text
session list
multi-select
rescan
selected-session tracking
```

---

### Phase 3 — Observe Mode

Implement:

```text
prompt recognition
state machine
logging
no automatic input
```

---

### Phase 4 — Ask Mode

Implement:

```text
supported prompt
user confirmation
safe continuation
post-action verification
```

---

### Phase 5 — Automatic Resume

Implement:

```text
identity validation
reset timer
grace period
single-instance lock
idempotency
retry
verification
```

---

### Phase 6 — Provider Integrations

Add:

```text
Codex app-server adapter
Claude status-line adapter
multiple-limit handling
provider failure isolation
```

---

### Phase 7 — Persistence

Add:

```text
state file
crash recovery
action lifecycle
prompt fingerprints
restart protection
```

---

### Phase 8 — Background Service

Add:

```text
systemd --user service
doctor command
init command
packaging
```

---

## 44. Architecture Evolution

### v0

```text
Bash TUI
   |
   +--> qdbus / Konsole
   |
   +--> /proc
   |
   +--> prompt recognizers
   |
   +--> log
```

---

### v1

```text
agent-watch supervisor
        |
        +--> Konsole adapter
        |
        +--> process classifier
        |
        +--> Codex provider adapter
        |
        +--> Claude provider adapter
        |
        +--> state machine
        |
        +--> policy engine
        |
        +--> logger
        |
        +--> persistent state
```

---

### Future Adapter Model

```text
TerminalAdapter
    KonsoleAdapter
    future KittyAdapter
    future WezTermAdapter
    future TmuxAdapter

ProviderAdapter
    CodexAdapter
    ClaudeAdapter
    future providers
```

---

## 45. Final Design Rule

The watcher is allowed to act only when it knows:

```text
WHAT process it is controlling
WHICH terminal session owns it
WHY the process is blocked
WHEN usage is available again
WHAT input the current prompt expects
WHETHER that action is allowed by policy
WHETHER the same action has already been attempted
```

If any of those are unknown:

```text
do not type
```

That behavior is the core safety boundary of the project.

---

## 46. Short Vision Statement

Agent While True should become a lightweight Linux supervisor for interactive coding-agent sessions: aware of Konsole sessions, aware of provider usage windows, conservative about input, resilient to resets and crashes, and simple enough to launch from a terminal without requiring root privileges or desktop automation.

The first version should stay intentionally narrow:

```text
Manjaro
KDE Konsole
Zsh
Codex
Claude Code
local sessions
explicit picker
observe / ask / auto
safe continuation
local log
```

Everything else should be added only after that path is reliable.
