Base: master @ 9683621   Head: 99fbe2e
Files changed: 21   +423 / -34 lines

**Findings**

```
#1  MEDIUM  Code  src/core/game.ts:293
    A team with no explicit faction falls back to its team index. Both factionOf() and the setup menu's `faction ?? i` use that index, so adding or removing a team can silently change alliances. Example: with teams A(unset→0), B(unset→1), C(explicit 1), removing A shifts B to index 0 and breaks the B+C alliance; a newly added team at index 2 also joins any team that explicitly chose faction 2. Fix: write an explicit `faction` onto every team when tag-teams is turned on and in add-team/remove-team (src/ui/menu.ts:611), so membership never depends on position in the list.
```

```
#2  LOW  Architecture  src/ui/hud.ts:204
    The fallback name "custom name, else Faction {n}" is written out separately in hud.ts:204, app.ts:294 and menu.ts:148. The valid-slot rule (integer, 0–3) is also repeated in game.ts:293, settings.ts:184 and the menu's hard-coded `length: 4`. Fix: keep one `factionName(config, faction)` helper and one `MAX_FACTIONS` constant next to `TeamConfig` in match.ts, so the HUD, victory screen and setup cannot drift apart.
```

**Verdict**

The branch can be merged as it stands. #1 is a real but visible setup-screen defect (the faction buttons show the shifted choice), worth fixing before or soon after the merge. Nothing blocks.

---
Final text:
Base: master @ 9683621   Head: 99fbe2e
Files changed: 21   +423 / -34 lines

**Findings**

```
#1  MEDIUM  Code  src/core/game.ts:293
    A team with no explicit faction falls back to its team index. Both factionOf() and the setup menu's `faction ?? i` use that index, so adding or removing a team can silently change alliances. Example: with teams A(unset→0), B(unset→1), C(explicit 1), removing A shifts B to index 0 and breaks the B+C alliance; a newly added team at index 2 also joins any team that explicitly chose faction 2. Fix: write an explicit `faction` onto every team when tag-teams is turned on and in add-team/remove-team (src/ui/menu.ts:611), so membership never depends on position in the list.
```

```
#2  LOW  Architecture  src/ui/hud.ts:204
    The fallback name "custom name, else Faction {n}" is written out separately in hud.ts:204, app.ts:294 and menu.ts:148. The valid-slot rule (integer, 0–3) is also repeated in game.ts:293, settings.ts:184 and the menu's hard-coded `length: 4`. Fix: keep one `factionName(config, faction)` helper and one `MAX_FACTIONS` constant next to `TeamConfig` in match.ts, so the HUD, victory screen and setup cannot drift apart.
```

**Verdict**

The branch can be merged as it stands. #1 is a real but visible setup-screen defect (the faction buttons show the shifted choice), worth fixing before or soon after the merge. Nothing blocks.
