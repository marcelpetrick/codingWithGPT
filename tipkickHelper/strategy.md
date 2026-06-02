# Strategy — How to actually play this pool

## Rule clarification — 2026-05-19

The user pasted the verbatim Kicktipp Spielregeln page. Confirmed:

- Scoring is **flat 2 / 3 / 4** (tendency / GD / exact) — as originally
  documented.
- Tipps are **90-minute results** (no ET, no penalties) — group AND
  knockout.
- Tip lock: **1 minute before kickoff**.
- Bonus picks: **4 pts each, order doesn't matter**.
- **Tie-break = number of matchday wins (Spieltagssiege)** — *new*
  vs the previous note that said "kicktipp.de placement system".

The tie-break clarification is the only material change. Implication:
pure chalk rarely wins a single matchday outright (the matchday winner
usually nailed an upset or two), so under perfect Strategy A you'll
land **mid-table on tie-break** if you're equal on points. The
locked Strategy A still holds for the *primary* goal (top-5 cash-out)
because tie-break only matters in ties, but it shaves a sliver off
the 1st-place equity. Documented; no strategy change.

## The pool sizing math

**Confirmed 2026-06-02**: **25 participants**. Each pays €10 → **pool
= €250**.

| Place | Share | Payout | Net (after −€10 stake) |
| --- | --- | --- | --- |
| 1st | 40 % | €100 | **+€90** |
| 2nd | 25 % | €62.50 | **+€52.50** |
| 3rd | 15 % | €37.50 | **+€27.50** |
| 4th | 12 % | €30 | **+€20** |
| 5th | 8 % | €20 | **+€10** |
| 6th–25th | 0 % | €0 | **−€10** |

**To cash out at all you need top-5 of 25** — i.e. the top **20 %**
of the field. Even **5th place doubles the stake** (+€10 net). This
is a much easier floor than the original 50-tipper assumption (top
10 %), which raises the cash-out probability of pure chalk play.

## What "cash out" probability actually requires

At **N = 25** the bar is the top 20 %. An above-median diligent
Kicktipp player should land top-5 of 25 roughly **55–65 %** of the
time, because:

- ~half the participants are casuals (random picks) — easy to beat.
- ~25 % are mid-engaged (chalk picks, no edge) — beatable with diligence.
- ~15 % are sharper than you on a given week.
- ~10 % land lucky on a high-variance bonus pick.

Out of 25, that's ~13 casuals + ~6 chalk-only + ~4 sharper + ~2
lucky-variance players. Your goal is to consistently outperform the
~19 casuals + chalk-only players. The sharper minority is hard to
beat reliably; ride variance.

## Two strategies — pick one before 11 June

### Strategy A — "Safe / Cash Out" (target: top 5)

> The goal is **at least €20 back** (5th place at N=25) with high
> probability — i.e. doubling the €10 stake. You give up some upside
> at 1st place. Recommended if you mostly want not to lose your €10.

**Rules**:

- Pick the **chalk** on every match — favorite to win, modal scoreline.
- For bonus picks, pick **4 consensus** semi-finalists (France, Spain,
  Argentina, Brazil) and **France** as champion. Yes, half the office
  will too — but you only need to *not lose* to them, and getting all
  4 semi-finalists is worth 16 pts that they'll also have.
- Goal of the strategy: rank consistently **above the median** by
  banking 90 %+ tendency points and a healthy share of GD/exact-result
  points.
- Per-match scorelines: always **2–1, 1–0, 2–0, or 1–1**. These four
  scorelines historically cover ~55 % of all World Cup match outcomes.
  Picking 2–1 for the favorite is the highest-EV per-match scoreline.

**Estimated finish range (at N=25)**: 2nd – 9th place (median ~5th).
**Cash-out probability (at N=25)**: ~55–65 %.

### Strategy B — "Swing / Win It" (target: 1st)

> The goal is **€100** (1st place at N=25). You accept that you might
> finish mid-table on most simulation runs in exchange for a real
> chance at the big prize.

**Rules**:

- Match A's per-match scoreline play (chalk on tendency, modal
  scorelines) — **don't over-cleverize the group stage**.
- Take **one** contrarian leverage bet — exactly one. Two examples
  (counts scaled to **N=25**):
  - **Champion = Portugal** (~+1000 implied 8 %; only ~1–2 of 25 will
    pick this). Adds 4 bonus pts if right and big positional swing.
  - **Semi-finalist swap: Brazil → Croatia or Morocco**. ~3–4 of 25
    will have Brazil; ≤2 will have Croatia/Morocco. If Croatia makes
    semis, you bank a 4-pt edge and a tiebreaker advantage.
- Don't take *both* — the variance compounds and you tank your floor.

**Estimated finish range (at N=25)**: 1st – 18th (bimodal).
**Cash-out probability (at N=25)**: ~45–55 %.
**1st-place probability (at N=25)**: ~8–12 % (vs. ~5–7 % under
Strategy A).

### Why not "all contrarian"?

The temptation: "pick Germany as champion, Morocco/Croatia/Egypt/Japan
as semis, win the big prize." Math says no:
- Germany champion: ~6 % implied. You'd need ~7× implied odds to make
  it +EV in the office (top-5 finish probability shifts toward 0 if
  the contrarian misses).
- Hitting 2+ contrarian bonuses is roughly 1 % — way below the ~10 %
  baseline you need to be top-5.

**Don't go all-in on contrarian. Pick exactly one swing.**

## How participant count shifts the math

**Confirmed**: **25 participants** (admin reminder, 2026-06-02). For
reference, here's how the threshold scales:

| Participants | Top-5 = top X % | Strategy implication |
| --- | --- | --- |
| 13 | top 38 % | Below 13 even 5th place loses money. |
| 20 | top 25 % | Safe play almost guaranteed cash-out. Go pure chalk. |
| **25** | **top 20 %** | **Pure chalk has positive EV; one swing optional for the 1st-place lottery.** |
| 30 | top 17 % | Slight contrarian advantage; still mostly chalk. |
| 50 | top 10 % | Recommended split: A or B. |
| 80 | top 6 % | Strategy B (one swing pick) becomes mandatory. |
| 100+ | top 5 % | Two swing picks become defensible — but tank floor. |

**Note**: at N=25, 5th place = +€10 (doubles stake). The cash-out
floor is now meaningful — Strategy A's "don't lose money" objective
is achievable with high probability under pure chalk.

## Operational checklist

- [ ] **By 09 Jun 2026, 23:59**: register, pay 10 €, send screenshot
      + tipp name to admin. Activate Kicktipp confirmation (check spam
      folder if you used a company e-mail address).
- [ ] **By 11 Jun 2026, 21:00 CET**: lock bonus picks in Kicktipp.
- [ ] **From 11 Jun 2026 daily**: enter each match's score in Kicktipp
      ≥1 min before kickoff. The app is more convenient than browser.
- [ ] **Don't forget knockout-stage** picks: 32 + 16 + 8 + 4 + 1 + 1 = 62
      additional matches.

## Final recommendation

**Strategy A** (safe cash-out) is what the user asked for ("at least
get our money back").

## 🔒 Decision — Strategy A is LOCKED (decided 2026-05-15)

The user chose Strategy A on 2026-05-15. This is the final strategy
and will not be reconsidered.

### Pool-size update — 2026-06-02 (does NOT unlock the strategy)

Confirmed N=25 (not the 50 assumed at locking time). The smaller pool
makes Strategy A's cash-out *easier* (top 20 % instead of top 10 %),
so the lock is reinforced, not weakened: 5th place now nets +€10,
4th nets +€20 — pure chalk is comfortably positive EV. No reason to
override the lock.

**Locked picks (bonus, A-set)**:
- Top-scorer team → **France**
- Semi-finalists → **France, Spain, Argentina, Brazil**
- Champion → **France**
- Group winners → all 12 bookmaker favorites (see `my_picks.md`)
- Per-match scorelines → chalk favorite, modal scoreline (2–1, 1–0,
  2–0, 1–1) — see `my_picks.md` for the full group-stage scratch sheet

### Rule: no mid-tournament strategy switch

Strategy A is the playbook from now through the final on 19 July 2026.
Forbidden moves:

- ❌ Swapping a bonus pick after the opening kickoff (11 Jun 21:00 CET
  is the lock anyway — Kicktipp won't let you).
- ❌ Mid-tournament panic moves: e.g. switching to high-variance
  scorelines because "I'm in 10th place after matchday 2". The pool
  is decided after **104 matches**, not 24 — variance regresses.
- ❌ "Strategy A with a B exception just this once" — the whole point
  of locking is to defeat that voice.

Allowed:

- ✅ Per-match picks change game by game (they have to — different
  fixtures every day).
- ✅ Adapting the **default pick** when info changes (injury, red-
  card suspension, weather) — but stay within the chalk philosophy.
- ✅ Bringing in new info between now and 11 June and letting it
  refine the bonus picks **before** lockout.

### When you might reconsider

Not during this tournament. If after the World Cup you want to evaluate
whether Strategy A or B was the better choice in hindsight, that's
fine — but it's a post-mortem, not a live correction.
