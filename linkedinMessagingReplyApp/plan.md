# Plan: LinkedIn Reply Assistant

Living document for the build. The goal is in `VISION.md`. The rules are in `AGENTS.md`.

## Verdict so far

The product is built and works end to end (v0.6.0): capture → OCR → classification → Ollama draft →
verified insertion, with Docker on GHCR, pipeline and CI green. All gates G0–G6 are implemented.
What remains are owner live checks L1–L5 (portal dialogs, real browser, real LinkedIn), see "Resume here".

## Review of VISION.md (2026-10-28)

| # | Finding | Action |
|---|---|---|
| V1 | Overlap with `../linkedinMessagingAutomation/` (reply desk): same goal, other read route (CDP/DMA vs. pixels). | Keep both. Separate code (D10). Same safety rules. |
| V2 | §14 insertion writes into linkedin.com. The sibling rules forbid "type on linkedin.com". | Bend B2 with a fence and a guard test. Copy Draft stays. |
| V3 | §13.1 says "40 GB VRAM node". The box has ~35.5 GB usable. | Use the measured value. No effect on the design. |
| V4 | §5 says Python 3.12+. The owner standard is 3.14. | Use 3.14 (installed: 3.14.7). |
| V5 | Tesseract has no English data here (`afr osd` only). §9.2 needs it. | User-level `eng.traineddata` via `scripts/fetch_tessdata.sh`, no root. Docker uses the distro package. |
| V6 | §14.4 Native Messaging starts a new host process per connection. It cannot reach the running app alone. | Native host = small relay to a Unix socket of the app (`$XDG_RUNTIME_DIR`, mode 0600). File permissions are the authentication. |
| V7 | §28 lists open user inputs. The owner asked me to decide. | Decided in D1–D9 below. All are config values, the owner can change them. |
| V8 | Docker for a Wayland desktop app is unusual. | The image runs the full app; the GUI needs a Wayland socket pass-through. The image smoke runs `lra selftest` (OCR + pipeline + fake backend) headless. |

## Gate 0 facts (measured 2026-10-28)

| Item | Value |
|---|---|
| Session | `wayland`, KDE Plasma, KWin 6.7.4 |
| ScreenCast portal | present, version 5 (restore tokens supported) |
| GlobalShortcuts portal | present, version 2 |
| PipeWire | 1.6.8, GStreamer `pipewiresrc` present, PyGObject (system) works |
| Tesseract | 5.5.3, languages `afr osd` (no `eng`, see V5) |
| Browsers | Chromium, Firefox. No Google Chrome. |
| Network Ollama | `http://192.168.100.67:11434`, 0.40.11, plain HTTP. Vision models: `qwen3.6:35b-a3b-q4_K_M`, `qwen3.8:27b-q4_K_M`, `gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic` |
| Local Ollama | `http://127.0.0.1:11434`, 0.40.4, running |

## Decisions (made by the agent, owner may change; 2026-10-28)

| ID | Question (`VISION.md` §28) | Decision |
|---|---|---|
| D1 | Unsolicited-decline prompt | Own default `config/prompts/sales_decline.md`. The owner can replace it with the GPT text. |
| D2 | Language policy | Mirror the sender language. English and German are supported. Other languages → manual review. |
| D3 | Profile snippets | `user_profile.yaml` with an explicit list of allowed facts. The prompt may use only those. |
| D4 | Reply length | Per category in `reply_rules.yaml`. Default short (≤ 60 words). |
| D5 | First browser | Chromium (Manifest V3). Playwright tests it. The same code is written to run in Firefox later. |
| D6 | Network endpoint | `http://192.168.100.67:11434`, scheme shown in the UI (§13.6). |
| D7 | Local Ollama policy | Use it only if it already runs. The app does not start it. |
| D8 | Reply model | `qwen3.6:35b-a3b-q4_K_M` (owner benchmark winner family), fallback list in `backends.yaml`. |
| D9 | Extractor | **OCR default** (benchmark 2026-10-28, table under "Results"): OCR 0.99–1.00 similarity in 0.2–0.4 s; vision (`qwen3-vl:4b`, local) 1.00 in 23–32 s with 1 of 5 empty answers. Vision stays as the `hybrid` fallback. |
| D10 | Reuse sibling code? | No. The sibling has no UI and a different data model. Copy ideas (ruleset, guard test), not modules. |
| D11 | Transport | Native Messaging relay → Unix socket (V6). No localhost TCP port. |
| D12 | Docker | Full app image on `python:3.14-slim` + Tesseract + GStreamer. Published to GHCR by a separate workflow. |

## Gates (from `VISION.md` §24) with steps

| Gate | Content | Exit check | Estimate |
|---|---|---|---|
| G0 | Skeleton, `pyproject.toml`, `localPipeline.sh`, CI, GPLv3, README; config loader; preflight service (session, portals, PipeWire, Ollama) + `lra preflight` | Pipeline green; `lra preflight` prints the facts above | 2 h |
| G1 | Frame + ROI model, file/test-window source, portal ScreenCast client (restore token rotation), GStreamer latest-frame grabber, capture test window, PySide6 main window with preview + ROI editor | Capture of the test window shows the right image; tests with a fake portal on a private D-Bus and `videotestsrc` | 4 h |
| G2 | GlobalShortcuts portal client, guardrails, Configure Hotkey UI, one `CaptureAndDraft` command, supersession by sequence ID | Hotkey signal and button run the same command; stale results are dropped (tests) | 2 h |
| G3 | Extractor interface, Tesseract OCR (TSV + confidence), quality check, vision extractor, OCR fixtures, editable text, benchmark | Fixtures pass with tolerant compare; benchmark recorded | 3 h |
| G4 | Ollama client, backend manager (priority, health cache, fallback, recovery), classifier (rules + model), reply policies, prompts with injection fences, generator (JSON contract), diagnostics in UI | Fixture tests per category + injection fixtures with fake LLM; one live check | 4 h |
| G5 | MV3 extension (content script, background, native port), native host relay, bridge server in app, insertion with read-back, conversation fingerprint, Copy Draft fallback, guard test | Playwright e2e on a routed fake LinkedIn page: insert works, wrong conversation is blocked, no Send | 4 h |
| G6 | Error texts §21, cancel, stale drafts, settings persistence, log redaction, debug captures, shortcuts page, packaging, Docker + GHCR workflow, README + screenshot, review, final check | All 30 acceptance criteria checked in the table below | 4 h |

## Owner requests during the build (2026-10-28)

| Request | Plan | State |
|---|---|---|
| Review and fix all findings | `review_20261028.md`, 5 findings | done, v0.5.3 |
| README: say what the project is; screenshot of the current state | "What is this project?" section; `docs/screenshot.png` and `docs/about.png` rendered on the live KDE Wayland session | done, v0.6.0 |
| About dialog (Help → About): author, mail, GPLv3, own risk, thought prototype, all dependencies with versions | `ui/about.py`; versions read at runtime (Python, Qt, PySide6, GStreamer, Tesseract, every declared Python requirement) | done, v0.6.0 |
| `/githubAbout`, final check against `VISION.md` | proposal only; tracker filled | done |
| Fix the failing GitHub Action | Pages build broke on Liquid syntax in `review_20261028.md`; reword, guard every `.md` | done, v0.6.1 |
| README: "How it works" as a Mermaid workflow chart, how content is grabbed and replies are prepared | Mermaid flowchart + 5 Ollama steps | done, v0.6.2 |
| `/updateDependencies` for the current state | check every pin against upstream, update, pipeline, commit | open |
| No open issues: pipeline, CI, Docker, Pages green, tree clean | final check | open |

## Acceptance criteria tracker (`VISION.md` §25)

All 29 code criteria are implemented and tested. The live checks L1–L5 need the owner at the desktop
(portal dialogs, a real LinkedIn tab); the procedure is under "Resume here".

| # | Criterion (short) | Gate | Evidence | State |
|---|---|---|---|---|
| 1 | Runs as normal user | G0 | No root anywhere; `scripts/install.sh` is user level; Docker runs as uid 1000 | done |
| 2 | Select window via portal | G1 | `portal/screencast.py`; `tests/integration/test_screencast.py` (fake portal, private D-Bus); live preflight: ScreenCast v5 | done (fake portal); **live pick: owner check L1** |
| 3 | Capture current frame | G1 | `capture/pipewire.py` latest-frame grabber, tested with GStreamer sources; `lra selftest` | done; **live: L1** |
| 4 | Persist conversation ROI | G1 | `state/settings.py`, ROI editor; `test_roi_and_debug_data`, `test_roi_dialog_drag` | done |
| 5 | Capture & Draft button always works | G2 | `test_window_full_flow`; `DisabledShortcuts` path | done |
| 6 | Approved global hotkey triggers same action | G2 | `test_hotkey_runs_same_command`, `test_global_shortcuts.py`, rebind on start (review #1) | done (fake portal); **live: L2** |
| 7 | Never overwrites an OS shortcut | G2 | App only proposes via portal; guardrails; no config writes (`shortcuts/`) | done |
| 8 | Hotkey failure shown, app works | G2 | `test_portal_missing`, `test_disabled_service`, hotkey chip | done |
| 9 | Captured image visible | G1 | Preview pane; screenshot `docs/screenshot.png` | done |
| 10 | Extracted text visible + editable | G3 | Message pane; `test_window_full_flow` | done |
| 11 | Visible category | G4 | Draft pane label; `test_window_full_flow` | done |
| 12 | Category override | G4 | Category combo; `test_regenerate_with_override_and_errors` | done |
| 13 | Network Ollama first | G4 | `backends.yaml` priority; `test_network_first_with_installed_model` | done (fakes); **live on box: L4** (box busy all day) |
| 14 | Local fallback | G4 | `test_fallback_to_local_when_network_down`; live 14/14 on local `qwen3.5:4b` | done |
| 15 | Backend + model shown | G4 | AI chip + backend info with fallback reason | done |
| 16 | Reply editable | G4 | Draft editor; `test_editing_marks_stale_and_edited` | done |
| 17 | Regenerate after edits | G4 | `test_regenerate_with_override_and_errors` | done |
| 18 | Superseded result cannot overwrite | G2/G4 | `test_superseded_results_are_dropped`, cancel tests | done |
| 19 | Extension + bridge for first browser | G5 | MV3 extension + `lra-native-host`; e2e 8/8 in Chromium | done; **live install: L3** |
| 20 | Insert into composer | G5 | e2e `test_insert_into_composer_without_sending` | done (fake page); **live: L3** |
| 21 | Insertion verified | G5 | Read-back in content script and `Inserter`; `NOT_VERIFIED` test | done |
| 22 | Never presses Send | G5 | Guard test + e2e counts send clicks, submits, key events = 0 | done |
| 23 | Blocks conversation mismatch | G5 | e2e `test_wrong_conversation_is_blocked`; token compare (review #4) | done |
| 24 | Copy fallback | G5 | Copy Draft button, `EXTENSION_DOWN` path | done |
| 25 | Fixture tests per category | G4 | 14 message fixtures, `test_reply_engine.py`, live test | done |
| 26 | Injection fixtures hold | G4 | 2 injection fixtures, fence + output guard tests; live 2/2 | done |
| 27 | No content persisted by default | G6 | Frames in memory; debug captures opt-in; `test_debug_captures_only_when_enabled` | done |
| 28 | Logs redacted | G6 | `events.py`; `test_full_run_on_fixture`, `test_event_log_redaction` | done |
| 29 | Failures readable in UI | G6 | `friendly_error`, §21 texts, chips; UI tests | done |
| 30 | Repeated success on real conversations | owner | Manual checklist §23.7 | **open: owner check L5** |

## Commit log (one row per commit, with its check)

| Version | Commit subject | Check run | Result |
|---|---|---|---|
| 0.1.0 | build(reply-assistant): add package skeleton, local pipeline and CI | `./localPipeline.sh` (9 stages) | green, coverage 100% |
| 0.1.1 | feat(reply-assistant): load and validate the YAML configuration | `./localPipeline.sh` (9 stages) | green, coverage 100% |
| 0.1.2 | feat(reply-assistant): add Ollama client and backend manager with fallback | `./localPipeline.sh` (9 stages) | green, coverage 100% |
| 0.2.0 | feat(reply-assistant): add preflight service and 'lra preflight' (gate 0) | `./localPipeline.sh` (9 stages); live: lra preflight on KDE/Wayland = 8 OK, tesseract FAIL (no eng data, V5) | green, coverage 100% |
| 0.2.1 | feat(reply-assistant): add ScreenCast portal capture with latest-frame PipeWire grabber | `./localPipeline.sh` (9 stages) | green, coverage 99% |
| 0.2.2 | feat(reply-assistant): add GlobalShortcuts portal client with trigger guardrails | `./localPipeline.sh` (9 stages) | green, coverage 99% |
| 0.2.3 | feat(reply-assistant): add OCR, vision and hybrid extractors with screenshot fixtures | `./localPipeline.sh` (9 stages); OCR on 5 fixtures: similarity 0.99-1.00, confidence 0.96 | green, coverage 99% |
| 0.2.4 | test(reply-assistant): add extractor benchmark and record the OCR default (D9) | `./localPipeline.sh` (9 stages); benchmark run, local-ollama qwen3-vl:4b | green, coverage 99% |
| 0.2.5 | feat(reply-assistant): add classifier, prompt fences and reply generator | `./localPipeline.sh` (9 stages) | green, coverage 99% |
| 0.2.6 | feat(reply-assistant): add workflow state machine and the Capture & Draft pipeline | `./localPipeline.sh` (9 stages); live: 14/14 reply fixtures on local qwen3.5:4b | green, coverage 99% |
| 0.3.0 | feat(reply-assistant): add browser extension, native host relay and verified insertion (gate 5) | `./localPipeline.sh` (10 stages); e2e: 8/8 (insert, no Send, no key events, mismatch blocked, no composer, non-LinkedIn tab, zero LinkedIn requests) | green, coverage 99% |
| 0.4.0 | feat(reply-assistant): add the PySide6 desktop UI, controller and lra commands | `./localPipeline.sh` (10 stages); lra selftest OK in a clean wheel venv; UI tests 20/20 | green, coverage 98% |
| 0.4.1 | build(reply-assistant): add a user-level install script with desktop entry | `./localPipeline.sh` (10 stages); scripts/install.sh on this machine: selftest OK, preflight 8 OK + bridge WARN | green, coverage 98% |
| 0.5.0 | build(reply-assistant): add Docker image, docker pipeline stage and GHCR publishing | `./localPipeline.sh` (11 stages); docker smoke: version, selftest --network none, UI render | green, coverage 98% |
| 0.5.1 | docs(reply-assistant): write the README with setup, usage, pipeline, Docker and a real screenshot | `./localPipeline.sh` (11 stages); docker GUI ran on the live Wayland session (demo, 60 s, no errors) | green, coverage 98% |
| 0.5.2 | fix(reply-assistant): keep prompt templates free of Liquid syntax so GitHub Pages builds again | `./localPipeline.sh` (11 stages) | green, coverage 98% |
| 0.5.3 | fix(reply-assistant): fix the five findings of the branch review | `./localPipeline.sh` (11 stages) | green, coverage 98% |
| 0.6.0 | feat(reply-assistant): add the About dialog and explain the project in the README | `./localPipeline.sh` (11 stages); screenshots rendered on the live Wayland session at v0.6.0 | green, coverage 99% |
| 0.6.1 | fix(reply-assistant): remove Liquid syntax from the review notes so GitHub Pages builds | `./localPipeline.sh` (11 stages) | green, coverage 99% |
| 0.6.2 | docs(reply-assistant): explain the workflow in the README with a Mermaid chart | `./localPipeline.sh` (11 stages) | green, coverage 98% |

## Results

### Extractor benchmark (D9), 2026-10-28

`scripts/benchmark_extractors.py --backend local-ollama`. The box (`192.168.100.67`) had another user's model loaded
(`kat-coder-v2.5`, keep-alive refreshed), so the vision run used the local GPU, per `AGENTS.md`.

| fixture | OCR similarity | OCR s | vision similarity | vision s |
|---|---|---|---|---|
| dark_normal | 0.993 | 0.2 | 1.000 | 32.4 |
| dark_small_short | 1.000 | 0.3 | 1.000 | 22.7 |
| light_hidpi_german | 1.000 | 0.3 | 1.000 | 24.9 |
| light_normal_short | 0.992 | 0.3 | 1.000 | 22.8 |
| light_zoom_multiline | 1.000 | 0.4 | error (empty answer) | – |

### Live reply check, local backend, 2026-10-28

`LIVE_OLLAMA=1 pytest tests/integration/test_live_ollama.py` with only `local-ollama` (`qwen3.5:4b`, the box was busy):
**14 of 14 fixtures passed** (category as expected, no forbidden pattern, injection fixtures declined politely).
Time per draft 3.4–10.5 s (classification by the model for the ambiguous fixtures plus generation).

## Status

| Date | Step | Result |
|---|---|---|
| 2026-10-28 | Read `VISION.md`, the sibling project, probed the machine and the box | Gate 0 facts above. Review V1–V8. |
| 2026-10-28 | Wrote `AGENTS.md` and `plan.md` | Decisions D1–D12, bends B1–B2 |
| 2026-10-28 | Gates G0–G6 built, v0.1.0 → v0.6.0 | See the commit log; CI, Docker workflow and GHCR image green |
| 2026-10-28 | Incident: prompt `system.md` broke the monorepo GitHub Pages build (Liquid double curly braces) since v0.1.1 | Fixed in v0.5.2, guard test added, Pages green again |
| 2026-10-28 | `/reviewBranch` | 5 findings, all fixed in v0.5.3 (`review_20261028.md`) |
| 2026-10-28 | `/githubAbout` | Proposal only (monorepo About covers all projects): topics `ollama`, `pyside6`, `wayland` suggested; not applied |
| 2026-10-28 | Final check against `VISION.md` §25 | 29/30 criteria done in code and tests; live checks L1–L5 wait for the owner |

## Resume here

- State: v0.6.0, all gates implemented, 289 tests, 98% branch coverage, CI + Docker workflow green.
- Check: `./localPipeline.sh` (exit 0 = green); `.venv/bin/lra preflight`; `.venv/bin/lra selftest`.
- Commit: `scripts/commit.sh patch "<subject>" "<why>"` (pipeline, plan row, commit, push).
- Owner live checks (each takes a few minutes):
  1. **L1 capture:** `.venv/bin/lra test-window` and `.venv/bin/lra gui`. Press Select Window, pick the test
     window, press Capture & Draft, Edit Region around the conversation, capture again.
  2. **L2 hotkey:** Tools → Keyboard Shortcuts… → Request from desktop, accept in the KDE dialog. Focus the
     test window, press the hotkey. Restart the app and press it again (review finding #1).
  3. **L3 extension:** `chromium://extensions` → Developer mode → Load unpacked → `extension/`. The chip
     shows "Extension: connected".
  4. **L4 network node:** when the box is free (`curl -s 192.168.100.67:11434/api/ps`), run
     `LIVE_OLLAMA=1 .venv/bin/pytest tests/integration/test_live_ollama.py -s`.
  5. **L5 LinkedIn (VISION §23.7):** in Chromium, open a real conversation, Capture & Draft, check text and
     category, edit, Insert into LinkedIn, verify the composer, do not let the app send. Repeat on several
     conversations. Record the result in the status table.
- After the round: decide GitHub topics for the monorepo (proposal in the status table, 2026-10-28).
