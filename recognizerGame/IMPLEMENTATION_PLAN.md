# Implementation Plan

This plan delivers the MVP in small, reviewable commits. Each implementation commit should do one coherent job, include or update relevant tests, pass the repository checks, and leave the application runnable. Commit messages below are proposals and may be adjusted to match the final repository conventions.

## Technical baseline

- TypeScript, React, and Vite
- CSS with custom properties and responsive layouts
- Static repository-owned icon assets
- Browser `localStorage` behind a versioned storage adapter
- Vitest and Testing Library for unit/component tests
- Playwright for critical end-to-end flows
- ESLint and Prettier
- Optional Vite PWA integration after the online browser build is stable

No backend is required for the MVP. Game rules and state transitions should live in framework-independent TypeScript modules.

## Delivery principles

- Keep generated card membership separate from randomized visual layout.
- Treat timestamps and derived elapsed time as the scoring source of truth.
- Make random behavior injectable or seedable for reproducible tests.
- Validate persisted data at the storage boundary; never trust parsed browser data.
- Prefer accessible native controls and explicit state transitions.
- Do not combine unrelated refactors, formatting changes, assets, and features in one commit.
- Do not commit failing tests or knowingly broken intermediate states.
- Record future multiplayer only as an architectural boundary, not as unused MVP infrastructure.

## Proposed atomic commit sequence

### 1. Scaffold the web application

**Commit:** `chore(recognizer): scaffold React TypeScript app`

- Create the Vite React/TypeScript project in this directory.
- Add package scripts for development, build, preview, type checking, linting, and testing.
- Add a minimal app shell and global style reset.
- Add ESLint, Prettier, Vitest, Testing Library, and baseline configuration.
- Add one smoke test proving the app renders.

**Verify:** clean install, lint, type check, unit test, and production build all pass.

### 2. Define game-domain types and constants

**Commit:** `feat(recognizer): define game domain model`

- Define stable symbol IDs, challenge sizes (`10 | 20 | 50`), card data, run states, results, rankings, and preference types.
- Define constants for the 57 symbols and supported challenge sizes.
- Document that challenge size is total cards and derive decision count as `cards - 1`.
- Add type-level and runtime guards where external data enters the domain.

**Verify:** unit tests cover valid challenge sizes, decision counts, and rejected invalid values.

### 3. Generate and verify the canonical deck

**Commit:** `feat(recognizer): add verified projective-plane deck`

- Implement a deterministic finite-projective-plane construction of order 7.
- Generate or commit the canonical 57 card definitions with 8 symbol IDs each.
- Keep generation deterministic so changes are reviewable.
- Add exhaustive invariants for all cards and all 1,596 card pairs.

**Verify:** tests prove 57 cards, 57 symbols, 8 unique symbols per card, each symbol on 8 cards, and one shared symbol for every pair.

### 4. Add run selection and seeded shuffling

**Commit:** `feat(recognizer): select and shuffle challenge cards`

- Implement unbiased card shuffling with an injectable random source.
- Select exactly 10, 20, or 50 distinct cards.
- Expose deterministic seeds for tests and development reproduction.
- Return the ordered challenge without mutating the canonical deck.

**Verify:** tests cover each tier, uniqueness, deterministic seeds, and unchanged source data.

### 5. Add symbol metadata and asset manifest

**Commit:** `feat(recognizer): add symbol catalog and asset contract`

- Add all 57 canonical names, primary colors, accessible labels, and asset paths.
- Validate one-to-one coverage between symbol IDs, metadata, deck references, and assets.
- Add an asset-generation record containing the shared art-direction prompt and per-icon subject prompts.
- Add a temporary development-safe placeholder only if artwork generation is performed in later batches.

**Verify:** catalog tests reject missing, duplicate, or orphaned entries.

### 6. Generate the icon library

**Commit:** `assets(recognizer): add generated clip-art symbol library`

- Use the image-generation tool to create all 57 repository-owned icons with a consistent thick-outline, single-dominant-color style.
- Normalize canvas dimensions, transparency, padding, and file format without altering the artwork's identity.
- Review at actual minimum and maximum rendered sizes.
- Replace subjects that are confusing when rotated or visually too similar.
- Store a contact sheet for review as development documentation, not as a runtime dependency.

**Verify:** an asset script/test confirms all expected files exist, decode correctly, use the intended dimensions, and have no unexpected extras. Human sign-off confirms distinctness and stylistic consistency.

### 7. Implement deterministic collision-free card layout

**Commit:** `feat(recognizer): generate collision-free card layouts`

- Model the circular usable area, icon bounds, padding, scale range, and rotation range.
- Generate eight placements with bounded attempts and a deterministic fallback layout.
- Account for rotated bounds and touch-target spacing.
- Return placement data independently of rendering.
- Expose tuning constants in one documented module.

**Verify:** property-style tests run many seeds and assert eight placements, no overlap, in-bounds geometry, allowed size/rotation, determinism, and guaranteed fallback.

### 8. Render responsive, interactive cards

**Commit:** `feat(recognizer): render responsive symbol cards`

- Build card and symbol components from immutable membership plus placement data.
- Preserve image aspect ratio and enlarge the interactive target without changing visual bounds.
- Allow selection from either card.
- Add labels and focus behavior appropriate to the visual interaction.
- Add desktop side-by-side and mobile stacked sizing.

**Verify:** component tests cover eight symbols, correct IDs, either-card callbacks, and responsive visual snapshots or focused CSS assertions.

### 9. Implement the game state machine

**Commit:** `feat(recognizer): implement single-player game state`

- Implement preparing, active, transitioning, completed, and abandoned states.
- Track current index, completed decisions, remaining decisions, and incorrect selections.
- Accept only the shared symbol and advance exactly one card.
- Ignore repeated input during successful transitions.
- Keep domain transitions pure and UI-independent.

**Verify:** tests cover complete runs for all tiers, wrong guesses, either-card selection, final completion, and rapid duplicate input.

### 10. Add the wall-clock timer

**Commit:** `feat(recognizer): track wall-clock completion time`

- Record start and finish timestamps with an injectable clock.
- Derive the visible time from the current timestamp rather than interval counts.
- Continue across focus loss and browser throttling.
- Freeze integer milliseconds on the final correct match.
- Add consistent active and result time formatting.

**Verify:** fake-clock tests cover start timing, long gaps, final freeze, formatting, and the absence of pause behavior.

### 11. Build the main menu and help experience

**Commit:** `feat(recognizer): add menu and game instructions`

- Add optional player name, tier selector, timed-challenge explanation, and start action.
- Add concise help with a visual example and accurate progression rules.
- Add routes or an explicit top-level view model for menu, help, rankings, game, and results.
- Enforce and explain the player-name length limit.

**Verify:** component tests cover defaults, selection, validation, help navigation, and creation of exact-size challenges.

### 12. Connect the playable game screen

**Commit:** `feat(recognizer): connect timed gameplay screen`

- Connect challenge creation, layouts, cards, state, timer, and progress.
- Label current and next cards clearly.
- Add correct-pair highlighting and brief transition feedback.
- Add non-blocking incorrect-selection warning without revealing the answer.
- Add confirmed restart and leave flows.

**Verify:** interaction tests cover correct and incorrect selections, progress, timer visibility, transition guarding, restart, abandonment, and completion.

### 13. Add sound and motion preferences

**Commit:** `feat(recognizer): add feedback preferences`

- Add optional short error/correct sounds using repository-owned assets or generated tones.
- Add sound and reduced-motion controls.
- Respect `prefers-reduced-motion` as the initial motion preference.
- Handle browser audio restrictions without blocking play.

**Verify:** tests cover muted operation, preference toggles, reduced transitions, and unavailable audio APIs.

### 14. Implement versioned local persistence

**Commit:** `feat(recognizer): persist local game data`

- Add a versioned storage schema for results and preferences.
- Validate, normalize, and safely recover from absent, malformed, or future-version data.
- Persist player name, tier, sound/motion settings, and completed results only.
- Add a confirmed clear-all-data operation.

**Verify:** adapter tests cover round trips, corruption, migrations, unavailable/quota-failed storage, and clearing.

### 15. Add rankings and results

**Commit:** `feat(recognizer): rank challenge results locally`

- Insert completed results into tier-specific rankings ordered by elapsed milliseconds.
- Resolve exact ties by completion/insertion order, first result first.
- Retain the best 10 per tier and allow duplicate names.
- Derive personal best for exact normalized display name and tier.
- Build results and ranking screens with placeholders and replay/navigation actions.

**Verify:** tests cover tier isolation, ties, trimming, duplicates, personal bests, outside-ranking results, and persistence after reload.

### 16. Harden responsive and accessible behavior

**Commit:** `fix(recognizer): improve responsive accessibility`

- Audit small portrait phones, tablets, desktop, zoom, and orientation changes.
- Ensure touch targets, focus indicators, contrast, semantic headings, live warnings, and confirmation dialogs are usable.
- Prevent card clipping and page-level gesture conflicts without disabling normal browser navigation.
- Confirm all non-game controls work by keyboard.

**Verify:** automated accessibility checks pass on main states; manual checklist covers touch, keyboard controls, 200% zoom, reduced motion, and sound off.

### 17. Add end-to-end browser coverage

**Commit:** `test(recognizer): cover critical browser journeys`

- Configure Playwright for desktop and mobile-sized browsers.
- Test a deterministic short game, wrong selection, completion, ranking persistence after reload, restart confirmation, data clearing, and help.
- Add test-only deterministic deck/layout/clock hooks that are excluded or inert in production.

**Verify:** the full lint, type-check, unit, component, end-to-end, and build pipeline passes.

### 18. Add installable/offline browser support

**Commit:** `feat(recognizer): add installable offline app shell`

- Add the web app manifest, application icons, theme metadata, and service worker.
- Cache the application shell and all symbol/audio assets after first successful load.
- Define a safe update strategy so a new release does not mix incompatible source and cached assets.
- Keep local scores independent of cache cleanup where the browser permits.

**Verify:** production build is installable, reloads offline after first load, and updates cleanly in a browser audit.

### 19. Document release and playtest results

**Commit:** `docs(recognizer): document MVP operation and tuning`

- Update the README with final commands, supported browser policy, architecture summary, and storage behavior.
- Record human playtest findings for icon ambiguity and layout fairness.
- Adjust documented tuning values to match the implementation.
- Add a concise manual acceptance checklist and known limitations.

**Verify:** run the full acceptance checklist against the production build with mouse and touch input.

## Milestones

### Milestone A: Mathematical vertical slice

Complete commits 1–4. The app builds, and the most important invariant—the canonical deck—is exhaustively proven.

### Milestone B: Visual card prototype

Complete commits 5–8. Stakeholders can review final icon direction, minimum readable size, layout density, rotation, and responsive card presentation before full gameplay is built.

### Milestone C: Playable alpha

Complete commits 9–12. All three challenge tiers are playable end to end, but rankings and polish may still be incomplete.

### Milestone D: Persistent beta

Complete commits 13–16. Feedback, preferences, results, local rankings, responsiveness, and accessibility are ready for structured playtesting.

### Milestone E: MVP release candidate

Complete commits 17–19. Browser journeys, offline installation, documentation, and manual acceptance checks are complete.

## Review gates

Implementation should pause for stakeholder review at these points:

1. **Art gate:** approve a small representative icon batch before generating all 57 assets.
2. **Readability gate:** approve card scale, spacing, rotation, and mobile presentation using the visual prototype.
3. **Feel gate:** play the 10-card alpha and tune transition duration, feedback, and default sound behavior.
4. **Acceptance gate:** run the documented criteria on the production build before calling the MVP complete.

The gates tune presentation inside the agreed scope. A request that changes the card mathematics, challenge-size meaning, ranking model, or MVP multiplayer scope should update the product specification before implementation continues.

## Definition of done for every implementation commit

- The change has a single coherent purpose reflected in its commit message.
- Relevant automated tests are included and passing.
- Type checking and linting pass.
- The application still starts and builds.
- New behavior has accessible labels and responsive styling where applicable.
- User-facing rules agree with the README.
- No unrelated files or generated local artifacts are included.
