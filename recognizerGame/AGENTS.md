# AGENTS.md

Contributor instructions for work in `recognizerGame/` and its descendants.

## Read first

Before changing the project, read:

1. `README.md` — authoritative MVP product specification.
2. `IMPLEMENTATION_PLAN.md` — intended architecture, sequence, verification, and review gates.

If old notes or prompts disagree with the README, follow the README. Do not silently reinterpret product rules. Update the specification in a dedicated documentation commit when an approved decision changes.

## Product invariants

These rules are non-negotiable unless the stakeholder explicitly changes the specification:

- The canonical deck has 57 cards and 57 symbols.
- Every card has exactly 8 unique symbols.
- Every pair of distinct cards shares exactly 1 symbol.
- Challenge sizes are 10, 20, or 50 **total cards**, producing 9, 19, or 49 matching decisions.
- A player may select the shared symbol on either visible card.
- Wrong selections give non-blocking feedback only. They do not advance, reveal the answer, lock play, or add a score penalty.
- The score is elapsed wall-clock time. It continues across focus loss, tab changes, minimization, and sleep.
- Rankings are separate by challenge size, fastest first, best 10, with exact ties ordered first-completed first.
- Persistence is local to the browser/device. The MVP has no accounts, backend, global leaderboard, multiplayer, or tournament mode.
- User-facing text must not name or reference an existing commercial game, brand, or source of inspiration.

Add or retain exhaustive tests for the deck invariants. Never hand-edit card membership without regenerating and re-running those tests.

## Architecture boundaries

- Keep deck construction, challenge selection, game transitions, time calculation, ranking, persistence validation, and card-layout geometry in framework-independent TypeScript.
- Keep canonical card membership immutable. Visual position, scale, and rotation are presentation data and may be randomized independently.
- Inject randomness and time into domain functions. Tests must be deterministic and problematic layouts must be reproducible by seed.
- Derive elapsed time from timestamps; do not use interval tick counts as score data.
- Put browser storage behind a versioned, validated adapter. Gracefully handle missing, corrupt, unavailable, or quota-limited storage.
- Model game phases explicitly. Guard the transition after a correct selection so rapid input cannot advance twice.
- Do not build speculative networking or tournament infrastructure for the MVP. Preserve clean domain boundaries instead.

## Visual assets

- Create canonical symbol artwork specifically for this project; do not substitute third-party clip art.
- Generate and obtain approval for a representative batch before producing all 57 icons.
- Follow the README art direction: thick black outline, bold recognizable silhouette, one dominant fill color, minimal detail, transparent clean background, and consistent padding.
- Store canonical runtime assets and useful generation prompts/metadata in the repository.
- Use the same source asset every time a symbol appears. Do not recolor, morph, or mirror symbols per card.
- Review icons at their actual minimum display size and under allowed rotation. Replace ambiguous subjects rather than compensating with color alone.
- Optimize generated assets reproducibly; do not overwrite original approved sources without an explicit reason.

## Layout and interaction quality

- All eight symbols and their interactive bounds must remain inside the card and must not overlap.
- Provide a bounded layout algorithm with a guaranteed deterministic fallback. Never allow an unbounded placement loop.
- Keep touch targets large enough even when the visible icon is smaller.
- Test representative narrow portrait, tablet, and desktop layouts.
- Respect reduced-motion preferences and keep the game fully usable without audio.
- Use native semantic controls, visible focus, sufficient contrast, and non-focus-stealing status messages wherever practical.

## Development workflow

- Follow the atomic sequence in `IMPLEMENTATION_PLAN.md` unless there is a concrete reason to reorder it.
- Keep each commit focused on one coherent behavior and include its tests in the same commit.
- Use Conventional Commit-style messages with the `recognizer` scope where practical, for example `feat(recognizer): add wall-clock timer`.
- Do not mix broad formatting, refactoring, generated assets, and feature behavior in a single commit.
- Preserve unrelated user changes. This directory lives inside a larger repository; stage and commit only paths intended for this project.
- Never use destructive Git commands to discard work. Do not amend or rewrite existing commits unless explicitly asked.
- Do not commit dependency caches, build output, browser reports, editor state, secrets, or local debug artifacts.

## Verification

Once the application scaffold exists, run the project-provided scripts for:

1. formatting check;
2. lint;
3. type checking;
4. unit and component tests;
5. production build;
6. relevant Playwright journeys for user-facing flows.

Use the actual scripts declared in `package.json`; do not assume command names. During early documentation-only work, run `git diff --check` and inspect the staged paths.

Tests should cover at minimum:

- all mathematical deck invariants and all card pairs;
- exact challenge sizes and distinct-card selection;
- seeded shuffle and layout determinism;
- layout bounds, spacing, rotation, and fallback behavior across many seeds;
- correct selection on either card, wrong selection, and double-input guarding;
- wall-clock timing across large clock jumps and final-time freezing;
- ranking tier isolation, ties, duplicates, trimming, and personal bests;
- persistence round trips, malformed data, schema migration, failure, and clearing;
- complete short-game flows at desktop and mobile viewport sizes.

If a required check cannot run, report exactly what was skipped and why.

## Documentation discipline

- Keep game terminology consistent across code, UI, tests, README, and help content.
- Update the README when behavior, supported environments, storage schema expectations, or acceptance criteria change.
- Update the implementation plan when a material delivery decision changes; mark completed work in project tracking rather than rewriting history.
- Record tuning values such as icon scale, rotation, spacing, and transition duration near their implementation and summarize final decisions in the README.
- Treat visual review and hands-on playtesting as required evidence for readability; automated geometry tests alone are insufficient.
