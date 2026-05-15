# Pool Rules — DATA MODUL WM 2026 (Kicktipp)

Source: e-mail from Marco Matthes Jiménez (Junior Project Manager,
DATA MODUL AG), the pool admin. English text only; payment link removed.

## What & how

- **Tournament**: 2026 FIFA World Cup in Mexico / USA / Canada.
- **Platform**: Kicktipp group (link is sent by the admin after stake is paid).
- **Stake**: 10 €.
- **Registration deadline**: **09 June 2026** (send admin a screenshot
  of the transfer + your "tipp name").
- **External tippers are not allowed** — DATA MODUL only.

## Scoring per match

You predict the result **after 90 minutes** (no extra time / penalties),
for every match from group stage through to the final.

| Outcome you got right | Points |
| --- | --- |
| Correct tendency (W/D/L) | **2** |
| Correct goal difference | **3** |
| Correct exact result | **4** |

> Note: "3" and "4" don't stack — they replace each other. Getting the
> exact result is worth 4, not 4+3+2.

## Bonus tips — 4 points each, lock at first kickoff

These must be submitted **before the opening match** (Thu 11 June 2026,
21:00 CET, Mexico vs South Africa).

1. **Which team has the top scorer?** (one team)
2. **Which four teams reach the semi-finals?** (four teams)
3. **Group winners** — one pick per group, 12 groups (A–L)
4. **World champion** — one team

If you assume max value: bonus pool ≈ 1 + 4 + 12 + 1 = **18 picks × 4 =
72 bonus points** at perfection (in practice you might bank 12–24).

## Prize distribution

| Place | Share of pool |
| --- | --- |
| 1st | **40 %** |
| 2nd | 25 % |
| 3rd | 15 % |
| 4th | 12 % |
| 5th | 8 % |

Tie-break by the kicktipp.de placement system.

## Submission timing

- Each match: at the **latest 1 minute before kickoff**.
- The Kicktipp mobile app is the easiest way.

## E-mail gotcha

If you use a `@data-modul.com` address, the Kicktipp confirmation may
land in your **spam folder** — check there to activate the account.

---

## Strategy deductions

The pool format strongly shapes how I'd play:

1. **Per-match picks dominate the leaderboard, not the bonus picks.**
   104 matches × up to 4 pts = up to 416 per-match points. Bonus is
   ~72 pts max. So your group-stage discipline matters most. Don't
   "waste" the group stage by chasing high-variance scorelines.

2. **Default to chalk on tendency.** With 2 pts for a correct W/D/L,
   the cheapest reliable points come from picking favorites to win in
   mismatches (e.g. Argentina vs Jordan, Spain vs Cabo Verde, Brazil
   vs Haiti). Almost everyone in the pool will pick the same — but
   *missing* these is what loses you the lead.

3. **Pick small scorelines, not blowouts.** Modal World Cup scoreline
   is **1–0** (most common), then **2–1** and **2–0**. Predicting 4–0
   or 3–2 chases the long tail; you lose the goal-difference 3-pointer
   when the favorite wins 2–0 instead. **Always-pick 2–1 for the
   favorite** is a defensible heuristic.

4. **Top 5 all get paid — but the gradient is steep.** 1st (40 %) vs
   5th (8 %) is a 5× difference. Risk-adjusted, mid-table is fine but
   the win is a 5× payout. With ~10–30 colleagues entering, going
   slightly contrarian on **one** high-leverage pick (e.g. champion or
   one semi-finalist) is worth more than safe-chalk everywhere.

5. **The four bonus picks should not all be chalk.** If you pick
   Spain/France/Argentina/Brazil semis + France champion + Spain top
   scorer, you'll match half the office. To outscore them, swap one
   bonus pick for a justified contrarian (Portugal, Germany, or
   England champion; Morocco/Croatia/Colombia semi-finalist).

6. **Bonus is locked at 11 June 21:00 CET.** Lock your bonus picks
   based on final 26-man squads (last is England 22 May, Spain 25 May).
   No revisions after kickoff.

7. **No extra time predictions.** All knockout picks are scores after
   90 minutes — a draw is a fine prediction in a knockout if you think
   it'll go to ET. Just predict the 90-min scoreline.

These deductions flow into [`model_picks.md`](model_picks.md) and the
template in [`my_picks.md`](my_picks.md).
