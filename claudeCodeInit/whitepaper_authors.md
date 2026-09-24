# Authors to credit and tag

Companion to [`whitepaper.md`](whitepaper.md) / [`paper.pdf`](paper.pdf).
Compiled 2026-09-19; author lookups completed 2026-09-20, extended the same day
to cover the two papers added by the round-5 literature sweep.

**Read the confidence column before tagging anyone.** Tagging the wrong person in
a public post is worse than tagging nobody. Three entries below are *name and
affiliation matches only* — the profile could not be tied to the paper by a
published link. Confirm those yourself, or use the institution instead.

**Method and its limits.** LinkedIn, DuckDuckGo and Mojeek all block automated
fetching, so no profile page below was read directly. Profiles are graded HIGH
only where a *verifiable chain* exists — a paper's stated code repository or
author email leading to an account that itself publishes the profile link, or an
official lab/institution page. MEDIUM means the name, the affiliation and the
research topic all match, but no verified account links to the profile. Where no
chain exists at all, the entry says so rather than guessing a URL.

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

### Brian Sam-Bodden — *the mechanism paper* (arXiv:2607.09691)
- **LinkedIn:** https://www.linkedin.com/in/sambodden
- **GitHub:** https://github.com/bsbodden · **Site:** https://integrallis.com
- **X:** https://twitter.com/bsbodden · Scottsdale, Arizona.
- **Confidence: HIGH — upgraded from MEDIUM on 2026-09-20.** Verified chain: the
  paper's author block gives *"Brian Sam-Bodden, Integrallis Software,
  bsbodden@integrallis.com"* and states *"Code and data:
  https://github.com/integrallis/act-context"*; that repository is owned by the
  `integrallis` org and described as reproduction code for the paper; the GitHub
  account `bsbodden` lists company `@integrallis`, is a member of that org, and
  **publishes the LinkedIn URL above on its own profile.**
- The earlier doubt is resolved: his *personal* GitHub shows Redis and Java work
  because the paper's code lives under the **company** org, not his user account.

### Niels Mündler-Sasahara — *second author*, the central study (arXiv:2602.11988)
- **LinkedIn:** https://www.linkedin.com/in/niels-muendler
- **GitHub:** https://github.com/nielstron · **X:** https://x.com/nielstron
- **Site:** https://blog.nielstron.de · **Scholar:**
  https://scholar.google.com/citations?user=iX8Ib9wAAAAJ
- PhD student, SRI Lab, ETH Zürich since July 2024, advised by Martin Vechev.
- **Confidence: HIGH.** Verified chain: his SRI Lab page
  (https://www.sri.inf.ethz.ch/people/niels) lists no socials but uses the handle
  `nielstron`; `github.com/nielstron` gives the full name *Niels
  Mündler-Sasahara*, ETH Zürich, *"Working on Code LLM security"*, and links
  http://blog.nielstron.de; that site names him as *"PhD Student at ETH Zurich
  under Martin Vechev"* and **publishes the LinkedIn URL above.**
- *Note: second author of five (Gloaguen, Mündler, Müller, Raychev, Vechev) —
  credit the team, not him alone.* Unlike Gloaguen, he **does** have a LinkedIn.

### Asa Shepard — *the exception*, probe-and-refine tuning (arXiv:2606.20512)
- **LinkedIn:** https://www.linkedin.com/in/asa-shepard/
- **GitHub:** https://github.com/asashepard · **Site:** https://asashepard.com
- Williams College (CS + Philosophy + Cognitive Science); co-founder of Sediment.
- **Confidence: HIGH.** Verified chain, the same standard as Khatri: the paper's
  author block gives *"Asa Shepard, Williams College, as66@williams.edu"* and the
  body states *"Code: https://github.com/asashepard/probe-and-refine-tuning"*;
  that account owns **and pins** a repo of exactly that name, described as *"Repo
  for the research paper 'Probe-and-Refine Tuning of Repository Guidance for
  Coding Agents'"*; and the profile **publishes the LinkedIn URL above.**
- **This is the most important new name in the review.** His is the only study of
  the five with a significance-tested positive result, and §7 of the whitepaper
  now rests on it. He is also a student, not a professor — worth crediting by
  name rather than by institution.

---

## Tier 2 — name and affiliation match only, CONFIRM BEFORE TAGGING

All three were checked on 2026-09-20. In each case the name is distinctive, the
LinkedIn headline states the same institution the paper states, and the profile's
research record matches — but no verified account of theirs publishes the URL, so
the last link of the chain is missing.

### Jai Lal Lulla — *first author*, efficiency study (arXiv:2601.20404)
- **Candidate LinkedIn:** https://www.linkedin.com/in/jai-lulla-764457206/
  (headline: *"Jai Lulla — Singapore Management University"*)
- **Scholar:** https://scholar.google.com/citations?user=U6GH2EMAAAAJ
- **Confidence: MEDIUM.** The paper's author block gives *"Jai Lal Lulla,
  Singapore Management University, jailal.l.2025@phdcs.smu.edu.sg"*; the Scholar
  profile carries a verified `smu.edu.sg` address, lists this paper, and states
  interests *"Software Engineering, AI4SE, Agentic AI Coding Tools"*. The LinkedIn
  headline matches the institution — **but nothing he controls publishes that
  URL**, so it stays MEDIUM.
- *To confirm in 30 seconds:* open the profile and look for SMU, the AGENTS.md
  paper, or "Loop Engineering" (his other 2026 paper) in the activity feed.
- The paper's online appendix is Zenodo DOI `10.5281/zenodo.18348507`; it carries
  no personal links, so that route is closed.

### Ali Arabat — *first author*, Instructions-as-Code (MSR 2026, arXiv:2606.13449)
- **Candidate LinkedIn:** https://ca.linkedin.com/in/ali-arabat-206906170
  (headline: *"ALI ARABAT — Software Engineering Researcher — École de
  technologie supérieure"*)
- **Confidence: MEDIUM.** The paper gives *"Ali Arabat, Mohammed Sayagh, École de
  Technologie Supérieure, Montréal, ali.arabat.1@ens.etsmtl.ca"*. The profile
  states the same institution and surfaces alongside his known record — the
  Empirical Software Engineering work with Sayagh on cross-component dependent
  changes in OpenStack. **But his supervisor's site (msayagh.github.io) names no
  students, and no personal page or GitHub of his could be found**, so there is
  no published link to close the chain.
- *(The earlier guess `aliarabat.github.io` is a 404 — that route stays closed.)*
- **Safe alternative:** tag **ÉTS Montréal**, and name his supervisor
  **Mohammed Sayagh** in the text — his faculty page
  (https://www.etsmtl.ca/etudier-a-lets/corps-enseignant/msayagh) and personal
  site (https://msayagh.github.io) are verified. A LinkedIn for Sayagh also turns
  up (`/in/mohammed-sayagh-24bab978/`) but it is a **search-result match only**,
  same caveat as above.

### Mojtaba Shahin — *co-author*, rule taxonomy and evolution (arXiv:2606.12231)
- **Candidate LinkedIn:** https://au.linkedin.com/in/mojtaba-shahin-659b87b8
  (headline: *"Senior Lecturer in Software Engineering"*, RMIT University)
- **Scholar:** https://scholar.google.com.au/citations?user=Aml0q7sAAAAJ
- **Confidence: MEDIUM.** The paper places him at *"School of Computing
  Technologies, RMIT University, Melbourne"*, and the profile states the same
  role and institution — but the URL came from search metadata, not from anything
  he publishes. Same caveat as the two entries above.
- *Note: fifth of five authors on a supporting, non-causal paper.* If you tag one
  name from that study it should be the first author, **Guangzong Cai** — who has
  no findable profile at all (Tier 3).

---

## Tier 3 — no taggable profile (no LinkedIn, or no identifiable person)

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
- **His second author does have a LinkedIn:** Niels Mündler-Sasahara, Tier 1
  above. Tagging him reaches the same paper — but credit the team, not him as
  first author.

### Christoph Treude — *co-author*, staleness study (arXiv:2606.09090)
- **No LinkedIn listed on his own site.**
- **Scholar:** https://scholar.google.com/citations?user=-ie8QFEAAAAJ ·
  **DBLP:** https://dblp.org/pid/29/1074.html ·
  **ORCID:** https://orcid.org/0000-0002-6919-2149
- Associate Professor, School of Computing and Information Systems, Singapore
  Management University. Verified from https://ctreude.ca

### Jeannie Albrecht — *co-author*, probe-and-refine (arXiv:2606.20512)
- **No LinkedIn.** Her own faculty page (https://www.cs.williams.edu/~jeannie/)
  publishes an email, a phone number, an office, a CV and a publication list —
  and no social profile of any kind. A deliberate absence, not an oversight.
- **Verified:** Robert G. Scott '68 Professor, Department of Computer Science,
  Williams College. Reachable at `jeannie@cs.williams.edu`.
- **Tag instead:** **Williams College**, and name her in the text. Her co-author
  Asa Shepard is in Tier 1 and reaches the same paper.

### Cai, Li, Liang, Li & Shahin — *rule taxonomy* (arXiv:2606.12231)
- **First author Guangzong Cai has no findable profile.** Wuhan University,
  School of Computer Science.
- Senior author **Peng Liang** (Wuhan University) is a prolific and publicly
  visible SE researcher — **Scholar:**
  https://scholar.google.com/citations?user=76CoujsAAAAJ — but no LinkedIn
  surfaced for him either. Co-authors: Ruiyin Li (Wuhan), Zengyang Li (Central
  China Normal University), Mojtaba Shahin (RMIT, Tier 2).
- **Tag instead:** **Wuhan University**. This is a supporting paper, not one of
  the five ablations, so it does not need a tag at all.

### Damon McMillan — *the factorial adherence study* (arXiv:2605.10039)
- **No profile can be tied to the paper. Do not tag anyone.**
- The paper's entire author block is two lines: *"Damon McMillan / HxAI
  Australia"*. No email, no ORCID, no repository, no data-availability statement
  anywhere in the 18 pages.
- **HxAI publishes no names.** https://h-x.ai describes *"an independent research
  organisation"*, attributes its output to the collective *"HxAi Research Team"*,
  and gives one contact: **research@h-x.ai**, Melbourne, Australia.
- LinkedIn has several Australians of that name — one at Deloitte Digital who
  posts about production agents, one an engineer at Blue Trail Engineering.
  **Neither is connected to HxAI by any published evidence**, and the topical
  plausibility of the first is exactly the trap this file exists to avoid.
- **Reach him at research@h-x.ai instead**, or cite *"HxAI (Melbourne)"*.

### Kushal Chakrabarti — *the +226% growth study* (arXiv:2608.11095)
- **No LinkedIn found; no affiliation published.**
- **ORCID:** https://orcid.org/0009-0007-9464-1608 ·
  **arXiv:** https://arxiv.org/a/chakrabarti_k_1
- **Confidence in identity: HIGH** — the arXiv author page lists
  *"Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding"*
  directly, alongside three other LLM papers.

---

## Tier 4 — closed

The four outstanding lookups were completed on 2026-09-20, and the one open
identity question was settled. Outcomes:

| Author | Outcome |
|---|---|
| **Brian Sam-Bodden** | **MEDIUM → HIGH.** Chain closed via `bsbodden@integrallis.com` and the `integrallis/act-context` repo → Tier 1 |
| **Niels Mündler-Sasahara** | **HIGH.** Chain closed via `nielstron` → blog.nielstron.de → Tier 1 |
| **Jai Lal Lulla** | **MEDIUM.** Affiliation and field match; no published link → Tier 2 |
| **Ali Arabat** | **MEDIUM.** Affiliation and record match; no published link → Tier 2 |
| **Damon McMillan** | **No profile tied.** HxAI publishes no names → Tier 3, email route only |

### Round 5 additions (same day)

The literature sweep added two papers, so their authors were checked to the same
standard:

| Author | Paper | Outcome |
|---|---|---|
| **Asa Shepard** | probe-and-refine, arXiv:2606.20512 | **HIGH.** Paper → `asashepard/probe-and-refine-tuning` → profile publishes the LinkedIn → Tier 1 |
| **Jeannie Albrecht** | same paper, co-author | **No LinkedIn.** Her faculty page publishes email and phone only → Tier 3 |
| **Mojtaba Shahin** | rule taxonomy, arXiv:2606.12231 | **MEDIUM.** Role and institution match; no published link → Tier 2 |
| **Guangzong Cai** + 3 co-authors | same paper | **No profiles found.** Scholar only → Tier 3 |

Of the **thirteen** people now checked: **five have a verified profile, three are
affiliation matches, four have no LinkedIn at all, and one cannot be identified.**
That distribution is itself the point: this is an academic literature, and more
than half of it is not reachable on LinkedIn.

### Round 7 additions (2026-09-24) — NOT CHECKED, do not tag

Round 7 added one controlled study and several mechanism papers. **We did no
author lookups for them.** Credit these authors by paper only; tagging any of them
would be a guess.

| Paper | Authors (from the arXiv page) | Status |
|---|---|---|
| *Guardrails Beat Guidance*, arXiv:2604.11088 (**S6**, the largest study) | Xing Zhang, Guanghui Wang, Yanwei Cui, Wei Qiu, Ziyuan Li, Bing Zhu, Peiyang He | **absent** — affiliation not verified |
| *The Working Set of a Coding Agent*, arXiv:2608.16630 | Bardia Mohammadi, Lars Klein, Aman Chadha, Akhil Arora, Laurent Bindschaedler | **absent** |
| *Harness-IF*, arXiv:2608.11727 | Zining Huang et al. (11 authors) | **absent** |
| *Skill Issue*, arXiv:2609.12742 | Mykhailo Kozyrev, Andrei Kozyrev, Anton Podkopaev | **absent** |
| *On Randomness in Agentic Evals*, arXiv:2602.07150 | Bjarni Haukur Bjarnason, André Silva, Martin Monperrus | **absent** |

---

## Institutions — low risk, easy to verify

Safer than an individual if you are unsure. Search LinkedIn for the official page
and confirm the verified badge before tagging:

- **ETH Zürich** — Gloaguen, Mündler-Sasahara et al., the central study
- **Singapore Management University** — Lulla and Treude
- **Heidelberg University** — Baltes
- **IIT Roorkee** — Khatri
- **ÉTS Montréal (École de technologie supérieure)** — Arabat and Sayagh
- **Williams College** — Shepard and Albrecht, the probe-and-refine study
- **Wuhan University** — Cai, Liang et al.; **RMIT University** — Shahin
- **HxAI**, Melbourne — McMillan; no individual is identifiable, so the
  organisation is the only safe credit

---

## Ready-to-paste credit line

> This review rests on work by Thibaud Gloaguen, Niels Mündler-Sasahara and
> colleagues at the SRI Lab, ETH Zürich; Prakhar Khatri; Brian Sam-Bodden;
> Asa Shepard and Jeannie Albrecht at Williams College; Kushal Chakrabarti;
> Ali Arabat and Mohammed Sayagh; Damon McMillan at HxAI; Xing Zhang and
> colleagues; Bardia Mohammadi and colleagues; and Jai Lal Lulla, Sebastian
> Baltes, Christoph Treude and co-authors. All of it is open-access on
> arXiv, and the ETH harness is public under MIT. Any errors in the synthesis are
> mine, not theirs.

**Suggested tagging order for a post** (highest verified confidence first):
Asa Shepard → Brian Sam-Bodden → Prakhar Khatri → Niels Mündler-Sasahara →
Sebastian Baltes → ETH Zürich → *(Jai Lal Lulla, Ali Arabat and Mojtaba Shahin
only once you have eyeballed the profiles; never Damon McMillan)*.

Shepard leads because his paper is the one that changed the review's conclusion,
and because a student's work is the easiest to under-credit.

---

## One courtesy note

Three of these studies report **null or negative** results, and the whitepaper
argues that most of the field's point estimates cannot be distinguished from
noise. If you tag the authors, it is worth making clear in the post that the
critique is of *the practice*, not of *their work* — their papers are the reason
the critique can be made at all, and Gloaguen et al.'s is an award-winning paper
whose own abstract states the nuance most commentary drops.

**And do not flatten the one positive result into the story.** Shepard &
Albrecht's paper reports a significant gain, and an earlier draft of this review
would have had to be rewritten around it — which it was. A post that cites all
six studies as if they agreed would misrepresent his, and his is the one that
made the argument honest.

---

## Copy-paste connection notes

LinkedIn caps an invitation note at **300 characters** (and free accounts get a
limited number of noted invites per month). All seven below are under the cap;
the count is given after each.

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

### Brian Sam-Bodden — confidence HIGH
https://www.linkedin.com/in/sambodden

> Hi Brian - "What Context Does a Coding Agent Actually Need to Act?" reframed a review I've been doing on repository context files: the 4/45 vs 27/45 result, and the temperature-0 noise floor under every small effect here. Thanks for pre-registering it. Would be glad to connect.

*(278 chars. The earlier draft opened with "if you're the author of" because the
identity was unconfirmed; that hedge is no longer needed — the chain closed on
2026-09-20. The note thanks him for the pre-registration because his registered
hypothesis **failed** and he published it anyway, which is the rarer thing.)*

### Asa Shepard — confidence HIGH
https://www.linkedin.com/in/asa-shepard/

> Hi Asa - I've been compiling the evidence on whether repository context files actually help coding agents, and probe-and-refine is the only study I found with a significance-tested gain. The coverage-versus-precision split changed how I read the rest of it. Would be glad to connect.

*(283 chars. Accurate and specific: his is the only one of the five ablations with
a significant positive result, and the coverage/precision decomposition is the
part that reconciles it with the four nulls. Note it says "the only study I found"
— three rounds of search missed this paper for three months, so the hedge is
honest rather than modest.)*

### Niels Mündler-Sasahara — confidence HIGH
https://www.linkedin.com/in/niels-muendler

> Hi Niels - I've been compiling the evidence on whether repository context files help coding agents, and your AGENTS.md evaluation is the backbone of the review. The distinction it draws - instructions followed, repository overviews not - is the part most commentary drops. Would be glad to connect.

*(298 chars — close to the cap; check it pastes whole. He is second of five
authors, so the note credits "your evaluation" as the team's paper and makes no
claim about who led it. This is the same paper Gloaguen first-authored, so do not
send both notes as if they were separate results.)*

### Jai Lal Lulla — confidence MEDIUM, eyeball the profile first
https://www.linkedin.com/in/jai-lulla-764457206/

> Hi Jai - I've been reviewing the evidence on repository context files for coding agents. Your AGENTS.md efficiency study measures the operational side - runtime and tokens rather than success rate - and keeping those two apart mattered for the review. Would be glad to connect.

*(277 chars. Accurate and deliberately narrow: his paper reports −28.64% runtime
and −16.58% output tokens but claims only "comparable task completion behavior",
so the note credits the efficiency finding and does not imply a correctness
result the paper never measured.)*

### Ali Arabat — confidence MEDIUM, eyeball the profile first
https://ca.linkedin.com/in/ali-arabat-206906170

> Hi Ali - I've been compiling the evidence on whether instruction files help coding agents. Your MSR 2026 study is the largest sample I found, and the finding that about as many projects got worse as better shaped the conclusions. Would be glad to connect.

*(Mojtaba Shahin has no note here: his paper is supporting evidence rather than
one of the five ablations, and he is fifth author on it. Tag Wuhan University
instead, or nobody.)*

*(255 chars. His headline result is close to a coin flip — 27.7% of projects up
at least 20 points, 26.35% down — so the note states that plainly rather than
dressing it up as a positive finding. "Largest sample I found" is true: 15,549
PRs across 148 projects.)*

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

### Jeannie Albrecht
No LinkedIn. Her faculty page gives an institutional address for exactly this
purpose: `jeannie@cs.williams.edu`. Her co-author Asa Shepard is on LinkedIn, so
the paper is reachable either way — but she is the senior author and a short
academic email costs nothing:

> Subject: Probe-and-refine tuning
>
> Dear Professor Albrecht,
>
> I've been putting together a review of whether repository context files help coding agents, and your paper with Asa Shepard is the only one of the six controlled studies I found with a significant head-to-head gain. The separation of coverage from precision is what let me reconcile it with the null results, rather than having to pick a side.
>
> Thank you for putting the code and the probes in the open.
>
> Best regards,
> Marcel Petrick

### Damon McMillan
No identifiable profile. HxAI names nobody publicly and gives one address, which
is the only safe channel: `research@h-x.ai` (Melbourne, Australia).

> Subject: Your factorial study of CLAUDE.md file structure
>
> Hello,
>
> I've been putting together a review of whether repository context files help coding agents, and arXiv:2605.10039 is the study I cite for the structural variables — the affirmative-null Bayes factors on file size and conflicting instructions, and the within-session compliance decay, which is the only effect in that design that survived.
>
> I could not find an individual profile to credit, so the review credits HxAI. If Damon McMillan would prefer to be named or tagged directly, I'm happy to correct that.
>
> Best regards,
> Marcel Petrick
