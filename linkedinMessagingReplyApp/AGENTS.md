# AGENTS.md: LinkedIn Reply Assistant

This file takes precedence over `../AGENTS.md` where they differ. Read these first:

- `VISION.md`: the product, the architecture, the gates and the 30 acceptance criteria.
- `plan.md`: the living document. Decisions, gates, the commit log with one check per commit, "Resume here".
  Update it with every commit.

Sibling project: `../linkedinMessagingAutomation/` ("reply desk", 2026-10-27). It reads LinkedIn over
CDP and the DMA API. This project reads **pixels** from the screen. The two projects share the safety
rules below. They do not share code (decision D10 in `plan.md`).

## Hard limits (never break these)

The owner's account must never get blocked. The rule is: no extra traffic, human pace, human session.

1. Never send a LinkedIn message, invitation, acceptance or reaction from code. The owner presses Send.
2. Never click, scroll or navigate on linkedin.com from code. Never focus or press the Send button.
3. Use only the owner's own visible browser and own login. No headless browser against linkedin.com, no
   `li_at` cookie, no Voyager calls, no LinkedIn credentials, no third-party login service.
4. Do not hide automation. No fingerprint spoofing, no captcha solving, no stealth plugins, no simulated
   "human" behavior.
5. The application makes **zero** requests to linkedin.com or api.linkedin.com. It reads the screen only.
6. No autonomous work: no inbox polling, no opening of threads or profiles, no timer that starts a capture.
   Every capture starts from a button press or the owner's hotkey.
7. Stop on an empty or unreadable capture. Never book it as a message. Show the reason in the UI.

## Bent rules (documented, owner request 2026-10-28: "bend them, do not break them")

The sibling rules say "never type on linkedin.com from code" and "read only by registered routes".
This project bends two of them. Each bend has a fence that a guard test enforces.

| # | Sibling rule | Bend | Fence |
|---|---|---|---|
| B1 | Read only by the routes in the sibling `vision.md` §1.2 | New route **S, screen capture**: the portal stream of the owner's own browser window. It makes zero requests to LinkedIn. It is safer than route I (no debugger attached). | Read-only. The owner picks the window in the portal dialog. Frames stay in memory. |
| B2 | Never type on linkedin.com from code | The extension puts the **approved** draft into the composer, like a paste. | Only after an explicit **Insert** press. Only into an **empty** composer on `/messaging/` of the active tab. No click, no key event, no Send, no navigation. It reads only the thread title and the URL (conversation check) and the composer (read-back). **Copy Draft** is always available as the rule-clean path. |

`tests/unit/test_guard.py` scans `src/` and `extension/` and fails on: `.click(`, a Send-button selector,
`form.submit`/`requestSubmit`, `KeyboardEvent`, `location.assign`/`location.href =`, `tabs.update` with a
URL, `tabs.create`, `li_at`, `voyager`, and any HTTP client call to `linkedin.com`.

## Tests and requests

1. No test, script or CI job contacts linkedin.com. Browser tests intercept every request with a
   Playwright route and serve a local fake page. An unrouted request fails the test.
2. Tests use the deterministic capture test window, sanitized fixtures and a fake LLM backend.
3. Live Ollama tests carry the marker `live_ollama` and are off by default (`LIVE_OLLAMA=1`).
4. The Ollama box (`192.168.100.67`) is a shared resource. Before a live run, check `api/ps`. If another
   model is loaded and in use, wait. Do not reconfigure, upgrade or restart the box.

## Data

1. Do not write screenshots, message text or reply history to disk by default. Debug captures are opt-in.
2. Logs record events, never message text (redaction filter, tested).
3. Fixtures are synthetic or anonymized. No real LinkedIn content goes into git.
4. Owner settings live in `~/.config/linkedin-reply-assistant/`. The repo ships defaults only.

## Engineering rules (owner's standard)

- Work on `master` (the owner said "main"; this repo's main branch is `master`).
- Atomic commits, Conventional Commit messages, the body says why.
- Semver in `src/linkedin_reply_assistant/version.py`. Every commit bumps the patch version. A gate or a
  major feature bumps the minor version.
- Every commit is green (`./localPipeline.sh`) before you commit. Push after every commit (owner, 2026-10-28).
- Add one row per commit to the commit log in `plan.md`: version, subject, the check you ran, the result.
- `localPipeline.sh` is the only quality gate: install, license headers, ruff lint, ruff format, mypy
  strict, guard, pytest with branch coverage ≥ 95%, build, wheel smoke, e2e, docker build + smoke.
- GitHub Actions mirror `localPipeline.sh` (`paths:` filter on this directory, `working-directory` per
  step). A second workflow builds the Docker image and publishes it to GHCR.
- GPLv3 or later. `LICENSE` file, SPDX header in every source file.
- Small scripts for repeated tasks in `scripts/`, each with purpose, usage and exit codes in its header.
- `README.md`: badges like `~/repos/myLastFmPlayer`, setup, tests, pipeline, Docker, usage, one real screenshot.
- Before you call the product done: `/reviewBranch` and fix the findings, `/githubAbout`, a final check
  against every item in `VISION.md`, a green pipeline, green CI, a working image, a clean tree.

## Monorepo notes

- The project lives in `codingWithGPT/linkedinMessagingReplyApp/`. Tags use the prefix
  `linkedinMessagingReplyApp-v`. The image is `ghcr.io/marcelpetrick/linkedin-reply-assistant`.

## Writing

Use Simplified Technical English (see `../AGENTS.md`). Put the verdict first.
