# Plan: LinkedIn reply desk

Living document for the build. The goal and the research are in `vision.md`. The rules are in `AGENTS.md`.

## Verdict so far

Research is done. No code yet. The read routes are route I (passive Chrome DevTools capture) and route A
(DMA API). The tool never sends. Next step: phase 0, the spikes.

## Phases

| Phase | Content | Exit check | Estimate |
|---|---|---|---|
| 0a | Spike route I: dedicated Chrome profile, owner logs in, capture 1 thread, 1 invitation list, 1 profile. Zero navigation from code. | 3 anonymized page fixtures in `tests/fixtures/pages/` | 1 h |
| 0b | Spike route A: app, token, `INBOX` + `INVITATIONS` snapshot, 1 changelog call. Request a route B export in parallel. | Anonymized JSON fixtures in `tests/fixtures/dma/` | 1 h + wait ≤ 24 h |
| 1 | Skeleton: layout, `pyproject.toml` (version 0.1.0), `localPipeline.sh`, CI with `paths:` filter, GPLv3, README with badges | Pipeline green local and in CI | 2 h |
| 2 | Collectors: CDP read-only client, page parsers, DMA client, export importer, SQLite store, merge, "pending" logic | Unit + integration tests on fixtures, fake page server | 4 h |
| 3 | Classifier, ruleset engine, drafts, prompts (from the GPT + personal notes) | One golden case per rule, fake LLM | 3 h |
| 4 | UI: queue, detail, Capture button, Copy + open thread, keyboard, profile hint | e2e test (Playwright on the local UI and the fake page server only) | 4 h |
| 5 | Learn loop: "save as rule example", rule editor | e2e test | 2 h |
| 6 | Background sync for route A (systemd user timer, hourly), token expiry warning | Integration test | 1 h |
| 7 | `/reviewBranch` and fixes, `/githubAbout`, real screenshot, final check against `vision.md` | All green, tree clean | 2 h |

Route I+ (active navigation) is not in the plan. It enters only if the owner decides D2.

## Safety checks in every phase

1. No test, script or CI job contacts linkedin.com or api.linkedin.com.
2. A live run is manual, one page or one API call, behind `LIVE_LINKEDIN=1`.
3. A guard test fails if the code contains a send, click, type or navigate call against LinkedIn.
4. A stop condition (login wall, captcha, 429, 999, empty read) stops the run. It is never booked as data.

## Status

| Date | Step | Result |
|---|---|---|
| 2026-10-27 | Research: API, terms, grey-zone tools | Route A found (DMA, official). D, E, F, H rejected. |
| 2026-10-27 | Owner input: Chrome + DevTools idea, no heavy traffic | Route I (passive capture) added as primary on-demand route. Safety rules in `vision.md` §1.4. |
| 2026-10-27 | `vision.md`, `AGENTS.md`, `plan.md` written | Committed locally, not pushed |
| 2026-10-27 | Research: approved partners, delegation, tools of creators and teams | No partner route for personal DMs; no delegate role. Teams use shared logins or session tools (grey). `vision.md` §1.6. Design unchanged. |
| 2026-10-27 | Research: detection and user reports per grey tool; owner asks for automation | No grey tool fits (most are outreach senders). Automation = read + draft + notify, not send. `vision.md` §1.7–1.8. |
| 2026-10-27 | Side task: report + two LinkedIn carousels on automation and the crackdown 2025–2026 | `research/automation_crackdown_2025_2026.md`, `carousel/v1_timeline.pdf` (9 slides), `carousel/v2_status_codes.pdf` (7 slides), `carousel/post.md`. Build: `scripts/build_carousel.sh`. Self-review fixed 4 issues (contradiction on DM reading, slide count, unsupported "mostly", overflow on v2 slide 2). |

## Resume here

- State: planning done, no code. Open owner decisions: D1, D2, D3 (`vision.md` §4).
- Owner actions before phase 0:
  1. Export the "unsolicited decline" GPT instructions (GPT editor → Configure → Instructions) into `prompts/unsolicited_decline.md`.
  2. For 0b: create the app at developer.linkedin.com (`vision.md` §1.5, steps 1–2).
  3. For 0b: request the data export (LinkedIn → Settings → Data privacy → Get a copy of your data).
- Start 0a:
  ```
  google-chrome --user-data-dir=$HOME/.config/linkedin-reply-desk/chrome \
    --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1
  ```
  Log in by hand, open one message thread, then run the capture spike.
- Check: `git log --oneline -- linkedinMessagingAutomation/`
