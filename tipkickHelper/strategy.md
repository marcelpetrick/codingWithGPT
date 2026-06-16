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

**Updated 2026-06-09**: **29 participants**. Each pays €10 → **pool
= €290**.

| Place | Share | Payout | Net (after −€10 stake) |
| --- | --- | --- | --- |
| 1st | 40 % | €116 | **+€106** |
| 2nd | 25 % | €72.50 | **+€62.50** |
| 3rd | 15 % | €43.50 | **+€33.50** |
| 4th | 12 % | €34.80 | **+€24.80** |
| 5th | 8 % | €23.20 | **+€13.20** |
| 6th–29th | 0 % | €0 | **−€10** |

**To cash out at all you need top-5 of 29** — i.e. the top **17.2 %**
of the field. Even **5th place more than doubles the stake** (+€13.20
net). This is a little tougher than N=25, but still much easier than
the original 50-tipper assumption (top 10 %), so pure chalk remains
the correct cash-out line.

## What "cash out" probability actually requires

At **N = 29** the bar is the top 17.2 %. An above-median diligent
Kicktipp player should land top-5 of 29 roughly **50–60 %** of the
time, because:

- ~half the participants are casuals (random picks) — easy to beat.
- ~25 % are mid-engaged (chalk picks, no edge) — beatable with diligence.
- ~15 % are sharper than you on a given week.
- ~10 % land lucky on a high-variance bonus pick.

Out of 29, that's ~15 casuals + ~7 chalk-only + ~4 sharper + ~3
lucky-variance players. Your goal is to consistently outperform the
~22 casuals + chalk-only players. The sharper minority is hard to
beat reliably; ride variance.

## Strategy choice — locked before 11 June

This section is historical context. The choice has already been made:
Strategy A was locked on 2026-05-15 and remains active through the
final.

### Strategy A — "Safe / Cash Out" (target: top 5)

> The goal is **at least €23.20 back** (5th place at N=29) with high
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

**Estimated finish range (at N=29)**: 2nd – 10th place (median ~5th/6th).
**Cash-out probability (at N=29)**: ~50–60 %.

### Strategy B — "Swing / Win It" (target: 1st)

> The goal is **€116** (1st place at N=29). You accept that you might
> finish mid-table on most simulation runs in exchange for a real
> chance at the big prize.

**Rules**:

- Match A's per-match scoreline play (chalk on tendency, modal
  scorelines) — **don't over-cleverize the group stage**.
- Take **one** contrarian leverage bet — exactly one. Two examples
  (counts scaled to **N=29**):
  - **Champion = Portugal** (~+1000 implied 10 %; only ~2–3 of 29 will
    pick this). Adds 4 bonus pts if right and big positional swing.
  - **Semi-finalist swap: Brazil → Croatia or Morocco**. ~3–5 of 29
    will have Brazil; ≤2 will have Croatia/Morocco. If Croatia makes
    semis, you bank a 4-pt edge and a tiebreaker advantage.
- Don't take *both* — the variance compounds and you tank your floor.

**Estimated finish range (at N=29)**: 1st – 20th (bimodal).
**Cash-out probability (at N=29)**: ~40–50 %.
**1st-place probability (at N=29)**: ~7–10 % (vs. ~4–6 % under
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

**Updated**: **29 participants** (user message, 2026-06-09). For
reference, here's how the threshold scales:

| Participants | Top-5 = top X % | Strategy implication |
| --- | --- | --- |
| 13 | top 38 % | Below 13 even 5th place loses money. |
| 20 | top 25 % | Safe play almost guaranteed cash-out. Go pure chalk. |
| 25 | top 20 % | Pure chalk has positive EV; one swing optional for the 1st-place lottery. |
| **29** | **top 17.2 %** | **Still Strategy A: pure chalk, only forced news-based changes.** |
| 30 | top 17 % | Slight contrarian advantage; still mostly chalk. |
| 50 | top 10 % | Recommended split: A or B. |
| 80 | top 6 % | Strategy B (one swing pick) becomes mandatory. |
| 100+ | top 5 % | Two swing picks become defensible — but tank floor. |

**Note**: at N=29, 5th place = +€13.20. The cash-out floor is still
meaningful — Strategy A's "don't lose money" objective remains
achievable with pure chalk, but the field is now just large enough
that wrong bonus favorites hurt more.

## Operational checklist

- [x] **By 09 Jun 2026, 23:59**: register, pay 10 €, send screenshot
      + tipp name to admin. Activate Kicktipp confirmation (check spam
      folder if you used a company e-mail address).
- [x] **By 11 Jun 2026, 21:00 CET**: lock bonus picks in Kicktipp.
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

### Pool-size update — 2026-06-09 (does NOT unlock the strategy)

Updated N=29 (not the 50 assumed at locking time). The smaller pool
still makes Strategy A's cash-out *easier* than the original assumption
(top 17.2 % instead of top 10 %), so the lock is reinforced, not
weakened: 5th place now nets +€13.20, 4th nets +€24.80 — pure chalk
is still positive EV. No reason to override the lock.

**Locked picks (bonus, A-set)**:
- Top-scorer team → **France**
- Semi-finalists → **France, Spain, Argentina, Brazil**
- Champion → **France**
- Group winners → all 12 market favorites (see `my_picks.md`; Group B
  updated Canada → Switzerland on 2026-06-09)
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
- ✅ Bringing in new info for future per-match picks and applying it
  before each match's 1-minute lockout.

### When you might reconsider

Not during this tournament. If after the World Cup you want to evaluate
whether Strategy A or B was the better choice in hindsight, that's
fine — but it's a post-mortem, not a live correction.

---

## In-tournament learnings — 2026-06-13 (early audit, corrected 2026-06-16)

**Conservative scoreboard after 4 matches: 6 / 16 pts (37.5 %)**

Audit correction 2026-06-16: the original version counted Canada –
Bosnia as a 1–1 exact hit. Current `my_picks.md` records that match as
`2–1` entered, so it is scored as a miss unless the Kicktipp app proves
the submitted pick was 1–1.

| Match | Pick | Actual | Pts |
|-------|------|--------|-----|
| Mexico – South Africa | 2–0 | 2–0 ✅ | +4 exact |
| Korea Rep – Czechia | 1–1 | 2–1 KOR ❌ | +0 tendency miss |
| Canada – Bosnia | 2–1 CAN per current `my_picks.md` | 1–1 ❌ | +0 miss |
| USA – Paraguay | 2–0 USA | 4–1 USA ⚠️ | +2 tendency only |

The Mexico exact hit was good, but the early audit is weaker than the
first review claimed. Korea and USA still teach the same lesson:
when a real tier gap exists, the scoreline pick was too conservative
relative to the favorite's edge.

### Calibration rule derived from matchday 1

> **When `groups.md` marks a team ★★★ and the opponent ★ or 💤, the
> default scoreline must be a WIN for the stronger side, not a draw (1–1).**
> A 1–1 pick is only correct when both teams are genuinely ★★ or when
> there is a specific reason for caginess (cagey tactical setup, neutral
> venue with no crowd edge, must-draw dynamic).

This is not a strategy change — it is a clarification of how to apply
"chalk" correctly. The default scorelines from `model_picks.md` (2–1,
1–0, 2–0, 1–1) stay the same; the lesson is which one to pick for a
given tier pairing.

### What to watch for in future picks

These are forward-looking notes, not adjustments to already-submitted
picks:

1. **★★★ vs ★ / 💤 → pick the win, not the draw.** Korea–Czechia and
   USA–Paraguay both showed the stronger side wins convincingly. When
   the tier gap is this large, 1–1 is the wrong modal outcome. Default
   to 2–0 or 1–0 for the favorite.

2. **Home crowd boost is real and larger than assumed.** USA scored 4
   vs Paraguay (picked 2–0). Mexico scored 2–0 comfortably at Azteca.
   For remaining host-nation matches (USA vs Australia, USA vs Türkiye;
   Mexico vs Korea, Mexico vs Czechia) lean toward a comfortable win
   margin, not just a bare minimum.

3. **★★ vs ★★ is where 1–1 earns its keep.** Canada–Bosnia 1–1 was the
   correct model read even though current `my_picks.md` says the
   submitted pick was 2–1. Both teams were close in quality, with no
   obvious enough edge to force a win. The draw is the right chalk for
   genuinely balanced matchups.

4. **Don't overcorrect after a tendency miss.** The Korea miss is 1 data
   point. The risk is now picking wins too aggressively and getting the
   tendency wrong the other way (e.g., calling a ★★★ team's win in a
   match where they tactically hold back for MD3). Apply the calibration
   rule with judgment, not mechanically.

5. **Brazil–Morocco style 50/50 draws: hold the 1–1.** When the model
   explicitly calls a match a "true 50/50" (equal tier, unknown lineup,
   neutral venue), the 1–1 is the correct pick regardless of the MD1
   lesson. The rule above applies to tier mismatches, not to balanced
   clashes between top-20 sides.

See [`StrategyReview20260613.md`](StrategyReview20260613.md) for the
original breakdown and [`StrategyReview20260616.md`](StrategyReview20260616.md)
for the corrected audit.
