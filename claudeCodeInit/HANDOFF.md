# Handoff — finish the author lookups

**Written 2026-09-19 by the session that produced this study.** Read this first
if you are a new or resumed session picking the work up.

## Why this file exists

The previous session exhausted its web-search budget (200/200). The limit was
raised to 400 in `~/.claude/settings.json` under
`env.CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`, but that value is read **at
session start**, so it could not take effect in the session that set it.

**First thing to do: confirm search actually works.** Run one `WebSearch`. If it
still reports the budget exhausted, the counter carried over with the resumed
session — stop and tell the user to start a *fresh* session instead (this file is
written so a fresh session with no prior context can do the work).

## State of the repository

- **On the public remote** (`github.com/marcelpetrick/codingWithGPT`, master):
  everything through commit `55c8dd6`, which **includes** `whitepaper_authors.md`.
- **Local only:** commit `03c8616` (the copy-paste connect notes) and this file.
- **Do not push** without asking the user. The previous session told the user
  `whitepaper_authors.md` was unpushed when it was in fact already public; be
  precise about remote state and verify with `git ls-remote origin refs/heads/master`
  rather than trusting `origin/master`.

## A decision already made — do not reopen it

`whitepaper_authors.md` is public (it is in commit `55c8dd6` on the remote).
The previous session flagged this to the user, including that the file says of a
named individual that the profile "may be a different person with the same name",
and offered to soften or remove it. **The user chose to leave it as is.** Do not
re-raise this, and do not edit that wording on your own initiative. If you *confirm*
the Sam-Bodden identity, updating the grade from MEDIUM to HIGH is of course fine —
that is the task.

## The job

Finish the author table in `whitepaper_authors.md`. Four first authors were never
looked up. For each: find a **LinkedIn profile URL** and write a **connect note
under 300 characters**, matching the format already used in that file.

| Author | Paper | Stated affiliation |
|---|---|---|
| **Jai Lal Lulla** (first author) | *On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents*, arXiv:2601.20404 | group spanning SMU / Heidelberg / Bamberg / KCL |
| **Damon McMillan** | *Instruction Adherence in Coding Agent Configuration Files*, arXiv:2605.10039 | HxAI, Australia |
| **Ali Arabat** (first author) | *Toward Instructions-as-Code*, MSR 2026, arXiv:2606.13449 | with Mohammed Sayagh, ÉTS Montréal |
| **Niels Mündler-Sasahara** | co-author, arXiv:2602.11988 | SRI Lab, ETH Zürich |

Also: **confirm or refute the Brian Sam-Bodden identity** (see below).

## Rules — these are the point of the task, not decoration

1. **Never publish a guessed profile URL.** Tagging the wrong person in a public
   post is the failure mode this whole file exists to prevent. If you cannot tie a
   profile to the paper, say so and leave the slot empty.
2. **Verify by chain, not by name match.** The two entries already graded HIGH
   were established like this: the paper states its code repository → that account
   pins exactly that repository → the profile lists the LinkedIn. Reproduce that
   standard. A matching name plus a plausible job title is **not** verification.
3. **Grade every entry** HIGH / MEDIUM / absent, and say what the evidence was.
4. **Expect absences.** Of the six authors checked so far, **three have no
   LinkedIn at all** (Gloaguen, Treude, Chakrabarti). Academics often don't. A
   confirmed absence is a valid, useful result — record it and suggest the
   institution instead. Do not manufacture a link to fill a row.
5. **Connect notes must be accurate about the work.** Khatri's result is a null,
   so his note praises the method. Baltes is a co-author, not first author, so his
   note says so. Three of these studies report null or negative results; the
   critique is of the practice, not of their work.
6. **LinkedIn blocks automated fetching**, as do DuckDuckGo (CAPTCHA) and Mojeek
   (403). `WebSearch` snippets and fetchable personal/lab/GitHub pages are the
   realistic routes.

## The one open verification

`https://www.linkedin.com/in/sambodden` is recorded at **MEDIUM** confidence for
**Brian Sam-Bodden**, author of arXiv:2607.09691 — the most load-bearing paper in
the whole review (the 4/45 vs 27/45 representation result and the ~9% temperature-0
noise floor). The profile is a real person: GitHub `bsbodden`, Integrallis,
Scottsdale AZ, ex-Redis DevRel, Java Champion, "Ex-Principal Applied AI Engineer".
**But nothing ties that profile to the paper** — his GitHub shows no SWE-bench or
coding-agent work. Settle it, and update the grade either way.

## When done

1. Update `whitepaper_authors.md` (new rows in the verified tiers, connect notes in
   the copy-paste section, and move anything confirmed out of Tier 4).
2. Commit locally with a message that states what was verified and how.
3. **Ask** before pushing.

## Background, if you need it

- `whitepaper.md` — the meta-study, with a 5-sentence TL;DR.
- `results.md` — the full dossier.
- `evidence/verification-log.md` — what was checked, what conflicted, and the
  claims rejected as fabricated. Read this before trusting any secondary source
  on this topic; two widely-circulated statistics in this space are invented.
