# CLAUDE.md — agent guide for this directory

You are helping the user win (or at least cash out in) the **DATA
MODUL WM 2026** Kicktipp prediction pool for the FIFA World Cup 2026
(USA / Canada / Mexico, 11 June – 19 July 2026).

This file is loaded into every Claude Code session that runs in this
directory. **Read it first.** Then read [`pool_rules.md`](pool_rules.md)
and [`strategy.md`](strategy.md) so you know the scoring model.

## Workflow

The user will periodically paste new information into the chat —
typical examples:

- A revised squad list, an injury update, a friendly result.
- Updated betting odds.
- An admin e-mail with new pool rules (e.g. a deadline shift).
- A new bonus question.
- News about a specific team or coach.
- Their gut feeling about a pick.
- The actual pool participant count (confirmed 2026-06-02: **25**).

For each new drop:

1. **Identify what kind of information it is** (rules / team-form /
   odds / scheduling / user gut).
2. **Integrate it into the relevant file(s)**:
   - Rules / pool changes → [`pool_rules.md`](pool_rules.md)
   - Team form / squad / injuries / coach → [`favorites.md`](favorites.md),
     [`hosts.md`](hosts.md), [`dark_horses.md`](dark_horses.md), or
     [`groups.md`](groups.md) — whichever covers that team.
   - Odds / power-ranking changes → [`favorites.md`](favorites.md)
   - Strategy implications (pool size, payout math) →
     [`strategy.md`](strategy.md)
   - Sources → append to [`sources.md`](sources.md)
3. **Re-check the model picks** in [`model_picks.md`](model_picks.md).
   If the new info materially changes a pick (e.g. Yamal ruled out,
   Mbappé injured), update it and call out the change in the chat.
4. **Update [`my_picks.md`](my_picks.md)** — propagate the change to
   any group-stage line or bonus pick that's affected. Make sure the
   default picks in `my_picks.md` are always consistent with
   `model_picks.md`.
5. **Briefly tell the user what changed and why** — one short paragraph
   per drop, not a wall of text.

## House rules for editing

- **Never edit `my_picks.md` without telling the user** — it's their
  pick sheet. Updating defaults is fine, but flag every change.
- **Don't rewrite files wholesale** — use `Edit` to patch the affected
  section. Leave the user's manual `___` entries untouched.
- **Always update `sources.md`** when you cite a new article.
- **Today's date matters**. Reconfirm with the user if a piece of info
  could be stale (e.g. an odds quote from weeks ago).
- **🔒 Strategy A is LOCKED** (decided 2026-05-15). All defaults must
  stay within the pure-chalk / cash-out philosophy. Do **not** suggest
  contrarian swaps or switches to Strategy B mid-tournament, even if
  events seem to call for it. Strategy A holds through the final on
  19 July 2026.
  - Allowed: refining a default within Strategy A when news arrives
    (injury, suspension, weather → pick the next-best favorite).
  - Forbidden: turning a chalk pick into a high-variance swing because
    "we're behind and need to catch up". The pool runs over 104
    matches — variance regresses; don't panic.

## What the user wants right now

- **Stake**: 10 €. **Pool size (confirmed 2026-06-02)**: 25 participants ⇒ pool = 250 €.
- **Primary goal**: top-5 finish (any paying place = at least €20 back, i.e. net +€10).
- **Stretch goal**: 1st place (€100).
- **Tone**: terse, decision-oriented. Skip generic "here's why football
  is unpredictable" disclaimers — the user knows.
- **Deliverable on each interaction**: which files changed and a
  one-line "what this means for your picks".

## Style

- The user has set Claude Code to terse mode in their preferences.
- Use markdown but don't be verbose. **Tables and bullet lists beat
  paragraphs.**
- Mix dictation-friendly prose if you must — the user often dictates,
  so misheard names (e.g. "Pochettino" rendered as "Pochettini") are
  the user's, not yours. Quietly correct them.

## Files in this directory

See [`README.md`](README.md) for the canonical file index. If you add
a new file, update both `README.md` and this `CLAUDE.md`.

## Out of scope

- Don't generate code unless asked. This is a research/picks repo,
  not a software project (despite the parent dir being `codingWithGPT`).
- Don't push to remote or commit unless the user asks.
