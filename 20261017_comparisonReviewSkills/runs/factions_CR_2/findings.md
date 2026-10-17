The review covers commit 99fbe2e (tag-team factions) against HEAD~1. I found 9 issues: three correctness bugs first, then cleanup and efficiency. None of them were verified by a separate pass.

9 findings, most severe first:

1. `src/core/ai.ts:461`: AI melee scoring never subtracts damage to allies, yet Game.melee hits every living buddy within reach, allies of any team included.

   Failure scenario: Tag teams on, an allied buddy from another team stands next to the enemy the AI is punching. planAttack scores the bat or punch on the enemy alone. Game.melee then hits and launches both, so the AI keeps swatting its ally. Unlike the shotgun and minigun paths, which now go through clearShot, this path has no FRIEND_WEIGHT penalty.

2. `src/core/ai.ts:410`: The torch and drill attack plans only check rock (lineOfSight) and enemy distance, never allied buddies on the tunnel path, so allies are not avoided there either.

   Failure scenario: An allied buddy stands between the AI and an enemy behind a wall. The torch plan scores full enemy damage and burns through the ally on the way, with no friendly penalty.

3. `src/core/stats.ts:218`: died() credits a kill to anyone who kills a buddy other than themselves, so killing an ally from another team counts as a kill, while damaged() books the same damage as friendly fire.

   Failure scenario: Team A blows up allied team B's last buddy. A's scoreboard shows the damage as friendly and dealt=0, but kills=1. The new faction-aware 'own' check was never applied to kills.

4. `src/ui/menu.ts:612`: A team with no stored faction defaults to its array index (`faction ?? i` in the menu, `team` in Game.factionOf), so removing a team silently moves later teams into other factions.

   Failure scenario: Teams A (default 0), B (explicitly 1), C (default 2). Removing A makes C index 1, so it now defaults to faction 1 and is allied with B without the user choosing it. Writing the faction onto the team at add-team time (or when tag teams are switched on) avoids this.

5. `src/core/ai.ts:195`: enemyWeight now builds rivals, mine and a new Set of factions on every call, and it runs for every buddy in every candidate blast during the AI search; allied()/factionOf re-validate the config on each call.

   Failure scenario: The AI planner scores hundreds of shots times every buddy. Each call allocates several arrays and a Set and calls factionOf many times. Computing a faction array once per Game (or once per planAttack) would remove this hot-path allocation.

6. `src/ui/hud.ts:202`: The 'custom faction name, else t(setup.factionNumber)' fallback is written three times (hud.ts, app.ts:293-294, menu.ts factionName); the HUD also runs it every frame even with tag teams off.

   Failure scenario: Three copies of the same label logic can drift apart. The HUD calls t() and indexes config.factions every frame in matches that have no factions. One shared ui helper that returns early when tagTeams is false fixes both.

7. `src/core/stats.ts:191`: The friendly-fire check is longer than it needs to be: Game.roster() always fills in faction (the team index when tag teams are off), so comparing factions alone gives the same answer.

   Failure scenario: The extra `culpritTeam === victim.team`, `!== undefined` and `>= 0` guards repeat Game.factionOf's job and invite drift. `own = roster.teams[culprit.team]?.faction === roster.teams[victim.team].faction` is the equivalent form.

8. `src/core/game.ts:189`: The faction limit 4 is a magic number repeated in Game.factionOf, parseTeam (settings.ts:184), parseSettings factions length, and the menu's Array.from({ length: 4 }) loops.

   Failure scenario: Raising the limit or changing the faction count in one place but not the others gives a game that accepts different factions than settings or the menu can produce. A shared MAX_FACTIONS constant in match.ts prevents this.

9. `src/app.ts:569`: In the test-hook state, `factions[].name` is `null` only when config.factions is missing; when the faction is simply unnamed it is the empty string '', unlike the HUD and victory screen, which show a default name instead.

   Failure scenario: Settings loaded through parseSettings always contain four '' entries, so __allium.state().factions[i].name is '' rather than null or the displayed 'Faction N'. E2E checks that expect null or the shown label behave inconsistently.

---
Final text:
The review covers commit 99fbe2e (tag-team factions) against HEAD~1. I found 9 issues: three correctness bugs first, then cleanup and efficiency. None of them were verified by a separate pass.

9 findings, most severe first:

1. `src/core/ai.ts:461`: AI melee scoring never subtracts damage to allies, yet Game.melee hits every living buddy within reach, allies of any team included.

   Failure scenario: Tag teams on, an allied buddy from another team stands next to the enemy the AI is punching. planAttack scores the bat or punch on the enemy alone. Game.melee then hits and launches both, so the AI keeps swatting its ally. Unlike the shotgun and minigun paths, which now go through clearShot, this path has no FRIEND_WEIGHT penalty.

2. `src/core/ai.ts:410`: The torch and drill attack plans only check rock (lineOfSight) and enemy distance, never allied buddies on the tunnel path, so allies are not avoided there either.

   Failure scenario: An allied buddy stands between the AI and an enemy behind a wall. The torch plan scores full enemy damage and burns through the ally on the way, with no friendly penalty.

3. `src/core/stats.ts:218`: died() credits a kill to anyone who kills a buddy other than themselves, so killing an ally from another team counts as a kill, while damaged() books the same damage as friendly fire.

   Failure scenario: Team A blows up allied team B's last buddy. A's scoreboard shows the damage as friendly and dealt=0, but kills=1. The new faction-aware 'own' check was never applied to kills.

4. `src/ui/menu.ts:612`: A team with no stored faction defaults to its array index (`faction ?? i` in the menu, `team` in Game.factionOf), so removing a team silently moves later teams into other factions.

   Failure scenario: Teams A (default 0), B (explicitly 1), C (default 2). Removing A makes C index 1, so it now defaults to faction 1 and is allied with B without the user choosing it. Writing the faction onto the team at add-team time (or when tag teams are switched on) avoids this.

5. `src/core/ai.ts:195`: enemyWeight now builds rivals, mine and a new Set of factions on every call, and it runs for every buddy in every candidate blast during the AI search; allied()/factionOf re-validate the config on each call.

   Failure scenario: The AI planner scores hundreds of shots times every buddy. Each call allocates several arrays and a Set and calls factionOf many times. Computing a faction array once per Game (or once per planAttack) would remove this hot-path allocation.

6. `src/ui/hud.ts:202`: The 'custom faction name, else t(setup.factionNumber)' fallback is written three times (hud.ts, app.ts:293-294, menu.ts factionName); the HUD also runs it every frame even with tag teams off.

   Failure scenario: Three copies of the same label logic can drift apart. The HUD calls t() and indexes config.factions every frame in matches that have no factions. One shared ui helper that returns early when tagTeams is false fixes both.

7. `src/core/stats.ts:191`: The friendly-fire check is longer than it needs to be: Game.roster() always fills in faction (the team index when tag teams are off), so comparing factions alone gives the same answer.

   Failure scenario: The extra `culpritTeam === victim.team`, `!== undefined` and `>= 0` guards repeat Game.factionOf's job and invite drift. `own = roster.teams[culprit.team]?.faction === roster.teams[victim.team].faction` is the equivalent form.

8. `src/core/game.ts:189`: The faction limit 4 is a magic number repeated in Game.factionOf, parseTeam (settings.ts:184), parseSettings factions length, and the menu's Array.from({ length: 4 }) loops.

   Failure scenario: Raising the limit or changing the faction count in one place but not the others gives a game that accepts different factions than settings or the menu can produce. A shared MAX_FACTIONS constant in match.ts prevents this.

9. `src/app.ts:569`: In the test-hook state, `factions[].name` is `null` only when config.factions is missing; when the faction is simply unnamed it is the empty string '', unlike the HUD and victory screen, which show a default name instead.

   Failure scenario: Settings loaded through parseSettings always contain four '' entries, so __allium.state().factions[i].name is '' rather than null or the displayed 'Faction N'. E2E checks that expect null or the shown label behave inconsistently.
