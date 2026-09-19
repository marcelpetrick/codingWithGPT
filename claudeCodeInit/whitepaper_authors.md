# Authors to credit and tag

Companion to [`whitepaper.md`](whitepaper.md) / [`paper.pdf`](paper.pdf).
Compiled 2026-09-19.

**Read the confidence column before tagging anyone.** Tagging the wrong person in
a public post is worse than tagging nobody. Two entries below are *name matches
only* — I could not tie the profile to the paper. Confirm those yourself, or use
the institution instead.

**Method and its limits.** The session's web-search budget was exhausted, and
LinkedIn, DuckDuckGo and Mojeek all block automated fetching. So profiles were
established only through *verifiable chains* — a paper's stated code repository
leading to a GitHub account leading to a linked profile, or an official
lab/institution page. Where no such chain exists, the entry says so rather than
guessing a URL.

**A finding in itself:** most of these are academics, and **several have no
LinkedIn at all.** Computer-science researchers tend to live on X, Bluesky,
Mastodon and Google Scholar. For those people the right move is to tag the
**institution** and name the person in the text.

---

## Tier 1 — verified, safe to tag

### Prakhar Khatri — *the two-agent ablation* (arXiv:2607.27250)
- **LinkedIn:** https://www.linkedin.com/in/prakhar-khatri-323200225/
- **X:** https://x.com/PrakharKhatri3 · **GitHub:** https://github.com/codeprakhar25
- Affiliation shown: IIT Roorkee.
- **Confidence: HIGH.** Verified chain: the paper states its code lives at
  `github.com/codeprakhar25/context-files-coding-agents`; that account pins a repo
  of exactly that name described as *"Research ablation study examining whether
  context files improve Claude Code and Codex performance"*; the profile itself
  lists the LinkedIn above.

### Sebastian Baltes — *co-author*, efficiency study (arXiv:2601.20404) and staleness study (arXiv:2606.09090)
- **LinkedIn:** https://www.linkedin.com/in/sebastianbaltes
- **X:** https://twitter.com/s_baltes · **GitHub:** https://github.com/sbaltes
- **Scholar:** https://scholar.google.de/citations?hl=en&user=xO09KrYAAAAJ
- Professor of Software Engineering, Heidelberg University (previously Bayreuth,
  Adelaide, QAware, SAP).
- **Confidence: HIGH.** Links taken from his own group site,
  `empirical-software.engineering` — the same domain that hosts the Lulla et al.
  PDF.
- *Note: co-author, not first author, on both papers.*

---

## Tier 2 — name match only, CONFIRM BEFORE TAGGING

### Brian Sam-Bodden — *the mechanism paper* (arXiv:2607.09691)
- **Candidate LinkedIn:** https://www.linkedin.com/in/sambodden
- **GitHub:** https://github.com/bsbodden · **Site:** https://integrallis.com
- Profile reads: *"Technologist, Author and Entrepreneur. Ex-Principal Applied AI
  Engineer. Ex-DevRel at Redis. @Java_Champions"*, Scottsdale, Arizona.
- **Confidence: MEDIUM — do not tag without checking.** The name is distinctive
  and "Ex-Principal Applied AI Engineer" fits the paper's subject, **but his
  GitHub shows no SWE-bench, coding-agent or context research, and nothing links
  him to arXiv:2607.09691.** This may be a different person with the same name.
  - *To confirm in 30 seconds:* open the LinkedIn profile and look for the paper,
    "SWE-bench", or an arXiv post in his activity.
  - This is the paper I lean on hardest (the 4/45 vs 27/45 result and the ~9%
    noise floor), so it is the one most worth getting right.

---

## Tier 3 — identity confirmed, but no LinkedIn exists / none found

### Thibaud Gloaguen — *the central study* (arXiv:2602.11988)
- **No LinkedIn found.** His official SRI Lab page lists only an institutional
  email, office, the lab GitHub org and the lab X account.
- **Verified:** PhD student, SRI Lab, ETH Zürich, since May 2025; MSc Statistics,
  ETH Zürich 2023–2025; advised by Prof. Martin Vechev. Listed on
  https://www.sri.inf.ethz.ch/people and https://www.sri.inf.ethz.ch/people/thibaud
- **Tag instead:** **ETH Zürich** (institution) and the lab account
  **@the_sri_lab** on X. Name him in the post text.
- Senior author **Martin Vechev** leads the SRI Lab — a more publicly visible
  figure if you want a second name, though he is last author, not main.

### Christoph Treude — *co-author*, staleness study (arXiv:2606.09090)
- **No LinkedIn listed on his own site.**
- **Scholar:** https://scholar.google.com/citations?user=-ie8QFEAAAAJ ·
  **DBLP:** https://dblp.org/pid/29/1074.html ·
  **ORCID:** https://orcid.org/0000-0002-6919-2149
- Associate Professor, School of Computing and Information Systems, Singapore
  Management University. Verified from https://ctreude.ca

### Kushal Chakrabarti — *the +226% growth study* (arXiv:2608.11095)
- **No LinkedIn found; no affiliation published.**
- **ORCID:** https://orcid.org/0009-0007-9464-1608 ·
  **arXiv:** https://arxiv.org/a/chakrabarti_k_1
- **Confidence in identity: HIGH** — the arXiv author page lists
  *"Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding"*
  directly, alongside three other LLM papers.

---

## Tier 4 — not looked up (search budget exhausted)

Paste these into LinkedIn search to finish the list. Each name is taken from the
paper itself, so the name is right even though the profile is unconfirmed.

| Author | Paper | Stated affiliation | Search string |
|---|---|---|---|
| **Jai Lal Lulla** (first author) | Efficiency study, arXiv:2601.20404 | group spanning SMU / Heidelberg / Bamberg / KCL | `"Jai Lal Lulla"` |
| **Damon McMillan** | Factorial adherence study, arXiv:2605.10039 | HxAI, Australia | `"Damon McMillan" HxAI` |
| **Ali Arabat** (first author) | Instructions-as-Code, MSR 2026, arXiv:2606.13449 | with Mohammed Sayagh (ÉTS Montréal) | `"Ali Arabat" ETS` |
| **Niels Mündler-Sasahara** | co-author, arXiv:2602.11988 | SRI Lab, ETH Zürich | `"Niels Mündler"` |

*(A personal site guess for Ali Arabat, `aliarabat.github.io`, returned 404 — so
that route is closed.)*

---

## Institutions — low risk, easy to verify

Safer than an individual if you are unsure. Search LinkedIn for the official page
and confirm the verified badge before tagging:

- **ETH Zürich** — Gloaguen et al., the central study
- **Singapore Management University** — Treude
- **Heidelberg University** — Baltes
- **IIT Roorkee** — Khatri

---

## Ready-to-paste credit line

> This review rests on work by Thibaud Gloaguen and colleagues at the SRI Lab,
> ETH Zürich; Prakhar Khatri; Brian Sam-Bodden; Kushal Chakrabarti; and Jai Lal
> Lulla, Sebastian Baltes, Christoph Treude and co-authors. All of it is
> open-access on arXiv, and the ETH harness is public under MIT. Any errors in
> the synthesis are mine, not theirs.

**Suggested tagging order for a post** (highest verified confidence first):
Prakhar Khatri → Sebastian Baltes → ETH Zürich → *(Brian Sam-Bodden only once
confirmed)*.

---

## One courtesy note

Three of these studies report **null or negative** results, and the whitepaper
argues the field's effect sizes sit under the noise floor. If you tag the authors,
it is worth making clear in the post that the critique is of *the practice*, not
of *their work* — their papers are the reason the critique can be made at all,
and Gloaguen et al.'s is an award-winning paper whose own abstract states the
nuance most commentary drops.

---

## Copy-paste connection notes

LinkedIn caps an invitation note at **300 characters** (and free accounts get a
limited number of noted invites per month). All three below are under the cap.

### Prakhar Khatri — confidence HIGH
https://www.linkedin.com/in/prakhar-khatri-323200225/

> Hi Prakhar - I've been compiling the evidence on whether CLAUDE.md / AGENTS.md context files actually help coding agents. Your two-agent ablation stood out for the equivalence testing and for being upfront about what it could and couldn't detect. Would be glad to connect.

*(272 chars. Accurate: his result is a null, and the paper is unusually honest —
it publishes its own power analysis showing a minimum detectable effect of
~30 pp. Complimenting the method rather than the result is the truthful move.)*

### Sebastian Baltes — confidence HIGH
https://www.linkedin.com/in/sebastianbaltes

> Hi Sebastian - I've been reviewing the evidence on repository context files for coding agents. The AGENTS.md efficiency study and your work on staleness in AI configuration artifacts both fed into it. Would be glad to connect.

*(226 chars. He is a co-author on both, not first author — the wording credits
the work without implying he led it.)*

### Brian Sam-Bodden — confidence MEDIUM, identity unconfirmed
https://www.linkedin.com/in/sambodden

> Hi Brian - if you're the author of "What Context Does a Coding Agent Actually Need to Act?", that paper reframed a review I've been doing on repo context files: the 4/45 vs 27/45 result and the temperature-0 noise floor especially. Would be glad to connect.

*(257 chars. The conditional opening is deliberate: it is honest about the
unverified identity, and it doubles as the verification — if it is the wrong
Brian, the phrasing costs nothing and no false claim was made.)*

---

## No LinkedIn — reach these by another channel

### Thibaud Gloaguen — first author of the central study
No LinkedIn. His SRI Lab page publishes an institutional address for exactly this
purpose: `thibaud.gloaguen@inf.ethz.ch`. A short academic email, not a connect note:

> Subject: Your AGENTS.md evaluation
>
> Hi Thibaud,
>
> I've been putting together a review of whether repository context files help coding agents, and your ICLR workshop paper is the backbone of it. The distinction your abstract draws — instructions followed, repository overviews not helpful — is the part most secondary commentary drops, and it turned out to be the finding that reconciles the rest of the literature.
>
> Thank you for releasing the harness under MIT.
>
> Best regards,
> Marcel Petrick

### Christoph Treude
No LinkedIn on his site. Reachable via Singapore Management University, or
https://scholar.google.com/citations?user=-ie8QFEAAAAJ

### Kushal Chakrabarti
No LinkedIn and no published affiliation. Only https://orcid.org/0009-0007-9464-1608
