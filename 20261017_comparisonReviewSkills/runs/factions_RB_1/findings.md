Base: master @ 9683621   Head: 99fbe2e
Files changed: 21   +423 / -34 lines

**Findings**

```
#1  LOW  Code  src/ui/menu.ts:611
    A team with no faction set falls back to its position in the list (`cfg.faction ?? i` here and in `alliedOnly`, `?? team` in `Game.factionOf`), and position numbers are also real faction slots. So removing a team silently moves every team after it into a different faction: in A(default), B(default), C(set to Faction 2), removing A drops B into slot 0 and breaks B's alliance with C. Adding a team can likewise join a slot someone already picked. Store the faction on the team when tag-teams is switched on and in `add-team`/`remove-team`, so membership never depends on list position.
```

```
#2  LOW  Architecture  src/app.ts:293
    The rule "custom faction name, otherwise the translated `Faction n`" is written out three times: here, in `src/ui/hud.ts:203-204` and in `Menu.factionName` (`src/ui/menu.ts:146`). The HUD and victory screen also each check `tagTeams` and `config.factions` on their own. Put one `factionLabel(config, faction)` helper in `src/ui` so a change to the naming or the fallback can't leave the HUD and the victory screen disagreeing.
```

I checked the rest of the faction logic and found no other problems:
- **Win check:** the victory test (one faction left), the draw case and `winnerTeams` (which also lists allies knocked out earlier) are correct.
- **AI:** every former same-team comparison now uses `allied()`. That covers enemy lists, blast tallies, mine and self-destruct friend checks, flying-sheep targeting and `clearShot`.
- **Homing lock:** it rejects allies, matching the AI's target list.
- **Stats:** the friendly-fire check works both with and without tag-teams.
- **Saved settings and Start button:** loading validates saved factions, and the Start guard is enforced on the button and in the click handler.

**Verdict**

The branch can be merged as it is. Neither finding blocks it; #1 is worth fixing soon because it can quietly change alliances while the player edits the setup.

---
Final text:
Base: master @ 9683621   Head: 99fbe2e
Files changed: 21   +423 / -34 lines

**Findings**

```
#1  LOW  Code  src/ui/menu.ts:611
    A team with no faction set falls back to its position in the list (`cfg.faction ?? i` here and in `alliedOnly`, `?? team` in `Game.factionOf`), and position numbers are also real faction slots. So removing a team silently moves every team after it into a different faction: in A(default), B(default), C(set to Faction 2), removing A drops B into slot 0 and breaks B's alliance with C. Adding a team can likewise join a slot someone already picked. Store the faction on the team when tag-teams is switched on and in `add-team`/`remove-team`, so membership never depends on list position.
```

```
#2  LOW  Architecture  src/app.ts:293
    The rule "custom faction name, otherwise the translated `Faction n`" is written out three times: here, in `src/ui/hud.ts:203-204` and in `Menu.factionName` (`src/ui/menu.ts:146`). The HUD and victory screen also each check `tagTeams` and `config.factions` on their own. Put one `factionLabel(config, faction)` helper in `src/ui` so a change to the naming or the fallback can't leave the HUD and the victory screen disagreeing.
```

I checked the rest of the faction logic and found no other problems:
- **Win check:** the victory test (one faction left), the draw case and `winnerTeams` (which also lists allies knocked out earlier) are correct.
- **AI:** every former same-team comparison now uses `allied()`. That covers enemy lists, blast tallies, mine and self-destruct friend checks, flying-sheep targeting and `clearShot`.
- **Homing lock:** it rejects allies, matching the AI's target list.
- **Stats:** the friendly-fire check works both with and without tag-teams.
- **Saved settings and Start button:** loading validates saved factions, and the Start guard is enforced on the button and in the click handler.

**Verdict**

The branch can be merged as it is. Neither finding blocks it; #1 is worth fixing soon because it can quietly change alliances while the player edits the setup.
