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
