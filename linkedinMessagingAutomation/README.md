# LinkedIn reply desk

[![linkedin-reply-desk](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/linkedin-reply-desk.yml/badge.svg?branch=master)](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/linkedin-reply-desk.yml)
[![License: GPL v3 or later](https://img.shields.io/badge/license-GPLv3%20or%20later-blue.svg)](LICENSE)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14%2B-3776ab.svg)](https://www.python.org/)
[![Coverage: 100%](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](pyproject.toml)

A local tool that reads your LinkedIn messages and connect requests, applies your ruleset, and writes a
draft reply for each one. **It never sends.** You check, edit and send every reply yourself.

**Author: Marcel Petrick <mail@marcelpetrick.it>**

**License: GPLv3 or later. See [`LICENSE`](LICENSE).**

**Note: project is generated with AI.**

## Status

Phase 1 of 7 is done (skeleton and quality gate). The ruleset engine (`reply_desk/rules.py`) is done.
There is no UI yet, so there is no screenshot yet.
The plan, the status and "Resume here" are in [`plan.md`](plan.md).

| Document | Content |
|---|---|
| [`vision.md`](vision.md) | Goal, data routes, LinkedIn terms, grey-zone tools, UI concept, ruleset, owner decisions |
| [`plan.md`](plan.md) | Living document: phases, status table, resume steps |
| [`AGENTS.md`](AGENTS.md) | Hard limits (never send, no heavy traffic) and build rules for agents |
| [`research/`](research/) | Dossier on LinkedIn automation and the crackdown 2025–2026 |
| [`carousel/`](carousel/) | Two LinkedIn carousels (PDF) built from that dossier |

## Setup

1. Install [uv](https://docs.astral.sh/uv/) and Python 3.14.
2. Run the pipeline once. It creates `.venv/` and installs the project with its dev tools:

   ```bash
   ./localPipeline.sh
   ```

3. Run the command line tool:

   ```bash
   .venv/bin/reply-desk --version
   ```

## Test and pipeline

`./localPipeline.sh` is the only quality gate. CI ([`linkedin-reply-desk.yml`](../.github/workflows/linkedin-reply-desk.yml))
runs the same script.

| Stage | Tool | Fails when |
|---|---|---|
| install | `uv` | dependencies do not resolve |
| license headers | `grep` | a `.py` or `.sh` file has no `SPDX-License-Identifier: GPL-3.0-or-later` |
| ruff lint | `ruff check` | a lint rule fails |
| ruff format | `ruff format --check` | a file is not formatted |
| mypy strict | `mypy --strict` | a type error exists |
| pytest coverage | `pytest-cov` | a test fails or branch coverage < 95% |
| build | `python -m build` | sdist or wheel do not build |
| wheel smoke | clean venv | the installed wheel cannot run `reply-desk --version` |

`tests/test_guard.py` enforces the hard limits: it fails if the code contains a click, a typed input, a
navigation, the `li_at` cookie, a Voyager call or a write request to linkedin.com.

No test contacts LinkedIn. Tests use fixtures and fakes only.

## Scripts

| Script | Purpose |
|---|---|
| [`localPipeline.sh`](localPipeline.sh) | Full quality gate (see above). Exit 0 = green. |
| [`scripts/build_carousel.sh`](scripts/build_carousel.sh) | Renders `carousel/*.html` to 1080×1350 PDFs and checks page size, page count and fonts. |

## Docker

Not planned yet (owner decision, 2026-10-27).
