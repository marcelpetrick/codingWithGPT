# Pool Rules — DATA MODUL WM 2026 (Kicktipp)

Source: pool admin e-mail **+** verbatim Kicktipp "Spielregeln" page
(user paste 2026-05-19, confirmed). Participant count updated
2026-06-09 from user message.

## What & how

- **Tournament**: 2026 FIFA World Cup in Mexico / USA / Canada.
- **Platform**: Kicktipp group (link is sent by the admin after stake is paid).
- **Stake**: 10 €.
- **Registration deadline**: **09 June 2026, 23:59** (send admin a
  screenshot of the transfer + your "tipp name"). Confirmed via admin
  reminder e-mail on 2026-06-02.
- **External tippers are not allowed** — company-internal pool.
- **Participant count (updated 2026-06-18)**: **35 tippers** ⇒
  pool = 35 × 10 € = **350 €**.

## Visibility (Sichtbarkeit der Tipps)

Tips are **hidden** until the tipp window closes. You can't see what
others tipped before kickoff — no real-time contrarian moves possible.

## Tipp mode (Tippmodus)

Two declarations on the rules page:

1. **"Es wird das genaue Ergebnis getippt"** — predict the exact score.
2. **"Es wird das Ergebnis '90 Minuten' getippt"** — the result is
   taken **after 90 minutes** (no extra time, no penalties).

⇒ **For every match (group + knockout) you predict the 90-minute
exact score.** A 1–1 prediction for a knockout that goes to ET is a
*valid* prediction — Kicktipp uses the 90-minute result.

## Scoring per match (Punkteregel: 2 – 4 Punkte)

|              | Tendency (Tendenz) | Goal-diff (Tordifferenz) | Exact result (Ergebnis) |
| ---          | --- | --- | --- |
| **Win**      | **2** | **3** | **4** |
| **Draw**     | **2** | — | **4** |

- Correct **tendency** (W/D/L) = **2 pts**.
- Correct **goal difference** (and tendency) = **3 pts**.
- Correct **exact result** = **4 pts**.
- These do **not** stack — getting the exact result is worth 4, not 4+3+2.

For a draw there's no separate goal-diff bonus (a draw has 0 GD by
definition) — it's either 2 pts (any draw) or 4 pts (exact draw).

## Bonus picks — 4 points each (Punkteregel: 4 Punkte)

> **Punkte pro richtiger Antwort: 4. Reihenfolge hat keine Bedeutung.**
> 4 pts per correct answer; order does not matter (relevant for the
> semi-finalist question).

These must be submitted **before the opening match** (Thu 11 June 2026,
21:00 CET, Mexico vs South Africa).

1. **Which team has the top scorer?** (one team)
2. **Which four teams reach the semi-finals?** (four teams, any order)
3. **Group winners** — one pick per group, 12 groups (A–L)
4. **World champion** — one team

If you assume max value: 1 + 4 + 12 + 1 = **18 picks × 4 = 72 bonus
points** at perfection (in practice you might bank 12–24).

## Tip lock (Tippabgaberegel)

**1 minute Vorlaufzeit** — tip window closes **1 minute before
kickoff**. The Kicktipp mobile app is the easiest way to submit on
match day.

## Tie-break (Punktegleichstand)

If two tippers finish equal on total points, the tie-break is the
**number of matchday wins** (*Spieltagssiege*) — i.e. how many
individual matchdays you finished as the top scorer of the pool.

> Note (clarification 2026-05-19): the previous version of this file
> said "kicktipp.de placement system". The actual rule on the page
> is **Anzahl der Spieltagssiege** — winning matchdays.

**Implication**: matching the modal pool score in the long run still
ranks you in the middle. To climb on the tie-break ladder you want
**occasional matchday-wins** — i.e. one or two days where your sheet
beats almost everyone. A pure-chalk sheet won't generate matchday
wins on the days the chalk loses.

## Prize distribution

| Place | Share of pool |
| --- | --- |
| 1st | **40 %** |
| 2nd | 25 % |
| 3rd | 15 % |
| 4th | 12 % |
| 5th | 8 % |

## E-mail gotcha

If you registered with a company e-mail address, the Kicktipp
confirmation may land in your **spam folder** — check there to activate
the account.

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
   the win is a 5× payout. At the **updated 35 participants**, top-5
   is top 14.3 % of the field — the cash-out floor is real (5th = +€18
   net), so safe chalk has positive EV. Under the locked Strategy A, do
   not turn the bonus sheet contrarian just because the pool grew.

5. **Bonus picks stay chalk under Strategy A.** France/Spain/Argentina/
   Brazil semis + France champion + France top-scorer team is not built
   to beat everyone on bonus uniqueness; it is built to avoid donating
   4-point bonus edges to the field.

6. **Tie-break = matchday wins.** This rewards *occasional* sharp
   matchdays. Pure chalk every day rarely wins a matchday outright —
   the matchday winner usually nails one or two upsets. Under Strategy A,
   treat this as upside you may lose, not a reason to add forced swings.

7. **Bonus is locked at 11 June 21:00 CET.** Lock your bonus picks
   based on final 26-man squads (last submissions due 01 June). No
   revisions after kickoff.

8. **No extra time predictions.** All picks (group + knockout) are
   scores after 90 minutes — a draw is a fine prediction in a
   knockout if you think it'll go to ET. Just predict the 90-min
   scoreline.

These deductions flow into [`model_picks.md`](model_picks.md) and the
template in [`my_picks.md`](my_picks.md).
