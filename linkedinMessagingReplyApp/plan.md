# Plan: LinkedIn Reply Assistant

Living document for the build. The goal is in `VISION.md`. The rules are in `AGENTS.md`.

## Verdict so far

`VISION.md` is buildable on this machine. Gate 0 facts are measured (table below). The plan is set.
Two sibling rules are bent, not broken (`AGENTS.md`, B1 and B2). Next step: gate 0 skeleton and pipeline.

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

## Acceptance criteria tracker (`VISION.md` §25)

| # | Criterion (short) | Gate | Evidence | State |
|---|---|---|---|---|
| 1 | Runs as normal user | G0 | | open |
| 2 | Select window via portal | G1 | | open |
| 3 | Capture current frame | G1 | | open |
| 4 | Persist conversation ROI | G1 | | open |
| 5 | Capture & Draft button always works | G2 | | open |
| 6 | Approved global hotkey triggers same action | G2 | | open |
| 7 | Never overwrites an OS shortcut | G2 | | open |
| 8 | Hotkey failure shown, app still works | G2 | | open |
| 9 | Captured image visible | G1 | | open |
| 10 | Extracted text visible + editable | G3 | | open |
| 11 | Visible category | G4 | | open |
| 12 | Category override | G4 | | open |
| 13 | Network Ollama first | G4 | | open |
| 14 | Local fallback | G4 | | open |
| 15 | Backend + model shown | G4 | | open |
| 16 | Reply editable | G4 | | open |
| 17 | Regenerate after edits | G4 | | open |
| 18 | Superseded result cannot overwrite | G2/G4 | | open |
| 19 | Extension + bridge for first browser | G5 | | open |
| 20 | Insert into composer | G5 | | open |
| 21 | Insertion verified | G5 | | open |
| 22 | Never presses Send | G5 | | open |
| 23 | Blocks conversation mismatch | G5 | | open |
| 24 | Copy fallback | G5 | | open |
| 25 | Fixture tests per category | G4 | | open |
| 26 | Injection fixtures hold | G4 | | open |
| 27 | No content persisted by default | G6 | | open |
| 28 | Logs redacted | G6 | | open |
| 29 | Failures readable in UI | G6 | | open |
| 30 | Repeated success on real conversations | owner | Manual checklist §23.7; needs the owner at LinkedIn | open |

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

## Status

| Date | Step | Result |
|---|---|---|
| 2026-10-28 | Read `VISION.md`, the sibling project, probed the machine and the box | Gate 0 facts above. Review V1–V8. |
| 2026-10-28 | Wrote `AGENTS.md` and `plan.md` | Decisions D1–D12, bends B1–B2 |

## Resume here

- State: planning done, no code yet.
- Check: `./localPipeline.sh` (exit 0 = green), `git log --oneline -- linkedinMessagingReplyApp/`.
- Next: G0 skeleton.
