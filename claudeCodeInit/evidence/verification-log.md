# Verification log

Claims that carry weight in `results.md` were re-fetched from the primary source
by the lead session rather than accepted from a subagent summary. This file
records what was checked and what came back.

| Claim | Source | Checked | Outcome |
|---|---|---|---|
| Gloaguen et al., AGENTS.md ablation: no general success gain, >20% cost | arXiv:2602.11988 | abstract re-fetched | **Confirmed.** Abstract verbatim: *"providing context files does not generally improve task success rates, while increasing inference cost by over 20% on average."* Plus the key qualifier the secondary summaries omit: *"instructions in the context files are well followed by coding agents, repository overviews, although popular and recommended by model providers, are not helpful."* Authors: Gloaguen, Mündler, Müller, Raychev, Vechev. v1 2026-02-12, v2 2026-06-23. |
| Lulla et al., AGENTS.md efficiency: −28.64% runtime, −16.58% output tokens | arXiv:2601.20404 | abstract re-fetched | **Confirmed for the numbers**, and confirmed for the limitation: the abstract claims only *"maintaining a comparable task completion behavior"* — correctness/success rate is **not** a measured primary metric. 10 repos, 124 PRs, Codex + Claude Code. v1 2026-01-28, v2 2026-03-30. |
| Arabat & Sayagh, instruction files ≈ coin flip on merge rate | arXiv:2606.13449 | abstract re-fetched | **Confirmed.** 15,549 agentic PRs, 148 projects, AIDev dataset. 27.7% of projects +≥20pt merge rate, 26.35% −≥20pt. MSR 2026. Moderator: *"Projects that managed to increase their merge rate have substantially longer instruction files, which are also well structured into a higher number of sections and sub-sections."* |
| `/init` prompt text; new gated `/init`; audit doctrine; load_reason enum | Claude Code binary v2.1.278 | extracted locally | **Confirmed** — see `primary-binary-extracts.md`. Reproducible with the commands recorded there. |
| CLAUDE.md sits in the cached "project context" layer | code.claude.com/docs/en/prompt-caching | subagent fetch | Accepted; corroborated by a second independent Anthropic source (claude.com/blog, prompt-caching post). Not independently re-fetched by the lead session — flagged as vendor-sourced. |

## Notes on things NOT verified

- The exact wording of secondary press coverage of arXiv:2602.11988 ("reduces
  success rates by up to 3%") was reported by a subagent as differing from the
  abstract. The abstract's own framing is "does not generally improve"; the
  per-condition figures (−0.5% SWE-bench Lite, −2% / +4% on AGENTBench) come from
  the paper body, which was not fetched in full. Treat the body figures as
  second-hand until someone reads the PDF.
- arXiv:2605.26177 (RepoMirage) and arXiv:2606.29718 were reported at
  search-snippet level by the subagent and are cited here as suggestive only.

## Conflicts between independent research passes (unresolved)

Two research passes read the body of arXiv:2602.11988 and reported **incompatible**
figures. Neither is accepted as fact in `results.md`; both are recorded here.

| Quantity | Pass A | Pass B | Status |
|---|---|---|---|
| Effect of LLM-generated context file | −0.5% (SWE-bench Lite), −2% (AGENTBench) | −0.5% to −2%, **but also "+2.7% even with no pre-existing docs"** | The +2.7% figure contradicts the negative headline and is **not** in the abstract. Not used. |
| Significance | not reported | p=0.87 and p=0.37, not significant | Plausible and consistent with the abstract's "does not generally improve", but unverified. |
| Reasoning-token inflation | "20–23% cost" | "14–22% reasoning tokens, >20% inference cost, 2–4 extra steps" | Compatible in spirit. Only the abstract's ">20% inference cost" is treated as established. |
| Author affiliation | ETH Zurich SRI Lab **+ LogicStar.ai** (Müller CTO, Raychev Chief Architect) | ETH Zurich SRI Lab, "no COI apparent" | Lead session fetched the SRI Lab page: it lists **ETH Zürich SRI Lab only**, no LogicStar mention. The LogicStar tie is real for those individuals historically but is **not** declared on the paper page. Recorded as "academic, with commercially-active co-authors" rather than asserting an undisclosed COI. |

**Resolution rule applied throughout `results.md`:** where passes disagree on a
number from a paper body that was not fetched in full, only the **abstract-level**
claim is stated as established, and the body-level figures are marked second-hand.

## Additional verification by the lead session

| Claim | Source | Outcome |
|---|---|---|
| Khatri, no measurable correctness effect, 288 runs | arXiv:2607.27250 | **Confirmed.** Abstract verbatim: *"Context strategy does not measurably move correctness on either agent (bounded to <=10-15pp via equivalence testing)."* Claude Code + Codex, 17 tasks, 3 repos, 288 evaluated runs, gold-test evaluation, submitted 2026-07-28. Also confirms the manipulation probe: *"the real AGENTS.md never converts a near-miss to a pass on either agent."* |
| Gloaguen et al. venue/affiliation | sri.inf.ethz.ch publication page | **Confirmed.** SRI Lab, ETH Zürich. Venue: MemAgents @ ICLR 2026, **Oral & Runner-up Best Paper**. |

## Claims explicitly rejected as unreliable

- **"No CLAUDE.md performed better in 5 of 8 tests"** (chaseai.io, attributed to
  "ETH Zurich research"). This figure appears nowhere in arXiv:2602.11988. The
  publisher sells Claude Code consulting. **Do not cite.**
- **"A 2025 GitHub developer survey found 30%+ fewer throwaway completions"** —
  traces to no actual GitHub survey; appears to be content-farm fabrication.
  **Do not cite.**
- **"Hundredfold gap in tool-invocation rates" (1.6x vs <0.01x)** — reported in a
  Substack post; the 1.6x half matches Gloaguen et al.'s tool-adoption figure, the
  "<0.01x" half has no traceable source. Cite only the 1.6x, as second-hand.

---

# Round 2: full-text reads

Round 1 read only abstracts. Round 2 read all four ablation papers in full
(three via arXiv HTML, McMillan via direct PDF page reads). This **materially
revised** the picture, and not in one direction.

## Corrections to round 1

| # | Round-1 claim | Full-text finding | Effect |
|---|---|---|---|
| 1 | "p=0.87 / p=0.37, not significant" attributed to Gloaguen | **The paper contains no significance testing anywhere.** It states: *"We sample completions for each agent once."* Single run per instance, no CIs, no tests. | The p-values were **fabricated** by a round-1 pass. They never entered `results.md` because the log marked them unverified. S1 is **weaker** than round 1 implied. |
| 2 | Gloaguen's success-rate figures (−0.5%, −2%, +4%) read as a results table | Success rates appear **only as bar charts (Figure 3)**, not as a numeric table. The percentages come from prose. | Numbers stand, but they are prose-level, not table-level precision. |
| 3 | "Instructions help, repository overviews don't" read as a content ablation | **It is not an ablation.** Two separately-instrumented analyses with *different proxy metrics*: overviews judged by time/steps-to-first-relevant-file-touch; instructions judged by tool-invocation counts (uv used 1.6×/instance when mentioned vs <0.01× when not; repo-specific tools 2.5× vs <0.05×). **Neither uses task success rate.** | The finding is real and pointed, but round 1 compressed two qualitative analyses into a clean ablation table **that does not exist**. Must be restated as proxy-based. |
| 4 | "+2.7%" dismissed as contradictory and unused | **Located and reconciled.** It is a *third condition*: repos with all markdown, example code and `docs/` folders **stripped**. Subsection title: *"Context files are redundant documentation."* Quote: *"where context files are the only source of documentation available, LLM-generated context files not only consistently improve performance by 2.7% on average, but also outperform developer-written documentation."* | **Not a contradiction — a key finding.** Both round-1 passes were each reading a different subsection. This is now central to the analysis. |
| 5 | Gloaguen's human-written arm "~+4%" | More precisely: *"developer-provided context files outperform the LLM-generated ones for all four agents... and improve the performance compared to no context files for all agents **but Claude Code**."* | Claude Code is the **exception** — worth flagging in a Claude Code dossier. |
| 6 | Khatri "no effect, bounded ≤10–15pp" treated as strong | True, but the paper's own power analysis gives **minimum detectable effect ≈30pp**, and says reaching 80% power at 10pp needs ~120–200 tasks (it has 15–17). | A null from an underpowered study. **Weaker** than round 1 implied. |
| 7 | McMillan treated as one null among several | It is by far the **most statistically rigorous** of the four: binomial GLMMs, LRTs, Benjamini-Hochberg FDR, Bayesian companion with Savage-Dickey Bayes factors giving **affirmative** nulls for size (BF₁₀=0.096) and conflict (BF₁₀=0.053). But the outcome is a **synthetic marker** (`// @tracked` comment), not task success. Baseline without a config file: **0/524 compliance**, confirming the marker is genuinely instruction-driven. | **Stronger** methodologically, **narrower** in construct. |
| 8 | Lulla's efficiency win taken at face value | Correctness was checked only by *"manual sanity check"* of **50 of 124** samples. The paper's own scope note: *"A comprehensive evaluation of the output quality... is beyond the scope of this paper."* | Admits an unexcluded alternative: the agent may do **less thorough work** when the file is present, on tasks (≤100 LOC, ≤5 files) too small to expose that as a quality loss. |

## Gloaguen Table 2 (steps / cost), as extracted

| Condition | Sonnet-4.5 | GPT-5.2 | GPT-5.1-mini | Qwen3-30B |
|---|---|---|---|---|
| SWE-bench, none | 54.4 / $1.30 | 12.5 / $0.32 | 40.9 / $0.18 | 29.7 / $0.12 |
| SWE-bench, LLM-gen | 57.2 / $1.51 | 12.7 / $0.43 | 45.2 / $0.22 | 32.2 / $0.13 |
| AGENTbench, none | 40.7 / $1.15 | 12.1 / $0.38 | 40.6 / $0.18 | 31.5 / $0.13 |
| AGENTbench, LLM-gen | 46.5 / $1.33 | 13.1 / $0.57 | 46.9 / $0.20 | 34.2 / $0.15 |
| AGENTbench, human | 45.3 / $1.30 | 13.6 / $0.54 | 46.6 / $0.19 | 32.8 / $0.15 |

## Khatri Table 1 (pass rate), as extracted

| Strategy | Claude Code (15 tasks) | Codex (17 tasks) |
|---|---|---|
| none | 53.3% (24/45) | 58.8% (30/51) |
| always_on | 55.6% (25/45) | 56.9% (29/51) |
| selective | 55.6% (25/45) | 52.9% (27/51) |
| omnibus p | 1.000 | 0.66 |

## McMillan main effects (instruction compliance rate)

| Variable | Levels | ICR | Test |
|---|---|---|---|
| Size | 25 / 100 / 250 / 500 lines | 60.0 / 65.2 / 67.7 / 64.0% | χ²=5.16, df=3, p=0.16; **BF₁₀=0.096** |
| Position | top → bottom (P1–P5) | 67.7 / 63.2 / 64.0 / 64.0 / 61.8% | χ²=1.47, df=4, p=0.83 |
| Architecture | single / +AGENTS.md / +nested | 67.7 / 68.2 / 61.7% | χ²=3.29, df=2, p=0.19 |
| Conflict | absent / present | 63.7 / 64.1% | χ²=0.10, df=1, p=0.76; **BF₁₀=0.053** |

Task identity dominates everything: χ²=355.16, p=1.4×10⁻⁷⁵.

## Code and data availability

- Gloaguen: https://github.com/eth-sri/agentbench
- Khatri: https://github.com/codeprakhar25/context-files-coding-agents
- Lulla: Zenodo DOI 10.5281/zenodo.18348507
- McMillan: no availability statement found

## Round 2 gap-hunt: two findings verified personally by the lead session

| Claim | Source | Outcome |
|---|---|---|
| CLAUDE.md files grow +226% over their lifetime; deletion hazard falls with age | [arXiv:2608.11095](https://arxiv.org/abs/2608.11095) | **Confirmed.** Kushal Chakrabarti, *"Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding"*, submitted 2026-08-11. **247,694 instruction lifetimes across 1,867 repositories.** Agentic prompts more than tripled (+226%); net **+4.9 instructions per commit**; deletion log-hazard **−0.032/commit** (older instructions get stuck). Mechanism named *"catastrophic remembering"* — the inverse of catastrophic forgetting: appending is cheap, deleting risks regressions with verification cost **O(2^\|D\|)**. Proposed fix (prompt comments encoding rationale): removes **99.3%** of excess instructions (+211.3% growth → +1.4%) on IFEval; **+23.1%** instruction-following on WildIFEval. |
| "~9% run-to-run variance at temperature 0" | [arXiv:2607.09691](https://arxiv.org/abs/2607.09691) | **Confirmed — and the paper was mischaracterised by the research pass.** It is not a variance paper. Brian Sam-Bodden, *"What Context Does a Coding Agent Actually Need to Act?"*, submitted 2026-06-19. It is the **single most mechanistically relevant paper in the whole dossier.** See below. |

### Sam-Bodden, arXiv:2607.09691 — why this matters more than the pass realised

Design: holds localization fixed with an oracle, varies **only how code is represented**, scores against real issue resolution on SWE-bench Verified. Registered hypothesis, frozen protocol.

Verbatim from the abstract:

> *"The signal lives in the code being edited itself: natural-language summaries of it answer almost none of the behavioral questions that the source answers (**4/45 vs. 27/45**, held-out repositories, independent judge), and **the gap belongs to the representation, not the summarizer — a frontier model's summaries score exactly as poorly as a 3B model's**."*

> *"rendering a file's remainder as UML skeletons and signatures **resolves no more issues than deleting that remainder outright** (N=70, exact McNemar p=0.75). **That was our registered hypothesis, and it failed.**"*

> *"Compressed context, meanwhile, matches whole files at a third of the tokens: a resolved issue costs **19K context tokens, not 94K**."*

> *"temperature-0 API inference flips **~9% of per-instance outcomes between byte-identical runs**. That is a **noise floor under every small effect reported on this benchmark, including ours**."*

**Two consequences for this dossier:**

1. **It supplies the missing mechanism.** Gloaguen measured *that* repository overviews don't help (via a proxy metric). Sam-Bodden shows *why*: a natural-language summary of code is an impoverished representation that loses the behavioural information an agent needs, and this is a property of the representation, **not fixable by writing a better summary**. The `/init`-generated architecture section is exactly such a summary.
2. **It disqualifies most of the literature's headline numbers.** The effects under debate — −0.5%, −2%, +2.7%, +4% — are all **smaller than the author-measured ~9% noise floor on this very benchmark**, and Gloaguen ran **one sample per instance**. This does not mean context files help; it means the small single-run point estimates on both sides should not be treated as measurements at all.

## Additional data-quality hazards found in round 2

- A blog attributes Gloaguen's numbers to a **"Kocetkov et al."** paper. **No such paper exists.** AI-generated secondary-source hallucination.
- **"Context rot" is now two unrelated things.** Chroma (2025) coined it for performance degradation as context *length* grows. Treude & Baltes ([arXiv:2606.09090](https://arxiv.org/abs/2606.09090)) reuse the label for documentation-vs-code *staleness*. Different phenomena, same name — a citation-search hazard.

## Round 4 (2026-09-20): author identity verification

The four outstanding author lookups from `whitepaper_authors.md` Tier 4, plus the
one open identity question. Same standard as the rest of this file: a profile is
HIGH only if something the person controls publishes the link.

| Person | Route attempted | Outcome |
|---|---|---|
| **Brian Sam-Bodden** (arXiv:2607.09691) | paper HTML → author block → GitHub | **MEDIUM → HIGH.** Author block: *"Brian Sam-Bodden, Integrallis Software, bsbodden@integrallis.com"*, footnote *"Code and data: https://github.com/integrallis/act-context"*. That repo is owned by the `integrallis` org; `github.com/bsbodden` lists company `@integrallis`, is a member of the org, and publishes `linkedin.com/in/sambodden` itself. The round-3 doubt ("his GitHub shows no coding-agent work") was a false negative: the paper's code lives under the company org, not his user account. |
| **Niels Mündler-Sasahara** (arXiv:2602.11988, 2nd of 5) | SRI Lab page → handle → personal site | **HIGH.** SRI page lists no socials but uses the handle `nielstron`; `github.com/nielstron` gives the full name, ETH Zürich, and links `blog.nielstron.de`; that site names him *"PhD Student at ETH Zurich under Martin Vechev"* and publishes `linkedin.com/in/niels-muendler`. Authorship re-checked against the arXiv abstract page: Gloaguen, Mündler, Müller, Raychev, Vechev. |
| **Jai Lal Lulla** (arXiv:2601.20404, 1st author) | paper PDF → Scholar → LinkedIn search | **MEDIUM.** Paper PDF (`assets.empirical-software.engineering`, extracted with `pdftotext`): *"Jai Lal Lulla, Singapore Management University, jailal.l.2025@phdcs.smu.edu.sg"*. Scholar `U6GH2EMAAAAJ` has a verified `smu.edu.sg` address and lists the paper. A LinkedIn profile with the matching institution exists (`/in/jai-lulla-764457206/`) but **no account of his publishes it**. The paper's appendix (Zenodo `10.5281/zenodo.18348507`) carries no personal links; the SMU PhD-student directory page returned no readable content. |
| **Ali Arabat** (arXiv:2606.13449, 1st author) | paper HTML → supervisor site → LinkedIn search | **MEDIUM.** Paper: *"Ali Arabat, Mohammed Sayagh, École de Technologie Supérieure, ali.arabat.1@ens.etsmtl.ca"*, replication package Figshare `10.6084/m9.figshare.30951143`. Candidate `ca.linkedin.com/in/ali-arabat-206906170` states the same institution and matches his known record (EMSE work with Sayagh on OpenStack cross-component changes). His supervisor's site `msayagh.github.io` **names no students**, and no personal site or GitHub was found, so the chain has no final link. `aliarabat.github.io` remains 404. |
| **Damon McMillan** (arXiv:2605.10039) | paper PDF → HxAI site | **No identification possible — recorded as a result, not a gap.** The paper's author block is two lines, *"Damon McMillan / HxAI Australia"*; a full-text grep of the PDF found no email, ORCID, repository or data-availability statement. `h-x.ai` calls itself an independent research organisation, attributes work to the collective *"HxAi Research Team"*, names no individual, and gives one address: `research@h-x.ai`, Melbourne. Several Australians of that name exist on LinkedIn, one of them topically plausible (Deloitte Digital, posts about production agents) — **plausibility is not evidence, and no link was recorded.** |

**Method note.** LinkedIn still blocks automated fetching, so every profile URL
above came from search-result metadata, not from reading the page. That is why
an affiliation match caps at MEDIUM: the grade reflects the *chain*, not the
plausibility. Two PDFs that `WebFetch` could not decode were extracted locally
with `pdftotext` — that is the reliable route for arXiv PDFs.

## Round 5 (2026-09-20): literature re-sweep with a restored search budget

Round 3 ended with the search budget exhausted (200/200). With the limit raised,
the field was swept again. **Three papers were found that the first three rounds
missed**, one of which changes a headline claim. Every abstract below was fetched
from `arxiv.org/abs/<id>` and extracted from the raw HTML `<blockquote
class="abstract">` — not read through a summarising model, and not taken from a
search snippet.

| Paper | Status | Verbatim evidence |
|---|---|---|
| **Shepard & Albrecht**, *Probe-and-Refine Tuning of Repository Guidance for Coding Agents*, [arXiv:2606.20512](https://arxiv.org/abs/2606.20512), submitted 2026-06-18 (v2 06-19), cs.SE | **Added as the fifth controlled ablation (S5).** Changes §4 of `results.md`, the TL;DR, and figure 1. | *"On SWE-bench Verified across four independent trials with Qwen3.5-35B-A3B at 200 steps, probe-and-refine achieves 33.0% mean resolve rate vs. 28.3% for the static knowledge base used to initialize it and 25.5% for an unguided baseline (p < 0.001 for both probe-and-refine contrasts)."* · *"The improvement comes from coverage rather than precision: refined guidance produces evaluable patches for 14.5 percentage points (pp) more instances while per-patch precision remains statistically constant (~59%, p = 0.119), showing that improved guidance helps agents reach the correct file rather than improving the quality of the changes they make."* · *"we show that how the guidance is produced is the decisive variable"* · *"a cross-model experiment with NVIDIA-Nemotron-3-Nano-30B-A3B finds that the tuning loop degrades when the model cannot generate sufficiently diagnostic output"* |
| **Cai, Li, Liang, Li, Shahin**, *Rule Taxonomy and Evolution in AI IDEs*, [arXiv:2606.12231](https://arxiv.org/abs/2606.12231), submitted 2026-06-10 | **Added as observational corroboration** of the ratchet (§7 of the whitepaper) and as a second adherence result. | *"mining 83 open-source projects and extracting 7,310 rules"* · *"our analysis of 1,540 rule evolution events revealed that rules are updated frequently… rule evolution is primarily driven by constructive context expansions (29.17%) and enrichments (26.59%)"* · *"surveyed developers reported modifying rules primarily to correct AI errors (77.78%), typically by adding new negative constraints rather than editing existing ones"* · *"an artifact compliance assessment of 160 rule evolution events revealed that updating rules significantly improves the adherence of software artifacts, with the average artifact compliance rate increasing by 22.99% (from 49.14% to 72.13%) following an update"* |
| **Vasilopoulos**, *Codified Context*, [arXiv:2602.20478](https://arxiv.org/abs/2602.20478), submitted 2026-02-24 | **Cited as illustrative only.** Single-project case study; no controlled comparison, so it cannot bear weight. | *"a 108,000-line C# distributed system"*, *"283 development sessions"*, *"four observational case studies"*. No success or cost measurement. |

### Checked and deliberately not used

- [arXiv:2608.21884](https://arxiv.org/abs/2608.21884) (Loop Engineering),
  [arXiv:2607.00911](https://arxiv.org/abs/2607.00911) (agent skills),
  [arXiv:2608.04661](https://arxiv.org/abs/2608.04661) (agent plans) — all by the
  Lulla/Treude/Baltes group, all **adoption studies that measure no task
  outcome**. Listed in `results.md` §13 so the next reader does not re-check them.
- [arXiv:2604.14228](https://arxiv.org/abs/2604.14228) (*Dive into Claude Code*) —
  a design-space tech report, explicitly not an empirical measurement.

### One claim in this review was weakened by round 5

The earlier draft said every published point estimate sits inside the ±9 pp
per-instance flip rate, and treated that as settling the question. The first half
is still true — S5's contrasts are +2.8 and +7.5 pp. **The inference was too
strong.** A per-instance flip rate bounds what a *single run* establishes; it is
not a minimum detectable effect, and a mean over repeated trials has a smaller
standard error. S5 resolves a +7.5 pp difference at *p*<0.001 from inside the
band. The claim now reads: the floor disqualifies **single-run point estimates**,
not the practice. Figure 1 was rebuilt to group the effects by design rather than
by study, because that is the distinction that decides which numbers are
measurements.

### Method note

Two arXiv PDFs (`2601.20404`, `2605.10039`) could not be decoded by the fetching
tool and were extracted locally with `pdftotext`; that is the reliable route, and
it is how the Lulla author block and the McMillan "HxAI Australia" affiliation
were read. For abstracts, `curl` plus a regex over the raw HTML avoids putting a
summarising model between the source and the log.

## Round 6 (2026-09-20): authors of the round-5 papers

Round 5 added two papers to the review, so their authors were checked to the same
standard as the rest of `whitepaper_authors.md` — a profile is HIGH only if
something the person controls publishes the link.

| Person | Route | Outcome |
|---|---|---|
| **Asa Shepard** (arXiv:2606.20512, 1st author) | paper PDF → stated repo → GitHub → profile | **HIGH.** `pdftotext` on the PDF gives *"Asa Shepard / Williams College / as66@williams.edu"* and, in the body, *"Code: https://github.com/asashepard/probe-and-refine-tuning"*. That account **owns and pins** a repo of exactly that name, described as *"Repo for the research paper 'Probe-and-Refine Tuning of Repository Guidance for Coding Agents'"*, and publishes `linkedin.com/in/asa-shepard/` on its own profile. Identical in form to the Khatri chain. |
| **Jeannie Albrecht** (same paper, senior author) | faculty page | **No LinkedIn — a result, not a gap.** `cs.williams.edu/~jeannie/` publishes an email, a phone number, an office, a CV and a publication list, and links no social profile of any kind. Title verified: *"Robert G. Scott '68 Professor"*, Department of Computer Science, Williams College. The department's own profile page (`csci.williams.edu/people/faculty/jeannie-albrecht/`) returns **HTTP 403** to automated fetching, so her personal page is the usable source. |
| **Mojtaba Shahin** (arXiv:2606.12231, 5th of 5) | paper → search metadata | **MEDIUM.** The paper places him at *"School of Computing Technologies, RMIT University, Melbourne"*; a profile stating the same role and institution exists at `au.linkedin.com/in/mojtaba-shahin-659b87b8`, but the URL came from search metadata, not from anything he publishes. Same cap as Lulla and Arabat. |
| **Guangzong Cai, Ruiyin Li, Peng Liang, Zengyang Li** (same paper) | search | **No profiles found.** Affiliations verified from the paper (Wuhan University; Central China Normal University). Peng Liang is publicly visible via Scholar (`user=76CoujsAAAAJ`) but no LinkedIn surfaced. Recorded as absent rather than guessed. |

**Running tally across all six rounds — thirteen people checked:** five verified
(HIGH), three affiliation matches (MEDIUM), four with no LinkedIn at all, one who
cannot be identified from any published source. The proportion is the finding: a
review of an academic literature cannot be credited entirely on LinkedIn, and
pretending otherwise is how the wrong person gets tagged.

## Round 7 (2026-09-24): re-sweep, vendor re-check, and a plain-language rewrite

Three parallel research passes (controlled studies; mechanism; vendor docs and
practice), then every candidate re-verified by the lead session: abstracts via
`curl https://arxiv.org/abs/<id>` and a regex over the raw `<blockquote
class="abstract">`, full text via `pdftotext` where a number was load-bearing.

### Added

| Paper | Role | Verbatim evidence (raw abstract unless stated) |
|---|---|---|
| **Zhang, Wang, Cui, Qiu, Li, Zhu, He**, *Guardrails Beat Guidance*, [arXiv:2604.11088](https://arxiv.org/abs/2604.11088), 2026-04-13, v2 2026-05-28 | **Sixth controlled ablation (S6).** The largest; the only one on a frontier agent with a positive direction. | *"Random rules improve a coding agent's task performance as much as expert-curated ones (both $+13.8$pp on a discriminative subset of SWE-bench Verified)"* · *"over 5{,}000 agent runs of Claude Code with Claude Opus 4.6"* · *"pass rates remain stable across rule counts from 0 to 50"*. **Full text (pdftotext):** *"retain 58 discriminative tasks (those solved 1 or 2 out of 3 times, i.e., 30–70% baseline pass rate)"*; *"no condition is significantly different from any other (Cochran's Q = 4.70, p = 0.697). The closest pairwise contrast is random vs. baseline (McNemar p = 0.077"*; *"a binomial sign test on the seven directions gives p = 0.008"*; Table 2: baseline 50.0, random 63.8 (*p*=.077), curated 63.8 (*p*=.115); *"always-pass and always-fail tasks behave identically across conditions"*. The ≈+1.6 pp full-benchmark figure is **our arithmetic** (13.8 × 58/500), not the paper's. |
| **Mohammadi, Klein, Chadha, Arora, Bindschaedler**, *The Working Set of a Coding Agent*, [arXiv:2608.16630](https://arxiv.org/abs/2608.16630), 2026-08-17 | Mechanism: stale files hurt | *"where standard and code disagree, agents follow the standard even when it prescribes the worse code, so a stale convention file costs more than no file"* · *"seven models and five harnesses"* |
| **Huang et al.**, *Harness-IF*, [arXiv:2608.11727](https://arxiv.org/abs/2608.11727), 2026-08-12 | Mechanism: adherence | *"Across 12 frontier models, accuracy spans 72.1-85.9% and AP-Acc 66.1-78.6%; every model is worse on against-prior rules, by 3.6 to 7.4 points (mean 5.81)"* |
| **Kozyrev, Kozyrev, Podkopaev**, *Skill Issue*, [arXiv:2609.12742](https://arxiv.org/abs/2609.12742), 2026-09-11 | Related controlled study (SKILL.md, not a context file) | *"the documents GEPA finds raise this score by $4.9$pp on average"* · *"it cannot be separated from the agent's run-to-run variance"* |
| **Bjarnason, Silva, Monperrus**, *On Randomness in Agentic Evals*, [arXiv:2602.07150](https://arxiv.org/abs/2602.07150), v3 2026-03-25 | Noise | *"single-run pass@1 estimates vary by 2.2 to 6.0 percentage points"* · *"reported improvements of 2--3 percentage points may reflect evaluation noise"* |
| **Yang & Ding**, *Signal or Noise?*, [arXiv:2608.23067](https://arxiv.org/abs/2608.23067); **Wen et al.**, *MTAC-IFBench*, [arXiv:2609.14992](https://arxiv.org/abs/2609.14992); **Yang, He, Zhou**, [arXiv:2607.26819](https://arxiv.org/abs/2607.26819) | Dossier only (adjacent) | see `results.md` §13 |

### Corrected (see `self-review.md` entries 5–8)

- **AAIF pairing.** Primary source re-fetched (`aaif.io/blog/measuring-agents-md-what-five-runs-show-that-one-doesn-t`): *"On the harder task, the AGENTS.md run looked 44% slower and 41% more expensive for identical output"* (a first single-run attempt); *"On the ambiguous task, it cut wall time 27%, credits 24%"*; *"On the multi-file task, the median win was smaller, 9 to 10%"*. The review had paired numbers from different tasks.
- **Second `/init`.** Memory docs: *"For an interactive multi-phase flow instead, set the `CLAUDE_CODE_NEW_INIT` environment variable to `1` before you run `/init`"*. Binary v2.1.282: `CLAUDE_CODE_NEW_INIT||x("tengu_slate_harbor_experiment",!1)` — still off by default; the "only include what Claude would get wrong without it" prompt unchanged.
- **AGENTS.md in Claude Code.** Changelog 2.1.277, 2026-09-18: *"Added AGENTS.md support: in a project with no CLAUDE.md, Claude Code reads AGENTS.md instead"*.
- **Codex and `CLAUDE.md`.** `developers.openai.com/codex/guides/agents-md` does not contain the string "CLAUDE.md"; lookup order is `AGENTS.override.md`, `AGENTS.md`, then `project_doc_fallback_filenames`.

### Re-checked and unchanged

- **Gloaguen v2** (2026-06-23). Abstract now reads *"does not generally improve task success rates, while increasing inference cost by over 20% on average"*; the quoted *"instructions … well followed … repository overviews … are not helpful"* sentence is unchanged. No artefact quoted the v1 "reduce" wording.
- **Agent READMEs v2** (2026-08-09): *"test procedures (75.9%), implementation details (70.8%), and architecture (68.1%)"*, *"security (14.8%) and performance (14.5%)"* — matches figure 3.
- **Pricing** (Sonnet 5: $2 in, $2.50 cache write, $0.20 cache read); **"target under 200 lines"**; **"Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"**; OpenAI *"Avoid chain-of-thought prompts"* — all still verbatim at source.

### Rejected

- A compliance-decay curve (*"95%+ … 60-80% … 20-60%"*) attributed in a search summary to a practitioner: **no primary source found**. Not used.
- Checked, not used (observational without an outcome, off-topic, or N=1): 2606.15828, 2608.23550, 2609.07360, 2608.10622, 2608.13867, 2609.05510, 2608.13662, 2607.11111, 2602.05892, 2607.10569, 2608.11386, 2606.25257 (study protocol, no results yet).
