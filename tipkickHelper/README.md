# tipkickHelper — FIFA World Cup 2026 Prediction Pool

Research notes and data-driven picks for a company-internal **WM 2026**
Kicktipp pool. Tournament runs **11 June – 19 July 2026** across USA,
Canada, Mexico.

> **Status as of 2026-07-17 — final matchday.** Final draw held
> **5 Dec 2025**, Washington, D.C.; pool entry closed **09 June 2026,
> 23:59**. 35 participants (pool €350). Bonus picks locked 11 June 2026, 21:00 CET.
>
> **Current position: 4th / 35 · 224 pts** (leader at 234, −10; podium is 2nd
> at 229 / 3rd at 227; tied with 5th at 224 but **ahead on the best Spieltagssiege
> tie-break in the pool, 1.83**). 1st is out of reach.
>
> **ST14 (Halbfinale) complete: 0/16 pts.** Both favourites lost: France 0–2
> Spain, England 1–2 Argentina — our `1:0` and `1:1` both scored 0. **France's
> exit killed our Champion bonus (dead) and flipped the top-scorer race to Messi**
> (8g/4a > Mbappé 8g/3a) — the +8 France double-bonus path to 1st is gone.
>
> **Final matchday (ST15) picks:** `2:1` Frankreich–England (Bronze, lock 18.07
> ~22:59 CET) · `2:1` Spanien–Argentinien (Finale, lock 19.07 ~20:59 CET).
> Switch the final to `1:2` Argentina only if the bonus scout shows rivals
> ahead hold a live champion pick.
>
> See [`review_20260717.md`](review_20260717.md) for the full final-matchday analysis.

## Live Pick Workflow

Use [`my_picks.md`](my_picks.md) as the submitted-pick record. Do not
rewrite it casually during the tournament. Use
[`pick_adjustment_watchlist.md`](pick_adjustment_watchlist.md) to see
which future lines need review before entry.

The pool's actual entry happens **inside the Kicktipp app**, but
`my_picks.md` is the local audit sheet for what was or should be entered.

## File index

| File | What's inside |
| --- | --- |
| [`pool_rules.md`](pool_rules.md) | **The Kicktipp pool rules + strategy deductions** |
| [`strategy.md`](strategy.md) | **Cash-out math at 35 participants + Strategy A vs B** |
| [`AGENTS.md`](AGENTS.md) | Agent / workflow guide for future agent sessions |
| [`format.md`](format.md) | New 48-team / 12-group format, schedule, host venues |
| [`groups.md`](groups.md) | All 12 groups A–L with quick reads per team |
| [`favorites.md`](favorites.md) | Top 8 contenders, odds, coach, form, key risks |
| [`hosts.md`](hosts.md) | USA, Canada, Mexico — home advantage analysis |
| [`dark_horses.md`](dark_horses.md) | Morocco, Croatia, Uruguay, Colombia, Portugal |
| [`model_picks.md`](model_picks.md) | My data-driven prediction — bonus picks, group winners, R32, R16, QF, SF, F, winner |
| [`my_picks.md`](my_picks.md) | **YOUR pick sheet** — fill this in |
| [`prediction_timeline.md`](prediction_timeline.md) | Chronological pick-vs-result audit through current results |
| [`pick_adjustment_watchlist.md`](pick_adjustment_watchlist.md) | Current "review before entry" queue for future picks |
| [`StrategyReview20260613.md`](StrategyReview20260613.md) | Superseded early in-tournament review; kept for audit history |
| [`StrategyReview20260616.md`](StrategyReview20260616.md) | Dated performance review after matches through 15 June 2026 |
| [`review_20260705.md`](review_20260705.md) | ST11 R32 scorecard (34 pts), ST12 R16 picks locked |
| [`review_20260706.md`](review_20260706.md) | ST12 partial (Brazil–Norway + Mexico–England), standings update |
| [`review_20260708.md`](review_20260708.md) | ST12 complete (8/32 pts), ST13 QF picks, QF odds + injury brief |
| [`review_20260713.md`](review_20260713.md) | ST13 complete (6/16), 3rd @ 224, SF picks + whole-race math |
| [`review_20260717.md`](review_20260717.md) | **ST14 complete (0/16), 4th @ 224, France bonus dead, final + bronze picks** |
| [`form_perspective_20260713.md`](form_perspective_20260713.md) | **Full-tournament form logs of all 4 semifinalists + fallen-team lessons** |
| [`explanation.md`](explanation.md) | Mermaid diagrams: how the research process works end-to-end |
| [`sources.md`](sources.md) | Links used as evidence |
| [`task_inventory_20260616.md`](task_inventory_20260616.md) | Auditable task list for the 2026-06-16 review loop |
| `Screenshot_*.png` | Kicktipp screenshots (Spieltag entries, bonus picks, R16, QF) |

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
6. When you paste your current Kicktipp state later, compare it against
   [`pick_adjustment_watchlist.md`](pick_adjustment_watchlist.md) and
   mark each line `OK`, `Review`, or `Off`.

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
