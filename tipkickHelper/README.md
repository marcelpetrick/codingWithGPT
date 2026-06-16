# tipkickHelper — FIFA World Cup 2026 Prediction Pool

Research notes and data-driven picks for the **DATA MODUL WM 2026**
Kicktipp pool. Tournament runs **11 June – 19 July 2026** across USA,
Canada, Mexico.

> Status as of 2026-06-09 (2 days to kick-off). Final draw was held
> **5 Dec 2025**, Washington, D.C. Pool entry deadline: **09 June 2026, 23:59**.
> Confirmed **29 participants** (pool €290). Bonus picks lock at the opening
> kickoff: **11 June 2026, 21:00 CET** (Mexico vs South Africa).
>
> **User status (2026-06-02): registered, paid, picks already submitted
> in the Kicktipp app.** This repo is in archive/monitor mode —
> future edits only on forced deviations (injuries/suspensions).
>
> **Latest monitoring update (2026-06-09):** 29 tippers confirmed. France
> beat Northern Ireland 3–1; Mbappé played the full match and Saliba started.
> Spain beat Peru 3–1 without Yamal/Nico Williams. June 9 Kalshi group market
> makes Switzerland the Group B favorite over Canada, so the Group B bonus
> default changes Canada → Switzerland.

## Where to put YOUR picks

Edit [`my_picks.md`](my_picks.md). That file is the only one meant to be
filled in by you. Everything else is research, rules, and model output.

The pool's actual entry happens **inside the Kicktipp app**, but
`my_picks.md` is the scratch sheet to organise your picks before you
copy them in.

## File index

| File | What's inside |
| --- | --- |
| [`pool_rules.md`](pool_rules.md) | **The Kicktipp pool rules + strategy deductions** |
| [`strategy.md`](strategy.md) | **Cash-out math at 29 participants + Strategy A vs B** |
| [`AGENTS.md`](AGENTS.md) | Agent / workflow guide for future agent sessions |
| [`format.md`](format.md) | New 48-team / 12-group format, schedule, host venues |
| [`groups.md`](groups.md) | All 12 groups A–L with quick reads per team |
| [`favorites.md`](favorites.md) | Top 8 contenders, odds, coach, form, key risks |
| [`hosts.md`](hosts.md) | USA, Canada, Mexico — home advantage analysis |
| [`dark_horses.md`](dark_horses.md) | Morocco, Croatia, Uruguay, Colombia, Portugal |
| [`model_picks.md`](model_picks.md) | My data-driven prediction — bonus picks, group winners, R32, R16, QF, SF, F, winner |
| [`my_picks.md`](my_picks.md) | **YOUR pick sheet** — fill this in |
| [`explanation.md`](explanation.md) | Mermaid diagrams: how the research process works end-to-end |
| [`sources.md`](sources.md) | Links used as evidence |
| [`task_inventory_20260616.md`](task_inventory_20260616.md) | Auditable task list for the 2026-06-16 review loop |

## How to use this

1. Read [`pool_rules.md`](pool_rules.md) first — it explains the
   Kicktipp scoring (2/3/4 points), the 4 bonus picks worth 4 pts each,
   and the strategy deductions that flow from them.
2. Read [`favorites.md`](favorites.md) and [`hosts.md`](hosts.md) —
   they cover ~80% of the plausible winners.
3. Skim [`groups.md`](groups.md) to see which heavyweights might trip
   in the group stage (it changes the bracket math).
4. Compare against [`model_picks.md`](model_picks.md) — the data-driven
   baseline including bonus picks and per-match scoreline heuristics.
5. Adjust only for forced news (injury, suspension, weather) while
   staying inside Strategy A.
6. Write your final answers into [`my_picks.md`](my_picks.md), then copy
   them into the Kicktipp app.

## A note on "data-driven"

The model picks lean on betting markets (sharper than punditry over
large samples), ESPN/Goal power rankings, recent form, coach quality,
and host-nation effects. They are **not** a guarantee — the World Cup
is high-variance. A bookmaker's 17 % top-of-market favorite still has
an 83 % chance of *not* winning.

Pool strategy here is shaped by the **5-place payout** (40/25/15/12/8 %)
and the per-match 2/3/4 scoring — see [`pool_rules.md`](pool_rules.md)
for the full deduction. Short version: default to **chalk** and only
change picks when new information changes the favorite.
