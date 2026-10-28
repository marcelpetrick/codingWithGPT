# VISION.md

# LinkedIn Reply Assistant — Vision, MVP Architecture, and Verification Plan

**Status:** working design for the first implementation  
**Primary platform:** Manjaro Linux, Wayland-first  
**Primary interaction model:** human-in-the-loop  
**Primary AI backend:** Ollama, network node first, local Ollama second  
**Primary MVP objective:** prove that a global hotkey or UI button can capture the current LinkedIn browser view, extract the visible conversation, classify the message, generate a useful reply, let the user edit it, and insert the approved text into the LinkedIn composer without sending it.

---

## 1. Product Vision

Build a local desktop assistant that sits beside a normal LinkedIn browser session and removes the repetitive work of reading, categorizing, drafting, copying, and pasting replies.

The intended daily workflow is approximately 10–20 messages. The application should make each message a short human review task rather than an automation task.

The user remains in control of navigation and sending:

1. The user opens LinkedIn normally in Firefox or Chromium/Chrome.
2. The user opens the message/conversation to answer.
3. The user presses a global **Capture & Draft** hotkey or clicks **Capture & Draft** in the application.
4. The application captures the configured browser window.
5. It extracts the visible conversation text from the capture.
6. It determines the message type.
7. It generates a warm, context-aware draft using the configured reply rules.
8. The application shows the classification, extracted text, and generated reply.
9. The user can edit or regenerate the reply.
10. The user presses **Insert into LinkedIn**.
11. The application inserts the final draft into LinkedIn's reply composer.
12. The user reviews it in LinkedIn and manually presses **Send**.

The application must never press Send on the user's behalf in the MVP.

---

## 2. Product Principles

### 2.1 Human approval is mandatory

The application may:

- capture the chosen browser window,
- extract visible conversation content,
- classify messages,
- generate replies,
- let the user edit replies,
- insert an approved reply into the active LinkedIn composer.

It must not:

- automatically send messages,
- autonomously work through the LinkedIn inbox,
- autonomously open profiles or conversations,
- attempt CAPTCHA bypass,
- spoof browser fingerprints,
- simulate human behavior for the purpose of avoiding platform detection,
- launch a hidden or separately automated browser session.

### 2.2 Use the user's real browser session

The user should remain logged into LinkedIn in their normal browser profile. The system should not need LinkedIn credentials and should not store LinkedIn cookies.

### 2.3 No root requirement

The desktop application must run as the normal user. It must not depend on `sudo`, root-owned keyboard hooks, or bypassing Wayland's security model.

### 2.4 Local AI first

Backend priority is initially:

1. configured network Ollama node,
2. local Ollama instance,
3. optional cloud providers later and only when explicitly enabled.

The UI must show exactly which backend and model produced each draft.

### 2.5 Fail visibly, not silently

If capture, OCR, model selection, generation, or insertion fails, the application should explain what failed and preserve the current user-editable state where possible.

---

## 3. MVP Strategy: Screen-Capture First

The first MVP is deliberately **screen-capture first**.

Although structured DOM extraction through a browser extension can later become the preferred extraction method, the first engineering goal is to prove the workflow the user explicitly wants:

> hotkey/button → capture browser window → extract message → classify → draft reply → review/edit → insert into LinkedIn

This is useful for two reasons:

- it validates the Wayland/PipeWire workflow early rather than leaving it as an untested fallback,
- it creates a browser-independent capture path that can continue working even if LinkedIn changes its DOM.

The browser extension is still part of the MVP for **inserting the approved reply**, because inserting directly into the LinkedIn composer is much more reliable through the page DOM than through synthetic mouse/keyboard automation.

### 3.1 MVP components

The first complete MVP consists of:

- PySide6 desktop application,
- Wayland ScreenCast portal integration,
- PipeWire frame capture,
- global hotkey registration where supported,
- visible capture button as a guaranteed fallback,
- configurable conversation-region crop,
- OCR and/or local vision extraction,
- reply classification,
- reply generation through Ollama,
- editable draft,
- one-browser extension for insertion,
- visible backend/model/status diagnostics,
- automated tests plus a small manual acceptance checklist.

### 3.2 Explicitly not required for MVP

The first MVP does not require:

- two browsers at once,
- cloud AI,
- autonomous navigation,
- automatic sending,
- background inbox monitoring,
- permanent message history,
- advanced CRM behavior,
- browser DOM extraction for the incoming message,
- perfect OCR for arbitrary sites.

---

## 4. High-Level Architecture

```text
                    ┌─────────────────────────────┐
                    │ Normal LinkedIn browser     │
                    │ Firefox or Chromium/Chrome  │
                    └──────────────┬──────────────┘
                                   │
                    Wayland ScreenCast / PipeWire
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────┐
│ PySide6 Desktop Application                              │
│                                                          │
│  Capture Service                                         │
│      ↓                                                   │
│  Region/Crop Processor                                   │
│      ↓                                                   │
│  OCR / Vision Extractor                                  │
│      ↓                                                   │
│  Message Classifier                                      │
│      ↓                                                   │
│  Reply Policy + Prompt Builder                           │
│      ↓                                                   │
│  Backend Manager → network Ollama → local Ollama         │
│      ↓                                                   │
│  Editable Draft                                          │
│      ↓                                                   │
│  Insert Request                                          │
└──────────────────────────────┬───────────────────────────┘
                               │
                    local authenticated bridge
                               │
                               ▼
                  ┌─────────────────────────┐
                  │ Browser WebExtension    │
                  │ inserts draft only      │
                  └─────────────────────────┘
```

The internal modules must have clean interfaces so capture, extraction, AI provider, browser transport, and UI can be tested separately.

---

## 5. Target Environment and Preflight

Initial target:

- Manjaro Linux,
- Wayland session expected,
- KDE Plasma, GNOME, or another portal-capable desktop must be detected rather than assumed,
- Python 3.12+ where practical,
- PySide6,
- PipeWire,
- `xdg-desktop-portal` and a suitable desktop portal backend,
- Firefox or Chromium/Chrome,
- Ollama-compatible API.

At startup, a **preflight service** should detect and report:

- `XDG_SESSION_TYPE`,
- `XDG_CURRENT_DESKTOP`,
- availability of the ScreenCast portal,
- availability of the GlobalShortcuts portal,
- PipeWire availability,
- browser-extension bridge status,
- network Ollama health,
- local Ollama health,
- available configured models.

This information should be visible under a compact **System Status** panel instead of being buried in logs.

The application must never assume that a feature exists merely because the OS is Manjaro.

---

## 6. Wayland Screen Capture Design

### 6.1 Why ScreenCast rather than arbitrary screenshot APIs

On Wayland, an ordinary application is not allowed to scrape arbitrary windows the way an X11 application could. The correct generic path is the desktop portal.

The MVP should use:

> XDG Desktop Portal ScreenCast → user-approved browser window → PipeWire stream

The user selects the browser window during setup. After permission is granted, the application receives video frames through PipeWire and can take a still frame whenever the capture action is triggered.

### 6.2 First-run source selection

On first use:

1. User presses **Select Browser Window**.
2. The portal's native source picker opens.
3. User chooses the LinkedIn browser window.
4. The application starts the PipeWire stream.
5. A test frame appears in the UI.
6. If the portal grants persistence, the application stores the returned restore token locally for the next session. Restore tokens must be treated as **single-use**: whenever a restored ScreenCast session starts successfully, replace the stored token with the newly returned token.

If the stored source cannot be restored later, the application asks the user to select the browser window again. The implementation must tolerate desktop/portal changes that invalidate persisted source metadata.

### 6.3 Frame handling

The capture service should maintain a low-overhead stream and retain only the latest usable frame. With recent ScreenCast portal versions, prefer the PipeWire stream's stable `pipewire-serial`/target-object metadata when available rather than assuming a PipeWire node ID is permanently unique.

For the MVP:

- no video recording,
- no long-term frame buffer,
- no screenshot file written to disk by default,
- capture is an in-memory still image derived from the latest PipeWire frame.

A developer/debug option may explicitly save captures for troubleshooting, but it should be off by default.

### 6.4 Conversation-region selection

OCR over the entire browser window will include navigation, sidebars, names, advertisements, and unrelated messages. The MVP therefore needs a simple **region of interest (ROI)** workflow.

After the first test capture:

1. show the captured browser image,
2. let the user drag a rectangle around the main LinkedIn conversation area,
3. store the rectangle as normalized coordinates relative to the captured window,
4. apply that region automatically to future captures.

The UI should have:

- **Edit Capture Region**,
- **Reset Capture Region**,
- a preview overlay.

Normalized coordinates make the crop reasonably tolerant to window resizing.

Later versions can automatically locate the conversation panel, but the MVP should prefer a deterministic user-selected crop.

### 6.5 Capture verification

Every capture should have metadata:

- timestamp,
- source name if available,
- image dimensions,
- crop region,
- extraction mode,
- capture sequence ID.

The UI should show a small screenshot preview so the user can immediately see whether the correct content was captured.

---

## 7. Global Hotkey Design on Wayland

### 7.1 Requirement

The user should be able to trigger **Capture & Draft** without switching focus to the application.

The hotkey must:

- be global where the desktop supports it,
- not silently overwrite an existing operating-system shortcut,
- not require root,
- not depend on X11-only keyboard grabbing,
- remain optional because the UI button must always work.

### 7.2 Preferred implementation

Use the XDG Desktop Portal **GlobalShortcuts** interface when available.

The application should not install a global shortcut automatically on first launch. Instead:

1. show **Configure Global Hotkey**,
2. request a shortcut session from the portal,
3. propose a preferred accelerator only as a suggestion,
4. let the desktop/compositor approve, reject, or change it,
5. display the actual bound shortcut returned by the desktop,
6. store the logical shortcut ID, not merely assume a key sequence succeeded,
7. if the user wants to change shortcuts later, use the portal's shortcut-configuration flow or create a new shortcut session rather than trying to bind a second time to the same session.

This is important because the compositor is the authority for global shortcuts under Wayland.

### 7.3 Conflict handling

A generic Wayland application cannot reliably enumerate every shortcut already owned by the desktop, other applications, window manager, or compositor. Therefore the application must **not claim that it can pre-check every system conflict itself**.

The safe policy is:

- never force a binding,
- treat the shortcut list returned by the portal as authoritative,
- never modify OS shortcut configuration directly,
- let the portal/compositor mediate the registration,
- show the binding that was actually accepted,
- if registration fails or no binding is returned, leave global capture disabled and keep the UI button available.

Before requesting a global shortcut, the application can still reject obviously unsuitable choices such as:

- bare `Super`, `Alt`, `Ctrl`, or `Shift`,
- `Alt+F4`,
- terminal/TTY switching combinations,
- combinations already used by the application's own local shortcuts.

This is a guardrail, not a complete system-wide conflict detector.

### 7.4 Desktop-specific fallback

If the GlobalShortcuts portal is not available:

- keep **Capture & Draft** fully usable from the UI,
- optionally support a desktop-specific adapter later, such as a KDE global-shortcut integration,
- do not fall back to privileged input hooks.

The first MVP must succeed without global shortcuts; global hotkey support is an enhancement to the same capture action, not a separate processing path.

### 7.5 MVP shortcut policy

Only one global shortcut is required initially:

> **Capture & Draft**

**Insert into LinkedIn** should remain an explicit UI button for the MVP. This reduces the chance of accidentally inserting a draft into the wrong conversation.

---

## 8. Capture-to-Draft Pipeline

The hotkey and the UI button must call the **same application command**.

```text
CaptureAndDraft
    ↓
validate capture source
    ↓
grab current frame
    ↓
apply ROI crop
    ↓
extract visible conversation text
    ↓
validate extraction
    ↓
classify message
    ↓
build reply prompt/rules
    ↓
select healthy Ollama backend/model
    ↓
generate draft
    ↓
show classification + draft + diagnostics
```

No capture logic should be duplicated between hotkey and button implementations.

### 8.1 Re-entrancy

If the user presses the hotkey twice quickly:

- the second request should cancel or supersede the first request,
- an old result must never overwrite a newer result,
- UI state must show which capture sequence is active.

### 8.2 Cancellation

The UI should have **Cancel** while extraction/generation is in progress.

Cancellation should prevent a late backend response from replacing a newer draft.

---

## 9. Text Extraction from the Screenshot

### 9.1 MVP extraction interface

Define a common extractor interface:

```text
extract(image, context) -> ExtractionResult
```

`ExtractionResult` should contain:

- raw text,
- structured message candidates where possible,
- confidence/quality indication,
- language guess,
- warnings,
- extractor name.

### 9.2 OCR mode

A basic local OCR implementation should be available in the MVP.

Candidates include:

- Tesseract,
- PaddleOCR,
- EasyOCR.

The implementation should be selected after a quick quality test on actual LinkedIn screenshots rather than by assumption.

The OCR pipeline may perform:

- image scaling,
- contrast normalization,
- optional grayscale conversion,
- line grouping,
- whitespace cleanup.

Do not over-process the image if it reduces OCR quality.

### 9.3 Vision-model mode

If the selected Ollama node has a suitable vision-capable model, a screenshot-to-structured-text extractor may outperform classical OCR because it can understand message layout and distinguish sender/recipient bubbles.

The architecture should therefore support:

- `OcrExtractor`,
- `VisionExtractor`,
- optional `HybridExtractor`.

The application can probe installed Ollama models and mark models known/configured as vision-capable.

For the MVP, OCR is the guaranteed baseline. Vision extraction is preferred only if it can be verified on the actual node.

### 9.4 Human-verifiable extraction

The recognized message text must be visible in the application.

The user should be able to correct OCR text manually before regenerating a reply.

This is important because a fluent LLM can hide OCR mistakes by producing a plausible response to incorrectly recognized text.

### 9.5 Extraction confidence

When extraction quality is obviously poor—for example almost no text, excessive garbage characters, or very low OCR confidence—the application should:

- show **Extraction needs review**,
- keep the screenshot preview visible,
- avoid presenting the draft as trustworthy,
- allow the user to edit the extracted text and regenerate.

---

## 10. Message Classification

Before drafting, the application determines the message category.

Initial categories:

- `friendly_connection`,
- `congratulations_or_support`,
- `generic_networking`,
- `substantive_professional`,
- `sales_outreach`,
- `lead_generation`,
- `meeting_request`,
- `recruiting`,
- `event_invitation`,
- `partnership_request`,
- `unknown_manual_review`.

Classification should return structured output, for example:

```json
{
  "category": "sales_outreach",
  "confidence": 0.92,
  "reason_short": "Unsolicited request for a sales call",
  "reply_policy": "sales_decline"
}
```

The classification label should be shown in the UI.

The user should be able to override it before regenerating if the model picked the wrong class.

### 10.1 Deterministic rules plus model classification

The system should support both:

- simple deterministic rules for obvious cases,
- model classification for ambiguous cases.

The rules should not become a huge hard-coded if/else tree. They should live in configuration and be testable.

---

## 11. Reply Policy and Prompt Design

The user will provide the existing unsolicited-decline prompt. That prompt is a first-class project input and should live in versioned configuration, not inside Python source code.

Suggested configuration structure:

```text
config/
  reply_rules.yaml
  user_profile.yaml
  prompts/
    system.md
    classifier.md
    friendly_connection.md
    sales_decline.md
    meeting_request.md
    recruiting.md
```

### 11.1 Global reply requirements

Generated replies should be:

- warm,
- professional,
- concise unless the incoming message requires more detail,
- customized to the actual message,
- free of unnecessary corporate filler,
- consistent with the user's personal style rules,
- not falsely claiming facts about the user.

### 11.2 Sales/lead-generation decline behavior

The exact wording will come from the user's prompt, but the engine should support rules such as:

- recognize unsolicited selling or meeting requests,
- respond politely,
- avoid hostile or robotic wording,
- do not say "I am not the right person" unless the user's policy specifically calls for it,
- acknowledge the sender's specific offer where useful,
- decline clearly enough that the reply does not invite an unnecessary follow-up meeting.

### 11.3 Friendly/networking replies

For supportive messages or people who simply want to connect:

- thank them naturally,
- respond to something specific where possible,
- optionally reference the user's current professional interests such as agentic AI when relevant and allowed by the user policy,
- avoid turning every short message into a long self-introduction.

### 11.4 Output contract

Generation should request structured output internally, for example:

```json
{
  "reply": "...",
  "category": "friendly_connection",
  "language": "en",
  "needs_manual_review": false
}
```

Only the reply body should be inserted into LinkedIn.

---

## 12. Prompt-Injection Resistance

LinkedIn messages are untrusted data.

A sender could include text such as "ignore all previous instructions" or attempt to make the model reveal system information.

The application must ensure that:

- conversation text is delimited as data,
- sender content never becomes application policy,
- sender content cannot alter backend configuration,
- sender content cannot cause files or secrets to be read,
- sender content cannot trigger insertion or sending,
- sender content cannot override the user's reply rules.

Tests must include adversarial fixtures.

---

## 13. Ollama Backend Architecture

### 13.1 Priority order

Initial backend priority:

1. configured 40 GB VRAM network Ollama node,
2. local Ollama,
3. optional remote/cloud providers later.

The actual model should not be hard-coded in the architecture.

### 13.2 Endpoint probing

At startup and when needed, the backend manager should probe:

- endpoint reachability,
- Ollama version,
- installed model list,
- selected model availability.

Health status should be cached for a short configurable period so the application does not repeatedly block on the same dead endpoint.

If the preferred network node is unavailable:

1. record the reason,
2. immediately try local Ollama,
3. show the fallback in the UI.

The network node should become eligible again later without restarting the application.

### 13.3 Model discovery

The UI should be able to show models reported by the Ollama endpoint.

The configuration should support a preference list, for example conceptually:

```yaml
backends:
  - name: network-ollama
    priority: 10
    model_preferences:
      reply:
        - <preferred-general-model>
        - <secondary-model>
      vision:
        - <preferred-vision-model>
  - name: local-ollama
    priority: 20
```

Model names will be filled in after probing the actual node.

### 13.4 Model evaluation

For reply generation, evaluate models on:

- instruction following,
- tone,
- brevity control,
- classification accuracy,
- hallucination rate,
- multilingual quality if needed,
- latency.

A coding benchmark is not a meaningful primary criterion for this use case.

### 13.5 Backend status in UI

For every draft, display:

- backend name,
- endpoint label,
- model,
- generation duration,
- fallback reason if applicable.

Example:

```text
AI: network-ollama / <model>
Generation: 1.6 s
Fallback: none
```

or:

```text
AI: local-ollama / <model>
Network node: timeout after 700 ms
Fallback: local
```

### 13.6 Network privacy

If the network Ollama endpoint uses plain HTTP, message data travels unencrypted on the local network.

The UI/configuration should make the endpoint scheme visible and allow HTTPS when available. This is not necessarily a blocker for a trusted private LAN, but it should not be hidden.

---

## 14. Browser Extension for Reply Insertion

The MVP should use a small WebExtension for one browser.

Its primary MVP responsibility is intentionally narrow:

> receive an approved draft from the desktop app and insert it into the currently active LinkedIn message composer.

### 14.1 Why not synthetic keyboard/mouse input

Using the extension avoids dependence on:

- window coordinates,
- fake mouse clicks,
- keyboard injection,
- clipboard timing,
- accessibility permissions.

It also works with the user's normal logged-in browser session.

### 14.1a No OS-level input injection (decision, 2026-10-28)

The application never produces input that looks like it comes from the user. This excludes:

- `ydotool`, `uinput`, `evdev` writes, `xdotool`, `wtype`, `libei`,
- the RemoteDesktop portal (it can inject keys and pointer events),
- Python input libraries such as `pynput` and `pyautogui`,
- synthetic `paste` or key events in the page (`ClipboardEvent`, `KeyboardEvent`).

Reasons:

1. Input that pretends to be human hides automation. That breaks hard limit 4 in `AGENTS.md`.
2. Events made in the page are marked `isTrusted: false`. A faked paste is easier to detect than an honest insert.
3. OS-level injection needs `uinput` access or a daemon with root rights. It can type into any window, also the wrong one.
4. The only real paste is the user's own `Ctrl+V`. It costs one key press.

A guard test (`tests/unit/test_guard.py`) fails the build on these names.

### 14.1b Manual mode: the extension is optional

The whole workflow works without the extension: capture, OCR, classification, draft, edit.
The last step is the user's own action:

1. Press **Copy Draft** (`Ctrl+D`).
2. Click into the LinkedIn composer.
3. Press `Ctrl+V`, read the text and press **Send**.

In manual mode the browser has no extension, so LinkedIn sees only a normal paste by a person.
The user then checks the thread name, because the extension's conversation check is not available.

### 14.2 Insertion behavior

When the user presses **Insert into LinkedIn**:

1. desktop app sends an insertion request to the extension,
2. extension verifies that the active tab is a LinkedIn messaging page,
3. extension locates the reply composer,
4. extension focuses the composer,
5. extension inserts the text using a contenteditable-compatible method,
6. extension dispatches the events needed for LinkedIn's UI framework to recognize the new content,
7. extension reads back the composer content,
8. extension returns success only if the expected text is present,
9. extension does **not** click Send.

### 14.3 Conversation safety

The MVP must avoid inserting a draft into the wrong conversation.

At capture time, the application should derive a **conversation fingerprint** from whatever information is available, for example:

- OCR-recognized participant name,
- visible thread title/name,
- optional extension-provided active conversation identifier,
- active URL metadata if stable.

Before insertion, the extension should report the active conversation identity if it can obtain one.

If the current conversation cannot be reasonably matched to the draft:

- block insertion,
- show **Conversation changed — recapture required**.

If a robust identity cannot be implemented in the first spike, insertion should require an explicit confirmation showing the captured participant name before it proceeds.

### 14.4 Transport

Preferred production transport:

> WebExtension ↔ Native Messaging ↔ desktop application

A localhost bridge may be used in the earliest prototype if it accelerates development, but if so it must:

- bind to `127.0.0.1` only,
- use a random per-session authentication token,
- reject arbitrary origins/clients,
- be abstracted so it can be replaced by Native Messaging later.

---

## 15. UI/UX Specification

The interface should look like a focused desktop tool, not a developer test harness.

### 15.1 Main window layout

Suggested three-area layout:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ LinkedIn Reply Assistant                                                │
│ Capture: Ready   Hotkey: Ctrl+...   AI: network-ollama / model   ● OK   │
├──────────────────────────┬──────────────────────────┬───────────────────┤
│ CAPTURE                  │ MESSAGE                  │ DRAFT             │
│                          │                          │                   │
│ [screenshot preview]     │ Sender: ...              │ [editable reply]  │
│                          │                          │                   │
│ ROI overlay / status     │ Extracted text:          │ Category: ...     │
│                          │ [editable text]          │                   │
│ [Select Window]          │                          │ [Regenerate]      │
│ [Edit Region]            │ Extraction: OCR/Vision   │                   │
├──────────────────────────┴──────────────────────────┴───────────────────┤
│ [Capture & Draft] [Cancel]                 [Insert into LinkedIn]      │
│ Status: Ready / Capturing / OCR / Generating / Draft ready / Error     │
└─────────────────────────────────────────────────────────────────────────┘
```

The actual layout may use two columns on smaller screens, but all major state should be visible without navigating through modal dialogs.

### 15.2 Key UI elements

**Top status strip**

- capture source,
- global hotkey status,
- backend/model,
- browser-extension status,
- compact health indicator.

**Capture pane**

- last screenshot preview,
- crop overlay,
- capture source selector,
- region editor.

**Message pane**

- extracted sender if available,
- editable extracted text,
- language,
- message category,
- extraction confidence/warnings.

**Draft pane**

- large editable reply field,
- category selector/override,
- regenerate button,
- length/tone controls later if useful.

**Primary action bar**

- **Capture & Draft**,
- **Cancel** when active,
- **Insert into LinkedIn** only when draft state is valid.

### 15.3 Visual behavior

The UI should make state obvious without excessive popups.

Examples:

- green/neutral status for healthy backend,
- warning chip for OCR uncertainty,
- visible badge when local Ollama was used as fallback,
- disabled insertion button when the draft is stale,
- small spinner/progress label during generation.

### 15.4 Window behavior

The application should not require always-on-top mode, but it can offer it as an option.

A useful optional mode is:

- keep app on a second monitor or beside the browser,
- hotkey triggers work while browser stays focused,
- when draft finishes, show a desktop notification or status indication,
- avoid aggressive focus stealing.

---

## 16. Application State Model

State must be explicit.

Suggested primary states:

- `NO_SOURCE`,
- `SOURCE_READY`,
- `CAPTURING`,
- `EXTRACTING`,
- `EXTRACTION_REVIEW`,
- `GENERATING`,
- `DRAFT_READY`,
- `DRAFT_EDITED`,
- `DRAFT_STALE`,
- `INSERTING`,
- `INSERTED`,
- `ERROR`.

Key rules:

- **Capture & Draft** requires a capture source.
- Generation requires usable extracted text.
- The user may edit extracted text and regenerate.
- The user may edit a generated draft.
- A new capture invalidates the previous draft.
- A conversation change should mark the old draft stale.
- A cancelled or superseded request cannot update the current draft.
- **Insert into LinkedIn** is enabled only for a non-stale draft.
- **Inserted** does not mean **Sent**.

---

## 17. Global and Local Keyboard Shortcuts

Keep global and in-application shortcuts separate.

### 17.1 Global

MVP:

- configurable **Capture & Draft** only.

### 17.2 In-application

Possible defaults, subject to platform conventions:

- `Ctrl+R` or another non-conflicting local key for regenerate,
- `Esc` for cancel,
- a local shortcut for focusing the draft editor.

Do not use a shortcut for insertion until the user explicitly enables one in a later version.

The app should have a **Keyboard Shortcuts** settings page showing:

- requested global shortcut,
- accepted global shortcut,
- status,
- local shortcuts.

---

## 18. Configuration

Configuration should be human-readable and versionable.

Suggested layout:

```text
config/
  app.yaml
  backends.yaml
  reply_rules.yaml
  user_profile.yaml
  prompts/
    system.md
    classifier.md
    friendly_connection.md
    sales_decline.md
    meeting_request.md
```

### 18.1 `app.yaml`

Contains:

- UI preferences,
- capture region metadata,
- global-hotkey logical configuration,
- extraction preferences,
- default language behavior.

### 18.2 `backends.yaml`

Contains:

- Ollama endpoints,
- priorities,
- timeouts,
- preferred models,
- health-cache interval.

Secrets should not be stored in plaintext configuration if authentication is later added.

### 18.3 `reply_rules.yaml`

Contains:

- category-to-policy mapping,
- style rules,
- default reply lengths,
- rules controlling when particular personal/professional information may be mentioned.

---

## 19. Language Behavior

Recommended default design:

- detect the dominant language of the visible incoming message,
- display the detected language,
- reply in that language unless a user setting overrides it.

The exact policy remains a user decision.

For the initial English-focused prototype, language detection can still be implemented but unsupported languages can be marked for manual review until prompt quality is verified.

---

## 20. Data Retention and Privacy

Default to minimum retention.

Do not permanently store by default:

- screenshots,
- LinkedIn message text,
- generated reply history.

Store locally:

- application configuration,
- selected capture source restore metadata where allowed,
- ROI coordinates,
- endpoint definitions,
- model preferences,
- prompt files,
- non-sensitive performance/health metrics.

### 20.1 Logs

Normal logs should record events such as:

```text
capture_started
capture_succeeded
extractor=ocr
classification=sales_outreach
backend=network-ollama
model=<name>
generation_ms=1432
insert_succeeded
```

They should not dump complete private LinkedIn messages unless an explicit debug mode is enabled.

### 20.2 Debug captures

If debug capture saving is enabled, show a clear warning and provide a button to delete saved debug data.

---

## 21. Error Handling and Recovery

### 21.1 Screen source unavailable

Show:

> Browser capture source is unavailable. Select the browser window again.

Do not crash or silently capture another window.

### 21.2 Hotkey unavailable

Show:

> Global hotkey is unavailable on this desktop. Capture & Draft remains available from the application.

### 21.3 OCR poor

Show the screenshot and editable extracted text. Allow manual correction and regeneration.

### 21.4 Network Ollama down

Attempt local Ollama according to policy and show the reason for fallback.

### 21.5 All AI backends unavailable

Keep the capture and extracted text visible and show a retry action. Do not discard the capture state.

### 21.6 Extension disconnected

Generation remains usable, but **Insert into LinkedIn** is disabled. Offer **Copy Draft**. It is a full, supported path (manual mode, §14.1b), not only an emergency fallback.

### 21.7 LinkedIn composer not found

Do not paste somewhere else. Return a precise error and leave the draft intact.

---

## 22. Performance Targets

These are interaction targets, not promises.

### 22.1 Capture

After hotkey/button press:

- frame acquisition should normally feel immediate,
- target well under 1 second when a live PipeWire stream already exists.

### 22.2 OCR/extraction

Target:

- approximately 0.2–2 seconds depending on extractor and hardware.

### 22.3 Backend failover

An unreachable preferred network Ollama node should not stall the user for many seconds.

Initial design target:

- short connection timeout,
- cached health state,
- local fallback quickly after a failed probe.

Exact timeout values should be tuned on the actual LAN.

### 22.4 Draft generation

Short LinkedIn replies should be optimized for interactive latency.

The application should measure:

- capture time,
- extraction time,
- backend selection time,
- model generation time,
- total hotkey-to-draft time.

A practical MVP target is to make **Capture & Draft** complete in a few seconds on the network GPU node for normal short messages.

---

## 23. Testing Strategy

Testing is required before depending on LinkedIn itself.

### 23.1 Unit tests

Cover:

- configuration parsing,
- state transitions,
- backend priority,
- health-cache behavior,
- timeout/fallback logic,
- model selection,
- classification parsing,
- prompt construction,
- stale-result suppression,
- conversation fingerprint comparison,
- log redaction.

### 23.2 Capture test harness

Create a local deterministic **Capture Test Window** containing sample LinkedIn-like message text.

This allows testing:

- ScreenCast source selection,
- PipeWire frames,
- ROI cropping,
- global shortcut triggering,
- OCR quality,
- screenshot preview,

without needing LinkedIn for every development test.

### 23.3 OCR fixtures

Keep sanitized image fixtures for:

- light theme,
- dark theme,
- normal zoom,
- high-DPI scaling,
- short message,
- multiline message,
- sender name plus conversation text.

Tests should compare extracted text with a tolerant expected result rather than requiring byte-for-byte OCR perfection.

### 23.4 Classification/reply fixtures

Examples:

```text
tests/fixtures/messages/
  friendly_connection_01.yaml
  congratulations_01.yaml
  sales_pitch_01.yaml
  lead_generation_01.yaml
  meeting_request_01.yaml
  recruiting_01.yaml
  prompt_injection_01.yaml
```

Each fixture can contain:

- incoming text,
- expected category,
- forbidden reply patterns,
- required policy behavior,
- optional human-rated reference characteristics.

### 23.5 Ollama integration tests

Verify:

- version probe,
- model discovery,
- text generation,
- selected-model missing behavior,
- network endpoint timeout,
- local fallback,
- vision generation if configured.

These tests should be marked separately so ordinary unit tests do not require a live model server.

### 23.6 Browser-extension tests

Verify:

- extension connects,
- active LinkedIn tab detection,
- composer detection,
- text insertion,
- read-back verification,
- no Send action,
- refusal when no LinkedIn composer is present.

### 23.7 Manual LinkedIn acceptance test

Only after the local harness works:

1. open a LinkedIn conversation,
2. select browser capture source,
3. set conversation ROI,
4. press Capture & Draft,
5. confirm screenshot is correct,
6. confirm extracted message is correct,
7. confirm classification is sensible,
8. edit generated draft,
9. press Insert into LinkedIn,
10. verify the text appears in the correct composer,
11. verify nothing was sent automatically.

---

## 24. MVP Engineering Gates

The project should advance through explicit gates. Each gate should work before adding the next major subsystem.

### Gate 0 — Environment preflight

Deliver:

- PySide6 app launches,
- session/desktop detection,
- ScreenCast portal detection,
- GlobalShortcuts portal detection,
- PipeWire status,
- network/local Ollama status.

Exit condition:

> The application can accurately describe what the current Manjaro/Wayland environment supports.

### Gate 1 — Screen capture spike

Deliver:

- Select Browser/Test Window,
- live PipeWire source,
- Capture button,
- screenshot preview,
- ROI selector,
- no OCR yet required for the earliest spike.

Exit condition:

> Pressing Capture reliably produces the correct current browser/test-window image.

This is the first critical technical proof.

### Gate 2 — Global Capture & Draft trigger

Deliver:

- GlobalShortcuts portal integration where supported,
- Configure Hotkey UI,
- same command path for button and hotkey,
- conflict-safe registration behavior,
- rapid-repeat/supersession protection.

Exit condition:

> The configured global shortcut triggers the same capture as the UI button without changing existing OS shortcut configuration.

### Gate 3 — Extraction

Deliver:

- OCR baseline,
- extracted text editor,
- extraction warnings,
- fixtures and tests,
- optional vision extractor if the Ollama node supports a verified model.

Exit condition:

> Visible LinkedIn-like text can be extracted reliably enough for the user to verify/correct it.

### Gate 4 — Classification and draft generation

Deliver:

- backend manager,
- network Ollama first,
- local fallback,
- category classification,
- reply rules,
- editable generated draft,
- backend/model/timing display.

Exit condition:

> Capture & Draft produces a useful editable answer from the test harness and sanitized message fixtures.

### Gate 5 — LinkedIn insertion

Deliver:

- first-browser extension,
- secure local/native bridge,
- composer location,
- text insertion,
- read-back verification,
- conversation-safety check,
- no Send action.

Exit condition:

> An edited draft can be inserted into the correct LinkedIn reply composer with one explicit button press.

### Gate 6 — MVP hardening

Deliver:

- robust errors,
- cancellation,
- stale draft handling,
- settings persistence,
- privacy/log review,
- packaging/run instructions,
- repeatable acceptance test.

Exit condition:

> The workflow is dependable enough for normal daily use with human review.

---

## 25. MVP Acceptance Criteria

The MVP is complete when all of the following are true.

### Capture and hotkey

1. The application runs as a normal user on the target Manjaro system.
2. The user can select the browser window through the Wayland portal.
3. The app can capture the current frame from that browser window.
4. The user can define and persist a conversation ROI.
5. A visible **Capture & Draft** button always works.
6. When the desktop supports it, a user-approved global hotkey triggers the same action.
7. The application never silently overwrites or remaps an existing OS shortcut.
8. If a global shortcut cannot be registered, the UI clearly says so and continues to work without it.

### Extraction and AI

9. The captured image is visible in the app.
10. The extracted conversation text is visible and editable.
11. The system assigns a visible message category.
12. The user can override the category.
13. The preferred network Ollama node is tried first.
14. Local Ollama is used automatically when the network node is unavailable according to configured policy.
15. The UI shows which backend and model produced the reply.
16. The generated reply is editable.
17. Regeneration works after editing extraction text or category.
18. A cancelled or superseded generation cannot overwrite a newer draft.

### Insertion

19. The first supported browser has a working extension/bridge.
20. **Insert into LinkedIn** inserts the current draft into the reply composer.
21. The application verifies insertion rather than assuming it succeeded.
22. The application does not press Send.
23. The application blocks or warns on a likely conversation mismatch.
24. If insertion is unavailable, the draft remains accessible and can be copied manually.

### Quality and safety

25. At least the initial reply categories have fixture-based tests.
26. Prompt-injection fixtures do not override user policy.
27. Message/screenshot content is not persisted by default.
28. Logs do not contain complete private conversations by default.
29. Failure states are understandable from the UI without reading a Python traceback.
30. The end-to-end workflow succeeds repeatedly on several real LinkedIn conversations before being considered ready for normal use.

---

## 26. Repository Structure

Suggested initial layout:

```text
linkedin-reply-assistant/
├── VISION.md
├── README.md
├── pyproject.toml
├── config/
│   ├── app.yaml
│   ├── backends.yaml
│   ├── reply_rules.yaml
│   ├── user_profile.yaml
│   └── prompts/
├── src/
│   └── linkedin_reply_assistant/
│       ├── app.py
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── capture_view.py
│       │   ├── message_view.py
│       │   ├── draft_view.py
│       │   └── settings_dialog.py
│       ├── state/
│       │   └── workflow.py
│       ├── capture/
│       │   ├── portal.py
│       │   ├── pipewire.py
│       │   ├── frame.py
│       │   └── roi.py
│       ├── shortcuts/
│       │   ├── base.py
│       │   ├── portal_global_shortcuts.py
│       │   └── disabled.py
│       ├── extraction/
│       │   ├── base.py
│       │   ├── ocr.py
│       │   ├── vision.py
│       │   └── quality.py
│       ├── reply_engine/
│       │   ├── classifier.py
│       │   ├── policies.py
│       │   ├── prompts.py
│       │   └── generator.py
│       ├── backends/
│       │   ├── base.py
│       │   ├── ollama.py
│       │   └── manager.py
│       ├── browser_bridge/
│       │   ├── base.py
│       │   ├── localhost_bridge.py
│       │   └── native_messaging.py
│       ├── diagnostics/
│       └── config/
├── extension/
│   ├── manifest.json
│   ├── background/
│   └── content/
├── tools/
│   └── capture_test_window.py
└── tests/
    ├── unit/
    ├── integration/
    ├── fixtures/
    │   ├── screenshots/
    │   └── messages/
    └── browser/
```

---

## 27. Implementation Technology Choices

These are recommended starting choices, not irreversible commitments.

### Desktop UI

- Python
- PySide6
- `asyncio` integration or worker threads so capture/OCR/model calls never block the GUI event loop

### Portal communication

Use a D-Bus library suitable for async integration, for example `dbus-next`.

### PipeWire frame access

A practical Python path is GStreamer/PyGObject with `pipewiresrc`, or another small native adapter if Python bindings prove unreliable.

This should be validated in Gate 1 before committing the rest of the architecture to a particular frame library.

### OCR

Start by benchmarking Tesseract and one modern OCR alternative on actual screenshots. Keep OCR behind an interface so the winner can change without touching the UI.

### AI

Direct Ollama HTTP API client with:

- explicit timeouts,
- cancellation,
- model discovery,
- health/version probing,
- optional image requests for vision models.

### Browser integration

WebExtension API plus Native Messaging when possible.

---

## 28. Important Design Gaps Still Requiring User Input

The architecture is now detailed enough to start Gate 0 and Gate 1. The following inputs are still required before the full reply behavior is considered correct.

### Required before classification/reply tuning

1. **Unsolicited-decline prompt**
   - the user's existing prompt/rules.

2. **Language policy**
   - English only,
   - mirror sender language,
   - or another rule.

3. **User profile snippets allowed in replies**
   - for example when it is appropriate to mention current work or agentic AI.

4. **Desired reply length**
   - short by default,
   - medium,
   - category-dependent.

### Required before browser insertion

5. **First browser**
   - Firefox or Chromium/Chrome.

### Required before backend implementation on the real system

6. **Network Ollama endpoint**
   - URL/host,
   - authentication if any,
   - HTTP or HTTPS.

7. **Local Ollama policy**
   - only use it if already running,
   - or allow the application to offer to start it.

### Useful but not blocking Gate 1

8. Desktop environment on the target Manjaro installation, for example KDE Plasma or GNOME.
9. Typical browser zoom level and display scaling.
10. Whether LinkedIn is usually used in light or dark theme.

---

## 29. Risks and Mitigations

### 29.1 Wayland portal differences

**Risk:** Portal behavior differs by desktop environment/version.

**Mitigation:** Preflight capability detection, UI fallback button, test Gate 1 before building higher layers.

### 29.2 Global hotkey support is not universal

**Risk:** GlobalShortcuts portal may be unavailable or behave differently.

**Mitigation:** Treat the hotkey as optional; never make it the only way to capture.

### 29.3 OCR reads unrelated UI text

**Risk:** Full-window OCR includes sidebars and navigation.

**Mitigation:** user-defined ROI, screenshot preview, editable extracted text.

### 29.4 OCR confuses message ownership

**Risk:** OCR alone may not know which text is incoming versus outgoing.

**Mitigation:** crop carefully; use layout/vision extraction when available; keep human-verifiable extracted text; later add DOM extraction.

### 29.5 LinkedIn DOM changes

**Risk:** Extension selectors for the composer change.

**Mitigation:** isolate selectors, use semantic/contenteditable clues, add browser tests, fail rather than inserting into an unknown element.

### 29.6 Wrong-conversation insertion

**Risk:** User captures conversation A, then navigates to B before pressing Insert.

**Mitigation:** draft fingerprint, active-conversation verification where possible, stale-draft state, explicit blocking/warning.

### 29.7 Slow dead network Ollama endpoint

**Risk:** every reply stalls while waiting for a dead node.

**Mitigation:** short probe timeout, health cache, deterministic local fallback, periodic recovery probe.

### 29.8 LLM sounds generic

**Risk:** replies become formulaic.

**Mitigation:** category-specific prompts, actual incoming-message context, user rules, fixture review, model comparison, easy regeneration/editing.

### 29.9 Prompt injection

**Risk:** sender text attempts to override system behavior.

**Mitigation:** strict separation of policy and message data, structured output, adversarial tests, no model-controlled tools/actions.

---

## 30. Post-MVP Evolution

After the screen-capture workflow is proven, the next major improvement should be **structured browser extraction**.

The extension can then optionally provide:

- sender name,
- current conversation text,
- message direction,
- recent context,
- stable conversation identity.

At that point the application can choose extraction mode:

1. **DOM** — preferred when the extension can confidently read the conversation,
2. **Screen/Vision** — useful when DOM extraction is unavailable or broken,
3. **Screen/OCR** — universal local fallback.

This preserves the screen-capture work rather than replacing it.

Later additions may include:

- second browser support,
- OpenAI provider,
- Anthropic provider,
- other OpenAI-compatible endpoints,
- richer language support,
- configurable per-category model choice,
- optional non-sensitive draft metrics,
- profile-context extraction with explicit user controls.

---

## 31. Self-Review of This Plan

This plan was reviewed against the requested workflow and the main engineering failure modes.

### Resolved gaps

- **Screen capture is no longer deferred.** It is now the first technical proof and the core of the MVP.
- **Global hotkeys are explicitly designed for Wayland.** The plan does not rely on X11 keyboard grabbing or root privileges.
- **Shortcut collision handling is realistic.** The compositor/portal mediates global shortcut ownership; the application does not pretend it can enumerate all OS shortcuts.
- **The UI button remains a guaranteed fallback.** Hotkey failure cannot make the application unusable.
- **Capture and hotkey use one code path.** This avoids separate behavior and testing drift.
- **ROI selection is included.** Without it, OCR quality on LinkedIn would likely be unnecessarily poor.
- **The extraction result is editable.** This prevents an LLM from hiding OCR errors behind fluent output.
- **The full one-action pipeline is defined.** Capture automatically flows into extraction, classification, and generation.
- **Insertion remains a second explicit action.** The user can inspect/edit the result before anything is placed into LinkedIn.
- **Insertion is verified.** The extension reads back the composer instead of assuming text entry succeeded.
- **Wrong-conversation risk is addressed.** Drafts are tied to capture/conversation identity and can become stale.
- **Backend failover is visible.** The user can see whether network or local Ollama was used.
- **Concurrency is addressed.** Rapid hotkey presses or slow model responses cannot overwrite newer work.
- **Privacy is addressed.** Captures and messages are not written to disk by default.
- **Testing does not depend on LinkedIn.** A local capture test window allows most of the hard Wayland/OCR work to be verified deterministically.

### Remaining uncertainties that must be tested rather than guessed

- exact GlobalShortcuts portal behavior on the user's desktop environment,
- the most reliable Python/PipeWire frame-access implementation on that Manjaro installation,
- which OCR engine performs best with the user's browser scaling/theme,
- whether a suitable installed Ollama vision model can improve screenshot extraction,
- the exact LinkedIn composer selectors/events needed by the first chosen browser,
- the best model and timeout settings on the actual 40 GB Ollama node.

These uncertainties are intentionally placed early in the engineering gates so they are discovered before significant code is built on top of them.

---

## 32. Definition of Success

The product is successful when the user's normal rhythm becomes:

> open a LinkedIn conversation → press one hotkey → inspect a good draft → make a quick edit if needed → press Insert → manually Send

The application should feel like a fast, local drafting console rather than an automation bot.

The immediate next engineering task after this document is **Gate 0 + Gate 1: environment preflight and a Wayland ScreenCast/PipeWire capture prototype with a polished minimal PySide6 UI**.
