No uncommitted changes, so the review covered commit `HEAD~1..HEAD` (99fbe2e). The faction core itself holds up: win check, `allied()`, the AI friend/enemy checks, homing lock and the friendly-fire stats are consistent with each other. I found 9 issues, all lower-severity correctness, UI or cleanup problems. Nothing here would crash or decide a match wrongly.

9 findings, most severe first:

1. `src/core/stats.ts:213`: `damaged()` now files damage to an ally as friendly fire, but `died()` still adds a kill when a buddy finishes off an allied buddy, so the two disagree.

   Failure scenario: Team A (faction 0) blasts a buddy of allied Team B (faction 0) down to 0 HP: the damage goes to `friendly` and not `dealt`, yet A's buddy gets `kills++`. Kill-based awards and the scoreboard then reward betraying an ally.

2. `src/ui/menu.ts:611`: Removing a team re-indexes the remaining teams, and every team without an explicit `faction` falls back to `faction ?? i`. Removing a team can therefore quietly change which teams are allied.

   Failure scenario: Tag teams on; T0 has no faction set (=0), T1 is set to faction 2, T2 has none (=2), so T1 and T2 are allied. Remove T0: T1 keeps faction 2 but T2 now defaults to 1, and the alliance is gone without the user touching any faction button. The same index fallback in `Game.factionOf` makes it carry into the match.

3. `src/ui/menu.ts:217`: The tag-team toggle pairs `opt.off` ('Off', 'Isključeno') with `title.on` (lowercase 'on', 'upaljen'), a key from the sound status line, so the two labels don't match in case or wording.

   Failure scenario: The setup screen shows 'Off | on' in English and 'Isključeno | upaljen' in Croatian, unlike every other segmented option. It should use a matching options pair (like `WALLED_OPTIONS`) with keys from the same family.

4. `src/app.ts:569`: The test hook's faction `name` is supposed to be null when no custom name exists, but `g.config.factions?.[f] ?? null` returns '' for an unnamed faction, because settings always store four strings.

   Failure scenario: After a reload, `parseSettings` fills `factions` with `['', '', '', '']`, so `__allium.state().factions[i].name` is '' instead of null. An E2E check like `name === null` for an unnamed faction fails or is misread.

5. `src/core/ai.ts:195`: `enemyWeight` rebuilds the rival-team list, sums health over all buddies, runs a second filter and builds a `Set` of factions on every call, and it is called per buddy in `addBlast` for every simulated shot.

   Failure scenario: AI planning scores thousands of candidate blasts per turn; each now pays several array passes plus a `Set` allocation per buddy hit, all with the same result for the whole turn. Compute rivals, faction health and group count once per `planAttack` and pass them in.

6. `src/ui/hud.ts:202`: The faction display-name logic (custom name, else `t('setup.factionNumber')`) is written three times: `app.ts:292-294`, `hud.ts:202-204` and `Menu.factionName`.

   Failure scenario: If the fallback rule changes (e.g. trimming, or a new placeholder key), the three copies drift and HUD, victory screen and setup show different names for the same faction. One shared `factionLabel(config, index)` helper in `src/ui` would replace all three.

7. `src/ui/hud.ts:202`: The HUD works out the faction name (including a `t()` lookup) on every update even when `tagTeams` is off, then throws it away.

   Failure scenario: In every normal match, each HUD update calls `factionOf`, reads `config.factions` and formats a localized string that is never shown. It should only do this inside the `g.config.tagTeams` branch.

8. `src/core/stats.ts:191`: The friendly-fire check is more convoluted than it needs to be. `roster()` always sets `faction` from `factionOf`, which returns the team index when tag teams are off, so the `!== undefined` guard and the separate same-team test are redundant.

   Failure scenario: A reader can't tell when `faction` can be undefined (it never is from `Game`). The check is just `culpritTeam >= 0 && roster.teams[culpritTeam].faction === roster.teams[victim.team].faction`.

9. `src/core/game.ts:293`: The faction-slot limit `4` is hard-coded separately in `Game.factionOf`, `parseTeam` (`settings.ts:184`), `parseSettings` and three `Array.from({ length: 4 })` calls in the menu, with no shared constant.

   Failure scenario: If the team or faction maximum changes, one copy is easily missed. For example, the menu offers a fifth faction that `factionOf` silently treats as 'own team', so allies the user picked are not allied in the match.

---
Final text:
No uncommitted changes, so the review covered commit `HEAD~1..HEAD` (99fbe2e). The faction core itself holds up: win check, `allied()`, the AI friend/enemy checks, homing lock and the friendly-fire stats are consistent with each other. I found 9 issues, all lower-severity correctness, UI or cleanup problems. Nothing here would crash or decide a match wrongly.

9 findings, most severe first:

1. `src/core/stats.ts:213`: `damaged()` now files damage to an ally as friendly fire, but `died()` still adds a kill when a buddy finishes off an allied buddy, so the two disagree.

   Failure scenario: Team A (faction 0) blasts a buddy of allied Team B (faction 0) down to 0 HP: the damage goes to `friendly` and not `dealt`, yet A's buddy gets `kills++`. Kill-based awards and the scoreboard then reward betraying an ally.

2. `src/ui/menu.ts:611`: Removing a team re-indexes the remaining teams, and every team without an explicit `faction` falls back to `faction ?? i`. Removing a team can therefore quietly change which teams are allied.

   Failure scenario: Tag teams on; T0 has no faction set (=0), T1 is set to faction 2, T2 has none (=2), so T1 and T2 are allied. Remove T0: T1 keeps faction 2 but T2 now defaults to 1, and the alliance is gone without the user touching any faction button. The same index fallback in `Game.factionOf` makes it carry into the match.

3. `src/ui/menu.ts:217`: The tag-team toggle pairs `opt.off` ('Off', 'Isključeno') with `title.on` (lowercase 'on', 'upaljen'), a key from the sound status line, so the two labels don't match in case or wording.

   Failure scenario: The setup screen shows 'Off | on' in English and 'Isključeno | upaljen' in Croatian, unlike every other segmented option. It should use a matching options pair (like `WALLED_OPTIONS`) with keys from the same family.

4. `src/app.ts:569`: The test hook's faction `name` is supposed to be null when no custom name exists, but `g.config.factions?.[f] ?? null` returns '' for an unnamed faction, because settings always store four strings.

   Failure scenario: After a reload, `parseSettings` fills `factions` with `['', '', '', '']`, so `__allium.state().factions[i].name` is '' instead of null. An E2E check like `name === null` for an unnamed faction fails or is misread.

5. `src/core/ai.ts:195`: `enemyWeight` rebuilds the rival-team list, sums health over all buddies, runs a second filter and builds a `Set` of factions on every call, and it is called per buddy in `addBlast` for every simulated shot.

   Failure scenario: AI planning scores thousands of candidate blasts per turn; each now pays several array passes plus a `Set` allocation per buddy hit, all with the same result for the whole turn. Compute rivals, faction health and group count once per `planAttack` and pass them in.

6. `src/ui/hud.ts:202`: The faction display-name logic (custom name, else `t('setup.factionNumber')`) is written three times: `app.ts:292-294`, `hud.ts:202-204` and `Menu.factionName`.

   Failure scenario: If the fallback rule changes (e.g. trimming, or a new placeholder key), the three copies drift and HUD, victory screen and setup show different names for the same faction. One shared `factionLabel(config, index)` helper in `src/ui` would replace all three.

7. `src/ui/hud.ts:202`: The HUD works out the faction name (including a `t()` lookup) on every update even when `tagTeams` is off, then throws it away.

   Failure scenario: In every normal match, each HUD update calls `factionOf`, reads `config.factions` and formats a localized string that is never shown. It should only do this inside the `g.config.tagTeams` branch.

8. `src/core/stats.ts:191`: The friendly-fire check is more convoluted than it needs to be. `roster()` always sets `faction` from `factionOf`, which returns the team index when tag teams are off, so the `!== undefined` guard and the separate same-team test are redundant.

   Failure scenario: A reader can't tell when `faction` can be undefined (it never is from `Game`). The check is just `culpritTeam >= 0 && roster.teams[culpritTeam].faction === roster.teams[victim.team].faction`.

9. `src/core/game.ts:293`: The faction-slot limit `4` is hard-coded separately in `Game.factionOf`, `parseTeam` (`settings.ts:184`), `parseSettings` and three `Array.from({ length: 4 })` calls in the menu, with no shared constant.

   Failure scenario: If the team or faction maximum changes, one copy is easily missed. For example, the menu offers a fifth faction that `factionOf` silently treats as 'own team', so allies the user picked are not allied in the match.
