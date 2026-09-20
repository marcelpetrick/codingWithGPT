# Does `/init` Help? A Meta-Study of Repository Context Files for Coding Agents

**Marcel Petrick** · **Claude Opus 5**
19 September 2026 · revised 20 September 2026

---

## TL;DR

**Running `/init` and keeping a `CLAUDE.md` does not reliably make a frontier
coding agent succeed more often.** Across the controlled ablations that measured
success, the effect runs from −5.9% to +4%. Every one of those numbers is smaller
than the ~9% of outcomes that flip between *byte-identical* runs at temperature
zero. Most of them come from designs that ran each task once, so they are not
measurements at all.

**One design does find a gain, and it is instructive.** It repeated its trials and
tested significance: **+7.5 pp** on an open mid-size model. But the gain appeared
only after the authors **tuned the guidance against the agent's own failures** —
and it came from reaching the right file, not from writing a better patch.

**Cost is the one effect clearly above the noise.** Context files raise inference
cost by 20–23%.

**The file is two artefacts with opposite signs.** Agents follow **instructions**:
a tool named in the file gets used 1.6× per task, against under 0.01× when it goes
unmentioned. Agents gain nothing from a **repository overview**, because prose
about code answers 4 of 45 behavioural questions where the source answers 27.

**`/init` still earns its place for reasons that were never about task success** —
onboarding, team documentation, and migrating Cursor and Copilot rules. Meanwhile
the performance case for a large always-loaded file has eroded, because Claude
Code grew hooks, skills, subagents and path-scoped rules that hold the same
content more cheaply.

> **Run `/init`, delete the architecture tour, and keep only what the repository
> cannot tell the agent itself.**

---

## 1. The question

Claude Code ships a `/init` command that reads a repository and writes a
`CLAUDE.md`. The agent then loads that file into every later session, in every project,
forever. Practitioners disagree sharply about whether this is leverage or
clutter. This study asks what the evidence actually shows, and — when the answer
turned out to be "not much" — why the feature exists at all.

## 2. Method

Three rounds of research, ten parallel agents, plus two local primary-source
efforts. Round 1 mapped the field (academic literature, vendor documentation,
practitioner grey literature, cross-harness comparison, context economics).
Round 2 closed the gaps round 1 exposed: reading the **full text** of every
controlled study rather than its abstract, hunting for work round 1 missed, and
independently re-verifying the pricing that the cost analysis rests on. Round 3
asked the historical question — why does `/init` exist, and has its value decayed?

**Two further rounds followed first publication.** Round 4 (2026-09-20) verified
the authorship behind every cited paper (`whitepaper_authors.md`). Round 5, the
same day, re-swept the literature with a restored search budget and found three
relevant papers the earlier rounds had missed — including a fifth controlled
ablation that **falsified an inference in the original TL;DR** (§4, and
`evidence/self-review.md` entry 4).

We produced two things locally rather than searching for them:

- **Binary extraction.** We mined the shipped Claude Code executable (v2.1.278)
  with `strings` and byte-offset reads, recovering the literal `/init` prompt, an
  unreleased second `/init` gated behind a feature flag, the CLAUDE.md audit
  doctrine, and the exact loading semantics. This is the artefact itself, not
  documentation about it, and it proved decisive.
- **Corpus measurement.** We measured all 35 agent instruction files under
  `~/repos` (median ≈1,590 tokens, p90 ≈3,300, max ≈6,800).

**Verification discipline.** We did not trust subagent output. We re-fetched every
load-bearing paper from arXiv and checked it against what the pass reported. This
caught: two passes reporting **incompatible** numbers from the same paper body;
one pass reporting **p-values that do not exist** in the paper it cited; one pass
**dismissing a real paper** as an untraceable mis-citation; two widely-circulated
statistics that are **fabricated**; and one vendor figure that **cannot be found
in its own source**. `evidence/verification-log.md` records all of them. A
detailed self-review (`evidence/self-review.md`) corrected three overstatements in
our own first draft.

## 3. The evidence base

**Five** controlled ablations of this exact question exist. All are 2026
preprints or workshop papers. None is journal-published. **None has been
replicated, and none has been formally rebutted.**

| Study | Design | Scale | Measured | Result |
|---|---|---|---|---|
| **Gloaguen et al.**, ETH Zürich, ICLR 2026 workshop (Oral, Runner-up Best Paper) | 4 agent/model combos × 3 conditions × 2 benchmarks. **Single run per instance; no significance testing; success reported only as bar charts.** | 300 + 138 instances | success, steps, cost | No general success gain; **+20–23% cost**. LLM-written −0.5 to −2%; developer-written ≈+4% but **not for Claude Code**. |
| **Khatri** | 3 injection strategies × 2 agents, gold tests, **3 repeats per task**, TOST equivalence testing | 17 tasks, 3 repos, 288 runs | success, latency | **No measurable effect** (≤10–15pp). *Its own power analysis gives a minimum detectable effect ≈30pp.* |
| **Lulla et al.**, ICSE 2026 workshop | paired with/without, isolated containers, small PRs only (≤100 LOC) | 10 repos, 124 PRs | runtime, tokens | **−28.6% median runtime, −16.6% output tokens.** Correctness **spot-checked on 50 of 124**. |
| **McMillan** | factorial: size × position × architecture × contradiction | **1,650 sessions**, 16,050 observations | adherence, via a synthetic `// @tracked` marker | **No structural variable mattered**, with *affirmative* Bayesian nulls (size BF₁₀=0.096; contradiction BF₁₀=0.053). Session length did: **−5.6% odds of compliance per generated function**. |
| **Shepard & Albrecht** | unguided vs static knowledge base vs *probe-and-refine* tuned guidance, **4 independent trials** | SWE-bench Verified, Qwen3.5-35B-A3B, 200 steps | resolve rate, patch precision | **The only positive, significance-tested success effect in the literature.** 25.5% → 28.3% (static) → **33.0%** (tuned), *p*<0.001 for both tuned contrasts. Gain is **coverage, not precision**: +14.5 pp more evaluable patches, per-patch precision flat at ~59% (*p*=0.119). |

Supporting, non-causal: **Arabat & Sayagh** (MSR 2026) on 15,549 agentic PRs found
adopting an instruction file raised merge rate ≥20 points for 27.7% of projects and
**lowered** it for 26.35% — a coin flip. **Cai et al.**
([arXiv:2606.12231](https://arxiv.org/abs/2606.12231)), mining 7,310 rules across 83
projects and surveying 99 practitioners, assessed 160 rule-evolution events and
found artefact compliance rising from 49.14% to 72.13% after a rule update — a
**+22.99-point** improvement in adherence, which is a different outcome from task
success and should not be read as one.

## 4. Finding 1 — most published effects are not measurements

This is the finding that reframes everything else.

Sam-Bodden ([arXiv:2607.09691](https://arxiv.org/abs/2607.09691)) reports, from a
frozen pre-registered protocol on SWE-bench Verified:

> *"temperature-0 API inference flips **~9% of per-instance outcomes between
> byte-identical runs**. That is a noise floor under every small effect reported on
> this benchmark, including ours."*

Every point estimate in the literature — −5.9, −2.0, −1.9, −0.5, +2.3, +2.7, +2.8,
+4.0, +7.5 — sits **inside** that band. And the study producing several of them
sampled each instance **once**, with no significance testing.

Independent corroboration that this field's numbers are fragile: misapplied pass@k
inflates reported scores by 0.85–0.97 absolute, and a single run correlates only
**ρ=0.417** with true repeated-rollout reliability ([arXiv:2608.14711](https://arxiv.org/abs/2608.14711));
run-level pass rates overstate retry-free coverage by up to **17.8pp**
([arXiv:2606.00920](https://arxiv.org/abs/2606.00920)); SWE-bench itself suffers
solution leakage and weak tests ([arXiv:2609.08149](https://arxiv.org/abs/2609.08149)).

A practical demonstration: the Agentic AI Foundation ran the same comparison five
times. One run showed AGENTS.md **44% slower and 41% more expensive**; the five-run
median showed **27% faster and 24% cheaper**. Same task, same setup.

**What the noise floor does and does not disqualify.** This is worth stating
precisely, because it is easy to over-read in the other direction. The ~9% figure
is a **per-instance flip rate**: it bounds what a *single* run can establish about
a *single* instance. It is **not** a minimum detectable effect. Average over
repeated trials and the standard error of the mean shrinks, so a design with
repeats can resolve a difference that is smaller than the flip rate — which is
exactly what Shepard & Albrecht do, reporting *p*<0.001 for a +7.5-point gap over
four trials.

So the band disqualifies **single-run point estimates**, not the practice. Of the
effects in figure 1, the four from a one-sample-per-instance design are not
measurements. Of the six from designs with repeats: four are nulls bounded by
equivalence testing, one is **+7.5 pp at *p*<0.001**, and one — the +2.8 pp
static-guidance contrast — the paper simply does not test.

> **Conclusion.** "Context files don't help" and "context files help" are both
> over-readings. The honest statement is that **nobody has yet measured the
> effect on frontier agents precisely enough to distinguish it from zero** — and that the one study which *did* measure with enough precision found
> a real gain, on a weaker model, from guidance produced in a way no `/init`
> command produces it (§7).

## 5. Finding 2 — the file is two artefacts with opposite signs

Gloaguen et al.'s abstract contains the most useful sentence in the literature:

> *"while **instructions** in the context files are **well followed** by coding
> agents, **repository overviews**, although popular and recommended by model
> providers, **are not helpful**."*

The supporting evidence, read in full, is two *separately instrumented* analyses
using different proxy metrics — not one clean content ablation:

- **Instructions are followed.** `uv` is invoked **1.6× per instance** when named
  in the file versus **<0.01×** when not; repository-specific tools **2.5×** versus
  **<0.05×**.
- **Overviews don't pay.** 8 of 12 developer-written files and **100%** of
  Sonnet-4.5-generated files contained a codebase overview, yet their presence
  *"does not meaningfully reduce"* the number of steps to reach the first relevant
  file.

Crucially, **no study anywhere ablates the two halves against a shared success
metric.** That experiment is cheap, obvious, and nobody has run it. It is the
single most decision-relevant gap in this field.

## 6. Finding 3 — why overviews fail, and why writing a better one won't help

Sam-Bodden supplies the mechanism. He holds localisation fixed with an oracle and varies only how the code is
*presented* to the agent:

> *"natural-language summaries of it answer almost none of the behavioral questions
> that the source answers (**4/45 vs. 27/45**)… and **the gap belongs to the
> representation, not the summarizer — a frontier model's summaries score exactly
> as poorly as a 3B model's**."*

The paper's registered hypothesis — that structured skeletons would beat nothing —
**failed**: rendering a file's remainder as UML skeletons and signatures *"resolves
no more issues than deleting that remainder outright"* (N=70, McNemar p=0.75).

This matters because it forecloses the obvious rebuttal. The problem with the
architecture section `/init` writes is **not** that it is badly written. Prose
about code is a lossy encoding of code, and no author — human or frontier model —
recovers the loss.

## 7. The exception — when guidance *does* move success

One result cuts against the rest, and it is the most methodologically careful of
the five. Shepard & Albrecht
([arXiv:2606.20512](https://arxiv.org/abs/2606.20512)) introduce **probe-and-refine
tuning**: synthetic bug-fix probes *iteratively diagnose and patch a repository's
guidance file*, through single-shot LLM calls with no agent loop during tuning. On SWE-bench Verified with Qwen3.5-35B-A3B, across four independent
trials:

| Condition | Resolve rate |
|---|---|
| Unguided baseline | 25.5% |
| Static knowledge base | 28.3% (not significance-tested) |
| **Probe-and-refine tuned guidance** | **33.0%** (*p*<0.001 vs both) |

Their framing is the useful part:

> *"how the guidance is produced is the decisive variable"*

And the mechanism is precisely located:

> *"The improvement comes from coverage rather than precision: refined guidance
> produces evaluable patches for 14.5 percentage points more instances while
> per-patch precision remains statistically constant (~59%, p = 0.119), showing
> that improved guidance helps agents reach the correct file rather than improving
> the quality of the changes they make."*

**Does this refute §4 and §5? No — it sharpens them.** Three things separate this
result from the null ones:

1. **Model class.** Qwen3.5-35B-A3B is an open mid-size model, not Claude Code or
   Codex. Under the principle in §11, scaffolding pays exactly where the model
   lacks the capability natively. Their own cross-model check supports this from
   the other side: the tuning loop *degrades* on Nemotron-3-Nano-30B, because that
   model "cannot generate sufficiently diagnostic output".
2. **Provenance, not content.** The static knowledge base — the condition closest
   to what `/init` writes — gained +2.8 points, and the paper reports *p*-values
   only for its two probe-and-refine contrasts, so that gap is **untested rather
   than null**. The demonstrated gain came only after the file was *tuned against
   observed failures*. That is not a repository tour; it is a defect log.
3. **It is a localisation aid, not a competence aid.** Precision was flat. This
   corroborates rather than contradicts Gloaguen's finding that agents fail on
   implementation skill: guidance got the agent to the right file and then stopped
   helping.

> **Conclusion.** The honest synthesis is not "context files don't work." It is:
> **a generated description of a repository does not move a frontier agent's
> success rate; a file that records what the agent actually got wrong can move a
> weaker agent's, by helping it navigate.** Which is the same finding as §5, from
> the opposite direction.

## 8. Finding 4 — these files only grow

Chakrabarti ([arXiv:2608.11095](https://arxiv.org/abs/2608.11095)), **247,694
instruction lifetimes across 1,867 repositories**:

- Context files grow **+226%** over their lifetime — a net **+4.9 instructions per commit**.
- The **older an instruction is, the less likely it is ever deleted** (log-hazard −0.032/commit).

He names the mechanism **catastrophic remembering** — the inverse of catastrophic
forgetting. Appending is cheap; proving a deletion is *safe* costs O(2^|D|). So
nobody deletes, and the file ratchets.

This is the strongest empirical support for the "clutter" worry — not that any
single file is too big today, but that **the artefact has no natural brake**.
Separately, 23.0% of AI config files already contain **stale code references**
([arXiv:2606.09090](https://arxiv.org/abs/2606.09090)).

Cai et al. ([arXiv:2606.12231](https://arxiv.org/abs/2606.12231)) reach the same
shape from a different corpus — 1,540 rule-evolution events across 83 projects.
Evolution is dominated by **constructive context expansions (29.17%) and
enrichments (26.59%)**, and surveyed developers say they edit rules mainly **to
correct AI errors (77.78%), "typically by adding new negative constraints rather
than editing existing ones."** Two independent mining studies, the same ratchet:
the file is where prohibitions accumulate, and nothing removes them.

That same paper supplies the counterweight, and it is the strongest argument for
keeping the practice at all: after a rule update, artefact compliance rose from
**49.14% to 72.13%**. Writing down what the agent got wrong *does* change what the
agent does — an adherence result, not a success-rate result, and §7 shows the two
are not the same thing.

## 9. Finding 5 — cost is real, money is not

Cost is the one effect that is consistently measured and clearly outside the noise:
**+20% (SWE-bench) to +23% (AGENTbench)**, with 2–4 extra reasoning steps.

But cost in *tokens* is not cost in *dollars*. `CLAUDE.md` sits in Claude Code's
cached **project-context** layer, between the system prompt and the conversation.
Using Anthropic's published rates (independently re-verified against two sources;
Sonnet 5 at $2/MTok in, $2.50 cache write, $0.20 cache read):

| CLAUDE.md size | Cached, 50 turns | Uncached, 50 turns |
|---|---|---|
| 500 tokens | $0.0062 | $0.0500 |
| 2,000 tokens | $0.0246 | $0.2000 |
| 10,000 tokens | **$0.123** | $1.00 |

The cached/uncached ratio is **exactly 50/6.15 = 8.13×**, and *N cancels* — the
discount is independent of file size (on the 1-hour cache tier, 7.25×).

> **Conclusion.** Even a 10,000-token CLAUDE.md costs about **12 cents** across a
> 50-turn session. **Do not shrink your CLAUDE.md to save money.** Shrink it to
> protect instruction compliance. The dollar argument is dead; the attention
> argument is not.

## 10. Why `/init` exists anyway

If the performance case is this weak, why ship it? Three honest answers.

**(a) It was there from day one.** `/init` and `CLAUDE.md` shipped in Claude Code's
first public build (2025-02-24, alongside Claude 3.7 Sonnet). It was not a patch
bolted on after watching the agent struggle, which weakens any "it was always a
crutch" story.

**(b) The performance case genuinely eroded — and Anthropic's own words track it.**

| Date | Anthropic's framing of CLAUDE.md |
|---|---|
| 2025-04 | *"an ideal place"* for commands, files, style, testing. **No size limit.** |
| 2025-09 | the *"naively dropped into context up front"* half of a hybrid with just-in-time glob/grep |
| 2026-09 | *"target under 200 lines… **Bloated CLAUDE.md files cause Claude to ignore your actual instructions!**"* — explicitly subtractive |

*(We initially read "naively" as self-criticism. Re-fetched in full, it is
descriptive of **eager** versus **just-in-time** loading, inside a paragraph that
presents the hybrid favourably. Corrected.)*

The retreat tracks the arrival of cheaper homes for the same content: **hooks**
(2025-06), **subagents** (2025-07), the **Explore subagent** — justified explicitly
*"to save context"* — and **Skills** (2025-10), **path-scoped rules** (2025-12),
**auto-memory** (2026-02). Every one is architecturally a way to stop cramming
things into the always-loaded file.

Anthropic's own unreleased `/init`, extracted from the binary, states the thesis
outright: *"CLAUDE.md is loaded into every Claude Code session, so it must be
concise — only include what Claude would get wrong without it."* Its per-line test:
*"Would removing this cause Claude to make mistakes?" If no, cut it.*

**(c) It has durable reasons that were never about task success.** `/init` is a
**migration tool** (it ingests `.cursor/rules`, `.cursorrules`,
`.github/copilot-instructions.md`, and behind a flag AGENTS.md, Windsurf, Devin and
Cline rules); an **onboarding** device; and a **human-readable team artefact**
checked into git. A mediocre draft also beats a blank page. None of that decays.

## 11. The unifying principle

Round 3 derived this from an unrelated literature — chain-of-thought, prefill,
verification prompting — and then found it predicts the context-file result:

> **Scaffolding decays when it substitutes for a capability the model now has
> natively. It persists when it supplies information the model structurally cannot
> derive, or enforces a constraint it cannot infer.**

| Half of the file | Kind | Fate | Evidence |
|---|---|---|---|
| Repository overview | **Substitutes** for reading the codebase — the agent can grep | **Decays** | no faster file-finding; 4/45 vs 27/45 |
| Commands, gotchas, prohibitions | **Supplies** non-derivable facts; **enforces** constraints | **Persists** | 1.6× vs <0.01× tool adoption |

The same principle explains the wider pattern: OpenAI now tells developers *"avoid
chain-of-thought prompts… prompting them to 'think step by step' is unnecessary"*;
Anthropic tells them to **remove** verification instructions because they *"cause
over-verification on Claude Opus 5… reduces wasted tokens with no loss in quality.
The same applies to legacy harness scaffolding."* Meanwhile scaffolding that
*supplies or enforces* — memory systems, fresh-context verifier subagents,
retrieval above the context threshold — is growing.

**The principle's best test is §7**, because it varies model capability while
holding the scaffolding fixed. Repository guidance is worth **+7.5 points** to
Qwen3.5-35B-A3B — a model that needs help finding the right file — and is worth
nothing measurable to Claude Code and Codex, which do not. The same file; opposite
verdicts; predicted by what the model can already do. Shepard & Albrecht's own
cross-model check closes the loop: the tuning procedure *fails* on a model too weak
to produce diagnostic output, so the scaffolding has a capability window on both
sides.

**Counter-evidence, kept:** few-shot prompting went the *other* way at GPT-3 scale
(the benefit **widened** with size); prompted persistence still adds *"close to
20%"* on GPT-4.1, a non-reasoning model. Both fit the principle: they substitute
for a capability those models genuinely lack.

## 12. What nobody has measured

1. **The two halves separately, against a shared success metric.** Cheap, obvious,
   still unrun. Shepard & Albrecht's coverage/precision split is the closest
   anyone has come, and it decomposes a *different* axis.
2. **Success, cost and latency jointly, with repeated runs.** No study does all three.
3. **Staleness versus consequence.** Prevalence is known (23%); impact is not.
4. **Whether instructions survive compaction** in practice.
5. **Hallucination rate of `/init` output** against ground truth.
6. **Anything at all** for Copilot, Windsurf, Cline, Amp, Devin, Junie, OpenHands.
7. **Non-Python, non-TypeScript.** Gloaguen's own caveat: Python's training
   representation *"might… nullify the effect of context files."*
8. **The capability window.** §7 shows guidance paying on a 35B open model and
   not on frontier agents, but nobody has run one design across a capability
   ladder. Until someone does, "does it help?" is missing its most important
   qualifier: *help whom?*
9. **Probe-and-refine on a frontier agent.** The one procedure that produced a
   significant gain has never been tried on Claude Code or Codex. It is the
   cheapest high-value experiment now open.

## 13. Recommendation

1. **Run `/init` once, as a draft.**
2. **Delete the architecture tour.** It is the half measured not to help, and §6
   says you cannot fix it by rewriting it.
3. **Write down what the agent got wrong, not what the repository contains.** This
   is the one intervention with a significance-tested positive result behind it
   (§7), and independently, rule updates lift compliance from 49% to 72% (§8). A
   line earns its place by having prevented a specific failure — which is, almost
   word for word, the test Anthropic's own unreleased `/init` applies.
4. **Keep only what the repo cannot tell the agent**: non-obvious commands,
   required env setup, gotchas, conventions that *differ* from defaults, repo
   etiquette, safety prohibitions.
5. **Count imperatives, not lines.** Compliance degrades with the number of
   simultaneous constraints and with session length — not, per McMillan, with file
   size.
6. **Move enforcement to hooks.** A rule that keeps being ignored was never a
   documentation problem. Hooks run outside the model's context.
7. **Move procedures to skills; module detail to subdirectory files or
   `paths:`-scoped rules.** These are the only genuinely lazy mechanisms —
   `@imports` load at launch and save nothing.
8. **Budget for the ratchet.** Files grow +226% and old lines never die. Schedule
   deletion; `/doctor` will propose cuts.
9. **Expect no success-rate miracle** *on a frontier agent*. The realistic wins are
   latency, compliance and avoided rediscovery. Agents fail on implementation
   skill, and no document fixes that — §7 found guidance moving *coverage* by
   14.5 points while patch precision did not budge.
10. **If you drive a smaller or local model, weight all of this differently.** The
    only measured success gain in the literature is on an open 35B model. The
    advice to prune is frontier-agent advice; on a weaker model a repository
    guidance file is load-bearing.

## 14. Limitations of this review

- **The base is five unreplicated 2026 preprints**, three of which are underpowered
  for the effects they report. The fifth (Shepard & Albrecht) was added on
  2026-09-20, after the first publication of this review — a reminder of how fast
  this literature is moving, and that a sixth may already exist.
- **We did not run an experiment.** This is a synthesis; the local corpus
  measurement (n=35) is descriptive only.
- **The cost tables are modelled**, with assumptions stated. The discovery-cost
  comparison in particular is an estimate, not telemetry.
- **The binary extraction is one version** (v2.1.278) on one machine; the gated
  `/init` may never ship.
- **Recency.** Claude Code shipped three versions during the week this was written.
- **The search budget was exhausted** (200/200 queries) before round 3 finished, so
  the scaffolding-decay round relied on targeted fetches of known sources rather
  than open-ended search. A round-5 sweep on 2026-09-20 with a raised budget found
  two directly relevant papers the earlier rounds had missed
  ([arXiv:2606.20512](https://arxiv.org/abs/2606.20512),
  [arXiv:2606.12231](https://arxiv.org/abs/2606.12231)), one of which changed a
  headline claim. **Assume the same is true of this version.**

## 15. Key sources

**Controlled ablations.** Gloaguen et al., [arXiv:2602.11988](https://arxiv.org/abs/2602.11988) ·
Khatri, [arXiv:2607.27250](https://arxiv.org/abs/2607.27250) ·
Lulla et al., [arXiv:2601.20404](https://arxiv.org/abs/2601.20404) ·
McMillan, [arXiv:2605.10039](https://arxiv.org/abs/2605.10039) ·
Shepard & Albrecht, [arXiv:2606.20512](https://arxiv.org/abs/2606.20512)

**Mechanism.** Sam-Bodden, [arXiv:2607.09691](https://arxiv.org/abs/2607.09691) ·
Chakrabarti, [arXiv:2608.11095](https://arxiv.org/abs/2608.11095) ·
Treude & Baltes, [arXiv:2606.09090](https://arxiv.org/abs/2606.09090)

**Observational.** Arabat & Sayagh, [arXiv:2606.13449](https://arxiv.org/abs/2606.13449) ·
Cai et al., [arXiv:2606.12231](https://arxiv.org/abs/2606.12231) ·
Jiang & Nam, [arXiv:2512.18925](https://arxiv.org/abs/2512.18925) ·
Chatlatanagulchai et al., [arXiv:2511.12884](https://arxiv.org/abs/2511.12884) ·
Vasilopoulos, [arXiv:2602.20478](https://arxiv.org/abs/2602.20478) (single-project
case study, 283 sessions — illustrative only)

**Reliability.** [arXiv:2608.14711](https://arxiv.org/abs/2608.14711) ·
[arXiv:2606.00920](https://arxiv.org/abs/2606.00920) ·
[arXiv:2609.08149](https://arxiv.org/abs/2609.08149)

**Scaffolding.** Wei et al., [arXiv:2201.11903](https://arxiv.org/abs/2201.11903) ·
Sprague et al., [arXiv:2409.12183](https://arxiv.org/abs/2409.12183) ·
Xia et al. (Agentless), [arXiv:2407.01489](https://arxiv.org/abs/2407.01489)

**Vendor.** [Claude Code memory](https://code.claude.com/docs/en/memory) ·
[best practices](https://code.claude.com/docs/en/best-practices) ·
[prompt caching](https://code.claude.com/docs/en/prompt-caching) ·
[Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (2025-09-29)

**This repository.** `results.md` (full dossier) · `evidence/` (binary extracts,
verification log, self-review, round-3 notes)
