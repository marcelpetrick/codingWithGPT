# Strategy — How to actually play this pool

## The pool sizing math

Assume **50 participants** (the user's best current estimate). Each
pays €10 → **pool = €500**.

| Place | Share | Payout | Net (after −€10 stake) |
| --- | --- | --- | --- |
| 1st | 40 % | €200 | **+€190** |
| 2nd | 25 % | €125 | **+€115** |
| 3rd | 15 % | €75 | **+€65** |
| 4th | 12 % | €60 | **+€50** |
| 5th | 8 % | €40 | **+€30** |
| 6th–50th | 0 % | €0 | **−€10** |

**To cash out at all you need top-5 of 50** — i.e. the top **10 %**
of the field. That's the headline target.

## What "cash out" probability actually requires

If you played fully optimally (impossible) you'd hit top 10 % almost
every time. In practice, even an **above-median Kicktipp player**
finishes top-5 of 50 maybe **20–30 %** of the time, because:

- ~half the participants are casuals (random picks) — easy to beat.
- ~25 % are mid-engaged (chalk picks, no edge) — beatable with diligence.
- ~15 % are sharper than you on a given week.
- ~10 % land lucky on a high-variance bonus pick.

Your goal is to consistently outperform the ~37 casuals + chalk-only
players. The sharper minority is hard to beat reliably; ride variance.

## Two strategies — pick one before 11 June

### Strategy A — "Safe / Cash Out" (target: top 5)

> The goal is **at least €40 back** (5th place) with high probability.
> You give up some upside at 1st place. Recommended if you mostly want
> not to lose your €10.

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

**Estimated finish range**: 4th – 12th place (median ~8th).
**Cash-out probability**: ~30 %.

### Strategy B — "Swing / Win It" (target: 1st)

> The goal is **€200** (1st place). You accept that you might finish
> mid-table on most simulation runs in exchange for a real chance at
> the big prize.

**Rules**:

- Match A's per-match scoreline play (chalk on tendency, modal
  scorelines) — **don't over-cleverize the group stage**.
- Take **one** contrarian leverage bet — exactly one. Two examples:
  - **Champion = Portugal** (~+1000 implied 8 %; only ~2–4 of 50 will
    pick this). Adds 4 bonus pts if right and big positional swing.
  - **Semi-finalist swap: Brazil → Croatia or Morocco**. ~5–8 of 50
    will have Brazil; <5 will have Croatia/Morocco. If Croatia makes
    semis, you bank a 4-pt edge and a tiebreaker advantage.
- Don't take *both* — the variance compounds and you tank your floor.

**Estimated finish range**: 1st – 25th (bimodal).
**Cash-out probability**: ~22 %. **1st-place probability**: ~3–4 %
(vs. ~1.5 % under Strategy A).

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

The user is estimating 50 participants. If the real count comes in
different, the strategy shifts:

| Participants | Top-5 = top X % | Strategy shift |
| --- | --- | --- |
| 20 | top 25 % | Safe play almost guaranteed cash-out. Go pure chalk. |
| 30 | top 17 % | Slight contrarian advantage; still mostly chalk. |
| **50** | **top 10 %** | **Recommended split: A or B above.** |
| 80 | top 6 % | Strategy B (one swing pick) becomes mandatory. |
| 100+ | top 5 % | Two swing picks become defensible — but tank floor. |

**Update this table** when the actual count is known (from admin).

## Operational checklist

- [ ] **By 09 Jun 2026**: register, pay 10 €, send screenshot + tipp
      name to admin Marco. Activate Kicktipp confirmation (check spam
      if `@data-modul.com`).
- [ ] **By 11 Jun 2026, 21:00 CET**: lock bonus picks in Kicktipp.
- [ ] **From 11 Jun 2026 daily**: enter each match's score in Kicktipp
      ≥1 min before kickoff. The app is more convenient than browser.
- [ ] **Don't forget knockout-stage** picks: 32 + 16 + 8 + 4 + 1 + 1 = 62
      additional matches.

## Final recommendation

**Strategy A** (safe cash-out) is what the user asked for ("at least
get our money back").

## 🔒 Decision — Strategy A is LOCKED (decided 2026-05-15)

Marcel chose Strategy A on 2026-05-15. This is the final strategy and
will not be reconsidered.

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
