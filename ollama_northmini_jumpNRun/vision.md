You are an autonomous senior game developer and QA engineer. Build a polished **2D side-scrolling jump-and-run browser game** inspired by the tight movement, pacing, readability, and playful level design of classic games such as *Super Mario Land*, while using **entirely original characters, enemies, art, sounds, names, and level layouts**.

## Target

* Runs fully in the browser.
* Primary target: **latest Firefox desktop**.
* No server dependency during gameplay.
* Smooth 60 FPS where hardware permits.
* Keyboard-first controls.
* Responsive to common desktop window sizes.
* Everything required to run the game must live in the repository.

## Game

Implement a complete, playable side-scrolling platformer with:

* Player walking/running.
* Acceleration and deceleration.
* Responsive jumping with variable jump height.
* Good coyote time and jump buffering.
* Gravity and collision handling that feel precise rather than floaty.
* Horizontal camera scrolling with smooth tracking.
* Platforms, pits, obstacles, moving platforms, and environmental hazards.
* Multiple enemy types with distinct movement patterns.
* Enemies that walk, turn at edges/walls where appropriate, jump, patrol, or otherwise create interesting timing challenges.
* Player/enemy collision and defeat logic.
* Ability to defeat appropriate enemies by jumping on them.
* Collectibles and score.
* Health/lives or another clear failure system.
* Checkpoints where useful.
* Start screen, gameplay HUD, pause, game-over state, and restart.
* At least **3 progressively more challenging levels**.
* Clear level completion condition.
* Appropriate sound effects and optional lightweight music.
* Nicely animated player, enemies, collectibles, environmental elements, transitions, and UI.

## Visual direction

Use crisp, charming, highly readable pixel-art or pixel-inspired visuals with a limited palette and strong silhouettes. Capture the simplicity and charm of early handheld platformers without reproducing Nintendo assets, characters, level geometry, sprites, music, trademarks, or other copyrighted material.

Ensure:

* Crisp rendering without blurry sprite scaling.
* Consistent animation timing.
* Smooth camera movement.
* Strong visual feedback for jumping, landing, damage, enemy defeat, pickups, checkpoints, and level completion.
* Small details such as squash/stretch, particles, screen shake, or impact effects where they improve game feel without becoming distracting.

## Technical approach

Choose a lightweight architecture suitable for Firefox. Prefer:

* HTML5
* CSS
* JavaScript or TypeScript
* Canvas/WebGL through a suitable lightweight game framework if beneficial

Keep dependencies minimal.

Use:

* Fixed-timestep or otherwise robust game simulation.
* Delta-time handling that does not make physics frame-rate dependent.
* Clear separation between rendering, physics, input, entities, levels, audio, UI, and game state.
* Deterministic, maintainable collision logic.
* Asset preloading.
* No console errors during normal operation.

## Controls

Default controls:

* Arrow keys or A/D: move.
* Space, Z, or Up: jump.
* Escape: pause.
* R: restart where appropriate.

Controls must feel immediate and consistent.

## Local development pipeline

Create a complete local development workflow.

Include:

* Dependency installation.
* Development server.
* Production build.
* Linting.
* Formatting.
* Automated tests.
* Browser/end-to-end tests where practical.
* A single command or small command sequence that verifies the project before release.

Use an appropriate toolchain such as Vite plus Playwright, Vitest, ESLint, or equivalent.

The project must work from a clean checkout with documented commands.

## Autonomous execution

Do not stop at scaffolding or a prototype.

Work iteratively:

1. Inspect the repository and establish the architecture.
2. Create the minimum playable vertical slice.
3. Run it locally.
4. Test movement, jumping, collisions, scrolling, enemies, death, restart, and level completion.
5. Fix defects.
6. Add animation, effects, audio, UI, and additional levels.
7. Run automated tests and production builds.
8. Test explicitly in Firefox.
9. Review gameplay quality yourself.
10. Identify anything that feels broken, rough, inconsistent, visually weak, or frustrating.
11. Fix it.
12. Repeat testing and review until the game is genuinely polished.

## Self-review criteria

Before declaring completion, explicitly verify:

* Game starts successfully in Firefox.
* No blocking console errors.
* Production build succeeds.
* Automated tests pass.
* Player cannot routinely fall through platforms.
* Collision behavior is stable at edges and corners.
* Jump buffering works.
* Coyote time works.
* Holding jump produces a higher jump than tapping it.
* Camera motion is smooth.
* Enemies interact correctly with terrain.
* Enemy defeat mechanics work reliably.
* Player damage/death works reliably.
* Restart never leaves stale state.
* Level transitions work.
* All levels can actually be completed.
* No unavoidable deaths caused by poor level layout.
* Animations correspond correctly to gameplay state.
* Pixel graphics remain crisp under normal scaling.
* Audio does not repeatedly restart or stack incorrectly.
* Pausing freezes gameplay correctly.
* Performance remains smooth during normal play.

## Browser QA

Use automated browser tooling where possible to:

* Launch the game.
* Load every level.
* Exercise movement and jumping.
* Detect runtime errors.
* Verify restart and navigation flows.
* Capture screenshots when useful for visual review.

Run the relevant suite using **Firefox**, not only Chromium.

## Game-feel review

After functional correctness, perform at least one dedicated polish pass focused entirely on game feel:

* Tune acceleration.
* Tune maximum movement speed.
* Tune gravity.
* Tune jump impulse.
* Tune short-hop behavior.
* Tune coyote time.
* Tune jump buffering.
* Tune enemy speed.
* Tune camera lag/dead-zone.
* Tune animation timing.
* Remove unfair obstacle placement.
* Improve visual and audio feedback.

Prefer responsive, satisfying gameplay over physically realistic movement.

## Deliverables

Finish with:

* Fully working source code.
* Original game assets.
* At least 3 playable levels.
* Local development/build/test pipeline.
* Automated tests.
* Firefox browser test.
* README containing exact setup and run commands.
* Concise architecture explanation.
* Concise description of the QA performed.
* List of any remaining known limitations.

Do not claim completion merely because the code compiles. **Completion means the game has been built, run, tested, reviewed, fixed, retested, and is enjoyable and reliable in Firefox.**

Make reasonable implementation decisions autonomously. When something is ambiguous, choose the option that produces the strongest playable game rather than stopping to ask for minor clarification.
