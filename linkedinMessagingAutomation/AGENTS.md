# AGENTS.md: LinkedIn reply desk

This file takes precedence over `../AGENTS.md` where they differ. Read these first:

- `vision.md`: goal, research on routes and terms, product, owner decisions.
- `plan.md`: the living document. Phases, status table, "Resume here". Update it after every step.

## Hard limits (never break these)

The owner's account must never get blocked. The rule is: no heavy traffic, human pace, human session.

1. Never send a LinkedIn message, invitation, acceptance or reaction from code. The owner sends every reply by hand.
2. Never click, type, scroll or navigate on linkedin.com from code. Route I reads the open tab only (attach, read, detach).
3. Use only a visible Chrome window with the owner's own login. No headless browser, no `li_at` cookie in scripts, no Voyager calls, no third-party login SaaS.
4. Do not hide automation (no fingerprint spoofing, no captcha solving, no stealth plugins).
5. Read LinkedIn data only by the routes marked "Primary", "Fallback" or "Always on" in `vision.md` §1.2.
6. Do not add a route marked "Owner decision" (for example I+, active navigation) until the owner decides it in `vision.md` §4. If decided, apply the caps in `vision.md` §1.4.
7. Stop at once on a login wall, captcha, "unusual activity" page, HTTP 429 or 999, or an empty read. Do not retry. Never book a stop as data.
8. Poll route A (DMA API) at most once per hour.

## Tests and requests (be careful)

1. No test, script or CI job contacts linkedin.com or api.linkedin.com.
2. Tests use saved, anonymized fixtures, a fake LinkedIn page server and a fake LLM.
3. A live check is manual, one page or one API call, behind `LIVE_LINKEDIN=1`. Write down each live check in `plan.md`.
4. Keep a guard test that fails if the code contains a send, click, type or navigate call against LinkedIn.

## Data

1. Keep message and profile data local. Never commit it, never log message text, never send it to a service other than the configured LLM.
2. Anonymize every fixture before it goes into `tests/fixtures/`.
3. Keep secrets and the Chrome profile in `~/.config/linkedin-reply-desk/`. Never put them in the repo.

## Engineering rules (owner's standard for all software)

- Work on the current branch (`master` in this repo). Use atomic commits with Conventional Commit messages.
- Commit locally. Push only when the owner asks (2026-10-27: "commit locally").
- Use semver. Every commit bumps the patch version. A major feature bumps the minor version.
- Make every commit green before you commit.
- Set up `localPipeline.sh` first. It runs tests, lint, format check, type/static checks, coverage and build. Add e2e checks when the UI exists.
- Keep the test coverage at 95% or more.
- Make the GitHub Actions workflow mirror `localPipeline.sh`. Keep it green.
- Use unit, integration and end-to-end tests where they fit. Do not skip a requirement.
- Write small reusable scripts for repeated tasks. Document each script (purpose, usage, exit codes).
- License: GPLv3 or later. Add `LICENSE` and a copyright/license header to each source file.
- `README.md`: badges like `~/repos/myLastFmPlayer`; setup, test, pipeline, usage; one real UI screenshot.
- Docker: not now (owner, 2026-10-27). Do not add it until the owner asks.
- Before you finish a phase: run `/reviewBranch` and fix the findings. At the end, run `/githubAbout`.
- Do a final check against every item in `vision.md` before you call the product done.

## Monorepo notes

- This project lives in `codingWithGPT/linkedinMessagingAutomation/`. Its CI workflow must use a
  `paths:` filter for this directory, and `working-directory` for every step.
- Keep the version in `pyproject.toml` of this project. Tags use the prefix `linkedinMessagingAutomation-v`.

## Writing

Use Simplified Technical English (see `../AGENTS.md`). Put the verdict first.
