# Agent status light

## Plan

1. Identify read-only status sources for the four local profiles. Allow 10 minutes.
2. Add a Python monitor and tests for the color priority. Allow 15 minutes.
3. Check live status and the light. Allow 5 minutes.

## Decisions

| ID | Outcome | Decision | Acceptance |
| --- | --- | --- | --- |
| USB-05 | Show local Claude and Codex agent status on the light. | Read each default and DMO profile. Red overrides yellow. Yellow overrides green. Show off when no agent is active. | Cover mixed states in fixtures. Query both live Codex sockets and Claude profiles. Read the result from the light. |

Use existing Codex App Server sockets and Claude's agent list command.
Keep each profile separate. Ignore idle sessions that have finished their turn.
Use the Python `websockets` library for the Codex Unix socket protocol.
Version 17.4 supports Python 3.14 and uses the BSD-3-Clause license.
The monitor reads status. It sends output only to the USB light.

## Status

| Time (CET) | Result |
| --- | --- |
| 16:57 | Confirmed the four local profile directories and two Codex control sockets. |
| 17:00 | Selected source data and color priority. |
| 17:04 | Confirmed live green and read back red, yellow and green with fixture data. |

## Resume here

1. Install the pinned requirements for the monitor.
2. Run `python3 agent_status.py --once --dry-run` to inspect the colors and reasons.
3. Run `python3 agent_status.py` to drive the light.

## Install and run

Use Python 3.14 on Linux. Run the commands from the project directory.

1. Create the virtual environment and install the monitor dependency.

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements-monitor.txt
   ```

2. Read the profile states once without setting the light.

   ```sh
   .venv/bin/python agent_status.py --once --dry-run
   ```

3. Start the monitor. Press Ctrl+C to stop it.

   ```sh
   .venv/bin/python agent_status.py
   ```

The monitor waits five seconds between scans. Use `--once` to write one color and exit.
The monitor switches the light off on Ctrl+C or SIGTERM. A one-shot command leaves its color on.
Use `--usb-port` to select one light when several are connected.

Version 0.2.0 prints its Semantic Version at startup and with `--version`.
It adds the color counts at the end of each status line.

```text
Cleware agent monitor 0.2.0
yellow claude=running claude-dmo=waiting codex=running codex-dmo=idle shown=red:0,yellow:1,green:2,off:0
```

Each count records a new display period after a successful USB write.
A scan that keeps the same color adds no count. Failed writes add no count.
The first successful write after a detected USB failure starts a new period.
Counts reset when you start the monitor. They omit the switch-off during shutdown.
A dry run labels the calculated counts `planned`.

Use the [udev setup](../README.md#setup-and-use) for USB access after replug.

## Color and source rules

| Color | Condition |
| --- | --- |
| Red | An agent reports a blocker, a Codex goal exceeds its budget, or a tracked account runs out of quota. |
| Yellow | An agent waits for a question reply or an approval. |
| Green | At least one agent runs, and the monitor sees no blocker, wait or unavailable profile. |
| Off | All detected sessions are idle, no session is present, or a profile cannot be read. The terminal shows `unavailable` for the last case. |

Red takes priority over yellow. Yellow takes priority over off and green.
An ordinary idle chat adds no wait. A completed answer that ends in a question needs a structured wait signal to turn the light yellow.

Claude uses `claude agents --json` with `CLAUDE_CONFIG_DIR` set to each profile.
Claude quotas come from the local `abtop-rate-limits.json` cache when that cache is at most five minutes old.
Codex reads the loaded threads and goals on each profile's local App Server socket.
A failed thread read adds an unavailable state. Other threads can still report red or yellow.
Codex quota refreshes at most once a minute per profile while that profile has loaded threads.
The monitor covers sessions exposed by these local interfaces. Separate Codex servers and cloud-only sessions are outside that view.
[Claude CLI reference](https://code.claude.com/docs/en/agent-view#list-sessions-as-json) ·
[Codex App Server](https://developers.openai.com/codex/app-server/) ·
[WebSocket dependency](https://pypi.org/project/websockets/17.4/)

## Verification

The installed Claude Code CLI exposed a live `waiting` state in DMO during source checks.
Both Codex profile control sockets answered read-only requests.
The live Python run found running agents and no waits at that time.
It set green. The light reported `9a 00 00 00 00 00`.
Tests use a Unix socket fixture for a thread waiting for input and a quota block.
Tests also cover mixed priorities, quota reset, unavailable data, and a USB replug retry.

The live test restored the current status after the fixture states.
Both updated C4 diagrams rendered with their monitor relationships.

## Commit review

Reviewed `7eb9bf464735de59842592c4ea4f7b8e1cfb1601` for USB-05.
The clean clone passed 23 tests, covered 233 of 233 executable lines, and caught nine mutations.
The archive passed the packaged command checks and SHA-256 verification.
The device returned `8b`, `8e` and `9a` as the first input bytes for red, yellow and green with fixture states.
Live reads confirmed both local Codex sockets and both Claude profile commands.
A live quota exhaustion and a live Codex input wait remain unobserved.
