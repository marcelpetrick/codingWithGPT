# AGENTS.md — agent guide, DATA MODUL WM 2026 Kicktipp

## Context

FIFA World Cup 2026 (USA/Canada/Mexico, 11 Jun – 19 Jul 2026).  
29-participant office pool · €290 prize pot · stake €10.  
Primary goal: top-5 finish (≥ €23.20 back). Stretch: 1st (€116).  
**Strategy A locked 2026-05-15**: chalk/cash-out. No mid-tournament switches.  
Semi-finalists: France, Spain, Argentina, Brazil. Champion: France.

Key file chain: [`pool_rules.md`](pool_rules.md) → [`strategy.md`](strategy.md) → [`model_picks.md`](model_picks.md) → [`my_picks.md`](my_picks.md).  
Active queue: [`pick_adjustment_watchlist.md`](pick_adjustment_watchlist.md).  
Audit trail: dated `StrategyReviewYYYYMMDD.md` files.

---

## Standard update run

Triggered when the user says: "update", "pull news", "review results", "what are the next bets", or similar.

### Step 1 — Fan out 4 subagents in parallel

Launch all four simultaneously. Do not wait for one before launching the next.

**Agent A — Match results (last 48 h)**
> Search ESPN, BBC Sport, FIFA.com, Sofascore, Olympics.com for all WC 2026 results from the last 48 hours. For each match: score, scorers, red cards, and — if our pick is known — how many Kicktipp points we scored (4=exact, 3=correct GD, 2=tendency, 0=miss). Today's date: {TODAY}. Output as a compact table.

**Agent B — Group standings (all 12 groups)**
> Search FIFA.com, Wikipedia, NBC Sports for current WC 2026 group standings for all 12 groups (A–L). For each group: team, Pld, W, D, L, GF, GA, Pts. Also flag which of these bonus group-winner picks are now threatened: Mexico(A), Switzerland(B), Brazil(C), USA(D), Germany(E), Netherlands(F), Belgium(G), Spain(H), France(I), Argentina(J), Portugal(K), England(L). Today's date: {TODAY}. Output: one table per group + threat-level bullet list.

**Agent C — Betting odds for upcoming matches**
> Search Oddschecker, Racing Post, bet365, CBS Sports, FanDuel for 1X2 odds on all WC 2026 matches not yet played as of {TODAY}. Cover the next two Spieltags (≈16 matches). For each: Match | Home% | Draw% | Away% | Implied favourite | Our current pick | Any notable line movement or injury factor. Output as a table.

**Agent D — Team and injury news**
> Search Sky Sports, ESPN, BBC Sport, The Athletic for WC 2026 injury, suspension, and lineup news updated in the last 48 hours. Focus on: France, Spain, Argentina, Brazil, Germany, Netherlands, England, Portugal, Belgium, Mexico, Norway, Colombia. For each team, one bullet — only new information vs the last 24 h. Flag any news that changes the chalk favourite for an upcoming match. Today's date: {TODAY}.

### Step 2 — After all agents return

1. **Score the results**: compare actual scores to `my_picks.md` picks; total points for the completed Spieltag.
2. **Flag urgent entries**: any match locking in <6 h gets ⚡ treatment first.
3. **Create `StrategyReviewYYYYMMDD.md`** (see template below).
4. **Update `my_picks.md`**: mark locked results with actual score + points; update Spieltag entry queues; add the next Spieltag queue if not yet present.
5. **Update `pick_adjustment_watchlist.md`**: update Spieltag result rows; refresh upcoming review items.
6. **Append to `sources.md`**: add all new URLs under a dated `## Research update — YYYY-MM-DD` section.
7. **Commit** (see guidelines below).
8. **Present summary to user** (see output format below).

### StrategyReview template

```markdown
# Strategy Review — DD Month YYYY

## Spieltag N — scorecard
| Match | Pick | Result | Points |
| … | … | … | … |
| **Total** | | | **X / 32** |

## Running total
| Window | Points | Notes |
| … | … | … |

## Bonus pick threats
| Pick | Status | Threat |
| … | … | LOW / MEDIUM / HIGH / VERY HIGH |

## Key news (last 48 h)
| Team | News | Pick impact |
| … | … | … |

## Spieltag N remaining — entry queue
| Kicktipp order | Enter | Lock (CET) | Status |

## Spieltag N+1 — entry queue
| Kicktipp order | Enter | Lock (CET) | Notes |

## Spieltag N+2 — entry queue (if known)
| Kicktipp order | Enter | Lock (CET) | Notes |

## Strategy verdict
One sentence: hold all / adjust X because Y.
```

---

## Commit guidelines

After every update run, commit exactly these files:

```
git add my_picks.md pick_adjustment_watchlist.md sources.md StrategyReview{YYYYMMDD}.md
git commit -m "$(cat <<'EOF'
chore(tipkick): review YYYY-MM-DD — ST{N} results, ST{N+1}/{N+2} picks locked

- ST{N}: X/32 pts — [key hit or miss]
- Running total: X pts
- [Any pick change, e.g. "Netherlands 2:1 flagged as high-risk"]
- Strategy A holds.
EOF
)"
```

Never push unless the user explicitly asks. Never commit without a StrategyReview for that date.

---

## House rules for editing

- **Never edit `my_picks.md` without flagging every change** — it is the submitted-pick record.
- **Edit (patch), don't rewrite** — use the Edit tool on affected sections only.
- **Always update `sources.md`** when citing a new article.
- **Flag stale info**: odds >48 h old, injury reports >24 h old — note the age.
- **Today's date matters.** If a data point could be stale, say so.

---

## Output format (after update run)

Deliver in this order — **tables beat paragraphs**:

1. **⚡ Urgent entries** — matches locking in <6 h, with the pick to enter
2. **Score recap** — Spieltag | Pick | Result | Pts, plus running total
3. **Next bets** — all pending picks for the next 2–3 Spieltags in one table
4. **Strategy verdict** — one sentence
5. **Bonus pick threats** — one line per at-risk pick only

Tone: terse, decision-oriented. Silently correct dictation mis-spellings (e.g. "Pochettini" → Pochettino). No "football is unpredictable" disclaimers.

---

## Strategy A rules (locked 2026-05-15)

- Default scorelines: **2–1** for clear favourite; **1–0** in tight games; **2–0** vs minnows; **1–1** when evenly matched.
- No blowout chasing (no 4–0, no 3–2).
- No contrarian swaps, even if behind in the pool and "needing to catch up".
- **Allowed**: update a default when injury/suspension/market materially changes who the chalk favourite is.
- **Forbidden**: switching to Strategy B or high-variance picks mid-tournament.

---

## File index

| File | Purpose |
|---|---|
| `pool_rules.md` | Scoring system, bonus rules, payout table |
| `strategy.md` | Strategy A rationale and decision log |
| `model_picks.md` | Data-driven baseline picks |
| `my_picks.md` | **Submitted-pick record** — the live sheet |
| `pick_adjustment_watchlist.md` | Live queue of results + upcoming entries |
| `sources.md` | All cited URLs, dated |
| `StrategyReviewYYYYMMDD.md` | Dated audit after each update run |
| `favorites.md` | Top-tier team research |
| `dark_horses.md` | Dark horse team research |
| `hosts.md` | Host nation analysis |
| `groups.md` | Group-by-group analysis |
| `prediction_timeline.md` | Tournament timeline |

If you add a new file, update both `README.md` and this file's table.

---

## Out of scope

- No code generation unless explicitly asked.
- No `git push` unless user asks.
- No wholesale file rewrites — patch only.
- No commits outside of an update run unless user asks.
