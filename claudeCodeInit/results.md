# Does `/init` help? — evidence review

> **This is the raw dossier.** For the synthesised meta-study — with a
> five-sentence TL;DR, the unifying principle, and the verdict — read
> [`whitepaper.md`](whitepaper.md). For the 3-page paper, see
> [`paper.pdf`](paper.pdf).
>
> **Round 7 (2026-09-24)** added a sixth controlled study (S6, Zhang et al.,
> the largest yet), five mechanism papers, and three corrections: the AAIF
> example paired numbers from two different tasks (§4.3); Codex does not read
> `CLAUDE.md` (§5); and the second `/init` is now documented as opt-in (§3.2).
>
> Rounds 2 and 3 revised several claims below. Where this file and the
> whitepaper differ, the whitepaper is current; every change is logged in
> [`evidence/verification-log.md`](evidence/verification-log.md).

**Question.** Claude Code ships a `/init` command that inspects a repository and
writes a `CLAUDE.md`. That file is loaded into every subsequent session. Does this
make later work faster, cheaper or better — or is it context clutter that burns
tokens and dilutes attention?

**Compiled** 2026-09-19. **Method:** five parallel research passes (academic
literature, vendor primary sources, practitioner grey literature, cross-harness
comparison, context economics), plus direct extraction from the shipped Claude
Code binary and a local measurement of 35 instruction files. Load-bearing claims
were re-fetched from the primary source by the lead session; see
[`evidence/verification-log.md`](evidence/verification-log.md).

---

## 1. The short answer

**`/init` does not reliably improve task success on a frontier agent. The
measured effects on correctness run from −5.9% to +4%, and in the careful studies
of Claude Code and Codex they are statistically indistinguishable from zero.**
Meanwhile the file costs 20%+ more inference in one study and *saves* 16–28% in
another.

**One qualification, added in round 5 and load-bearing.** S5 (Shepard & Albrecht)
finds a real gain — 25.5% → 33.0% resolve rate, *p*<0.001 over four trials — on
an **open 35B model**, and only when the guidance file was **tuned against the
agent's own observed failures**. The condition closest to a `/init` draft gained
2.8 points, which that paper does not significance-test. So the null is a finding
about *frontier agents and generated descriptions*, not about the practice as
such. §4.1a works this through.

**A second qualification, added in round 7.** S6 (Zhang et al., 5,000+ Claude
Code runs on Opus 4.6) finds every rule file beating no file by 6.9–13.8 pp — but
only on the 58 of 500 SWE-bench Verified tasks the agent solves 1–2 times in 3, no
single contrast significant (random vs none *p*=0.077; the headline rests on a
sign test across seven conditions, *p*=0.008), and **random rules tie curated ones
at 63.8%**. The other 442 tasks did not move, so over the full benchmark the gain
is ≈+1.6 pp (our arithmetic: 13.8 × 58/500). Presence may prime; content does not
decide. §4.1b.

But the aggregate number hides the finding that actually matters, and it is
reproduced independently by an academic paper and by Anthropic's own new,
opt-in `/init`:

> **A CLAUDE.md is two different things glued together, and they have opposite
> signs. The *instructions* (non-standard commands, gotchas, prohibitions,
> conventions that differ from defaults) are followed and are worth their tokens.
> The *repository overview* (architecture tours, directory layouts, dependency
> lists, tech-stack summaries) is not helpful, and it is the bulk of what a
> default `/init` writes.**

ETH Zürich, arXiv:2602.11988, abstract, verbatim:

> *"while instructions in the context files are well followed by coding agents,
> **repository overviews, although popular and recommended by model providers, are
> not helpful**."*

Anthropic's new, opt-in `/init`, extracted from the shipped binary, independently:

> *"CLAUDE.md is loaded into every Claude Code session, so it must be concise —
> only include what Claude would get wrong without it."*

And Anthropic's shipped CLAUDE.md audit doctrine, same binary:

> *"A line of a checked-in CLAUDE.md that a fresh session could reconstruct with a
> few tool calls (`ls`, `cat`, reading the manifest, `--help`) is dead weight every
> session it loads into pays for."*

So: **the practice is sound, the default artefact is not.** Run `/init`, then
delete most of what it wrote.

### The answer in one table

| If you ask… | Answer | Confidence |
|---|---|---|
| Does having a CLAUDE.md raise task success? | No measurable effect (bounded to ≤10–15pp; point estimates −2% to +4%) | **Medium-high** — **two** studies measured success directly (S1, S2) and agree; a third reports "comparable completion" without gating on correctness |
| Does an **LLM-generated** (`/init`-style) file beat no file? | No, it is the worst-performing category | Medium-high |
| Does a **hand-written** file beat no file? | Marginally, ~+4%, not significant | Medium |
| Does it cost more tokens? | Contested: +20% (ETH) vs −16 to −28% (JAWs/Lulla) | **Low** — direct contradiction, unresolved |
| Does it cost more *money*? | Negligible once prompt caching works — ~$0.02/session for a 2,000-token file | High (arithmetic, from published pricing) |
| Is it faster? | Probably yes: −27 to −28% wall-clock in two independent measurements | Medium |
| Does file size hurt adherence? | **Not detected** in the one factorial study of this exact question | Medium — surprising, contradicts folk wisdom |
| What *does* hurt adherence? | Session length: ~5.6% lower odds of compliance per generated function | Medium |
| Does *what the file says* matter for success? | **Apparently not, on a frontier agent:** random rules tie curated ones (S6) | Low-medium — one study, borderline-task subset, no single contrast significant |
| Is `/init`'s repo-overview section worth it? | **No.** Converging evidence from academia and from Anthropic's own code | **High** |

---

## 2. How to read the evidence grades

Throughout, sources are graded:

- **A — controlled ablation.** Same tasks run with and without the file, outcome
  measured against gold tests. Four such studies exist. All are 2026 preprints or
  workshop papers; none is a journal publication.
- **B — large-N observational.** Real-world outcomes correlated with file
  presence. Cannot establish causation; confounded by which projects adopt files.
- **C — descriptive corpus.** What's in these files across many repos. Says
  nothing about whether they work.
- **D — vendor documentation.** Authoritative on *mechanism*, worthless on
  *effectiveness*, and commercially interested.
- **E — practitioner anecdote.** Useful for failure modes, not for effect sizes.

**A recurring structural problem:** every vendor in this space documents the
mechanism in exhaustive detail and publishes no ablation. Anthropic, OpenAI,
GitHub, Cursor, Windsurf, Cline, Amp, Cognition, JetBrains — not one has published
a controlled with/without measurement of its own instruction-file feature. The
entire evidentiary base is five academic papers and one foundation blog post.

---

## 3. What `/init` actually is (primary source)

Extracted from `/home/mpetrick/.local/share/claude/versions/2.1.278` — the shipped
binary, not the documentation. Full extracts and reproduction commands in
[`evidence/primary-binary-extracts.md`](evidence/primary-binary-extracts.md).

### 3.1 The current prompt

`/init` asks the model for exactly two things:

1. *"Commands that will be commonly used, such as how to build, lint, and run tests."*
2. *"High-level code architecture and structure… Focus on the 'big picture' architecture that requires reading multiple files to understand."*

Then it spends four of its eight usage notes trying to stop the model padding:

> - Avoid listing every component or file structure that can be easily discovered.
> - Don't include generic development practices.
> - Do not make up information such as "Common Development Tasks", "Tips for Development", "Support and Documentation" unless this is expressly included in other files that you read.
> - …do not include obvious instructions like "Provide helpful error messages to users"…

**This matters for how you read the criticism.** The common complaint — "`/init`
generates a bloated file full of stuff I could have read off `package.json`" — is
not a complaint about what `/init` *asks for*. It is the model under-complying
with a prompt that explicitly forbids that. And note item 2: `/init` asks for the
architecture overview that arXiv:2602.11988 found to be the unhelpful half.

### 3.2 There is a second `/init`: documented, opt-in, still off by default

Gated behind `CLAUDE_CODE_NEW_INIT` or the `tengu_slate_harbor_experiment` flag.
*Round 7 update:* the [memory docs](https://code.claude.com/docs/en/memory) now
describe it — *"For an interactive multi-phase flow instead, set the
`CLAUDE_CODE_NEW_INIT` environment variable to `1` before you run `/init`… it asks
which artifacts to set up: CLAUDE.md files, skills, and hooks."* In binary
v2.1.282 the gate still reads `CLAUDE_CODE_NEW_INIT||x("tengu_slate_harbor_experiment",!1)`,
so it remains off by default, and the "only include what Claude would get wrong
without it" prompt is unchanged. Separately, since v2.1.277 (2026-09-18) Claude
Code reads `AGENTS.md` directly when a project has no `CLAUDE.md`.
Its design premise is the sceptics' argument. It is an eight-phase interactive
flow whose acceptance test for every line is:

> *"Would removing this cause Claude to make mistakes?" If no, cut it.*

Its explicit **Exclude** list bans file-by-file structure, standard conventions,
generic advice, detailed API docs, frequently-changing information, and *"commands
obvious from manifest files"*. It routes content **out** of the always-loaded file
into three cheaper homes:

| Artefact | For | Loading cost |
|---|---|---|
| **Hook** | deterministic per-edit shell commands (format, lint) | zero context — runs outside the model |
| **Skill** | on-demand workflows (`/verify`, `/deploy-staging`) | one-line description resident; body loads on invocation |
| **CLAUDE.md note** | guidance that shapes behaviour but isn't enforced | always resident |

That Anthropic has built, and gated behind an experiment flag, a replacement for `/init` founded on
"the old one produces files that are too big" is the strongest single piece of
evidence on the clutter question — and it comes from the vendor's own build.

### 3.3 Exact loading semantics

The `InstructionsLoaded` hook contract exposes a `load_reason` enum that is the
whole cost model:

| `load_reason` | What | Cost |
|---|---|---|
| `session_start` | root `CLAUDE.md`, `~/.claude/CLAUDE.md`, unscoped `.claude/rules/*.md` | resident all session |
| `compact` | re-injected after compaction | paid again per compaction |
| `nested_traversal` | subdirectory `CLAUDE.md`, when Claude touches that directory | paid only if you go there |
| `path_glob_match` | `.claude/rules/*.md` with `paths:` frontmatter | paid only for matching files |
| `include` | `@path` imports | **not lazy** — resolved when the parent loads |

The last row is a common misconception worth stating plainly: **splitting a big
CLAUDE.md into `@imports` does not reduce context.** Anthropic's docs confirm it:
*"Splitting content into imports… doesn't reduce context, since imported files
load at launch."* Only `nested_traversal` and `path_glob_match` are genuinely lazy.

### 3.4 Where it sits in the prompt, and what that costs

Two independent Anthropic sources (the `prompt-caching` doc and the
`claude.com/blog` prompt-caching post) agree that Claude Code orders each request
static-first:

| Layer | Contents | Invalidated when |
|---|---|---|
| System prompt | core instructions, tool definitions | tool set changes |
| **Project context** | **CLAUDE.md, auto memory, unscoped rules** | session start, `/clear`, `/compact` |
| Conversation | messages, tool results | every turn |

**CLAUDE.md is in the cached prefix.** This largely defuses the "it burns tokens
every turn" objection — see §7. It is also delivered *as a user message after the
system prompt*, not as part of the system prompt, so it carries no special
authority: *"Claude reads it and tries to follow it, but there's no guarantee of
strict compliance."* Anthropic is explicit that it is **context, not configuration**:
*"To block an action regardless of what Claude decides, use a PreToolUse hook instead."*

### 3.5 Anthropic's own stated limits

| Guidance | Value | Source |
|---|---|---|
| Recommended ceiling | **under 200 lines** | `memory`, `best-practices`, `costs` docs |
| In-product warning threshold | ~5% of context window in characters, floor ~40,000 chars | `getMaxMemoryCharacterCount`, cited in shipped audit doctrine |
| Hard ceiling | 4 MiB, larger files skipped entirely | `memory` doc |
| Import recursion | 4 hops | `memory` doc |

And the concession that matters most, from Anthropic's own best-practices page:

> *"**Bloated CLAUDE.md files cause Claude to ignore your actual instructions!**"*
> *"If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost."*

A vendor asserting that its own feature degrades when overused is a credible
concession — it cuts against the commercial interest in "add more context".

---

## 4. The direct causal evidence

Six controlled ablations exist. This is the entire grade-A base for the question.
**S6 was added in round 7 (2026-09-24)** — public since April and missed by six
earlier rounds; it is the largest of the six.
**S5 was added in round 5 (2026-09-20)** — three earlier rounds of search missed
it, and it is the only one of the six reporting a significant positive effect on
task success.

### 4.1 The six studies

| # | Study | Design | N | Measured | Result |
|---|---|---|---|---|---|
| **S1** | **Gloaguen, Mündler, Müller, Raychev, Vechev** — *Evaluating AGENTS.md* [arXiv:2602.11988](https://arxiv.org/abs/2602.11988). SRI Lab, ETH Zürich. MemAgents @ ICLR 2026, **Oral & Runner-up Best Paper**. Code: [eth-sri/agentbench](https://github.com/eth-sri/agentbench) | 4 agent/model combos × 3 conditions (none / LLM-generated / human-written) × 2 benchmarks (SWE-bench Lite 300; AGENTbench 138 issues from 12 repos with developer-committed files). **Single run per instance — *"We sample completions for each agent once."* No significance testing, no CIs. Success rates published only as bar charts.** | 300 + 138 | success rate, steps, $ cost | **No general success improvement; +20% (SWE-bench) to +23% (AGENTbench) cost.** LLM-generated −0.5% to −2%; human-written beats LLM-generated for all 4 agents and beats *no file* for **all agents except Claude Code**. **Third condition:** with repo docs stripped, LLM-generated files **+2.7%** and beat developer-written docs. |
| **S2** | **Khatri** — *Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories* [arXiv:2607.27250](https://arxiv.org/abs/2607.27250), 2026-07-28 | Claude Code + Codex, context-injection strategies ablated, gold-test evaluation, **equivalence testing** rather than only null-hypothesis testing | 17 tasks, 3 repos, **288 evaluated runs (3 repeats/task — the only repeated-run correctness design)** | correctness, latency | **No measurable effect, bounded to ≤10–15pp.** *But its own power analysis gives a minimum detectable effect ≈**30pp***, needing ~120–200 tasks for 80% power at 10pp. Failure triage: agents fail on *implementation skill* — design, pattern selection, wiring — not missing repo knowledge. Manipulation probe: the real AGENTS.md **never converts a near-miss into a pass**. |
| **S3** | **Lulla, Mohsenimofidi, Galster, Zhang, Baltes, Treude** — *On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents* [arXiv:2601.20404](https://arxiv.org/abs/2601.20404). JAWs @ ICSE 2026. | paired within-task: same task run with and without AGENTS.md, isolated containers, small PRs (≤100 LOC, ≤5 files) | 10 repos, **124 PRs** | runtime, tokens — **correctness only spot-checked on 50 of 124** | **Median runtime −28.64%** (98.6s→70.3s), **output tokens −16.58%**, input −9.73%. Completion behaviour "comparable" — correctness was *not* a measured primary metric. |
| **S4** | **McMillan** — *Instruction Adherence in Coding Agent Configuration Files: A Factorial Study of Four File-Structure Variables* [arXiv:2605.10039](https://arxiv.org/abs/2605.10039), 2026-05-11 | factorial over file size × instruction position × file architecture × cross-file contradictions | **1,650 Claude Code sessions**, 16,050 function-level observations, 2 TS codebases, 3 models | instruction adherence, via a **synthetic `// @tracked` marker** (not task success) | **Most statistically rigorous of the four** (GLMMs, FDR correction, Bayesian companion). **None of the four structural variables had a detectable effect**, with *affirmative* Bayesian nulls for size (BF₁₀=0.096) and contradiction (BF₁₀=0.053) after multiple-testing correction. What did matter: **session length — ~5.6% lower odds of compliance per additional generated function (OR 0.944).** |
| **S5** | **Shepard & Albrecht** — *Probe-and-Refine Tuning of Repository Guidance for Coding Agents* [arXiv:2606.20512](https://arxiv.org/abs/2606.20512), 2026-06-18 (v2 06-19) | three conditions — unguided / static knowledge base / **probe-and-refine tuned** guidance, where synthetic bug-fix probes iteratively diagnose and patch the guidance file via single-shot LLM calls, **no agent loop during tuning**. Plus a step-budget experiment and a cross-model check on NVIDIA-Nemotron-3-Nano-30B-A3B | SWE-bench Verified, **4 independent trials**, Qwen3.5-35B-A3B at 200 steps | resolve rate, patch precision, coverage | **The only positive significance-tested success effect in the literature.** 25.5% unguided → 28.3% static KB → **33.0% tuned** (*p*<0.001 for both tuned contrasts — the paper tests **only** the two probe-and-refine contrasts, so the static-vs-unguided +2.8 pp gap is untested rather than null). **The gain is coverage, not precision:** +14.5 pp more instances yield an evaluable patch, per-patch precision flat at ≈59% (*p*=0.119) — i.e. guidance *"helps agents reach the correct file rather than improving the quality of the changes they make."* Thesis: *"how the guidance is produced is the decisive variable."* Cross-model: the tuning loop **degrades** when the model cannot emit sufficiently diagnostic output. |
| **S6** | **Zhang, Wang, Cui, Qiu, Li, Zhu, He** — *Guardrails Beat Guidance: A Large-Scale Study of Rules, Skills, and Persistent Configuration for Coding Agents* [arXiv:2604.11088](https://arxiv.org/abs/2604.11088), 2026-04-13 (v2 05-28) | 679 scraped rule files (25,532 rules); no-rule baseline vs seven rule conditions (curated, popular, random, matched, mismatched, shuffled, native-only); per-rule ablation; rule counts 0–50. **Task selection:** all 500 SWE-bench Verified tasks screened ×3, keeping the **58** solved 1–2 of 3 times (*"47% of tasks are always solved and 27% never solved regardless of rules"*). Experiment 1 is **one trajectory per task**; McNemar and Cochran's Q | >5,000 runs of **Claude Code + Opus 4.6** | resolve rate on the discriminative subset | Every rule condition beats the 50.0% baseline by **6.9–13.8 pp**; *"no condition is significantly different from any other (Cochran's Q = 4.70, p = 0.697)"*; random vs baseline McNemar *p*=0.077; headline rests on a sign test over seven directions, *p*=0.008. **Random = curated = 63.8%** → *"context priming"*. Per-rule (n=35): every helpful rule is a negative constraint, every harmful one a positive directive; only one rule individually significant (*p*=0.016, not surviving correction). Pass rate flat for 0–50 rules. Baseline itself moved 50.0% → 60.3% between experiments (single vs three-seed). |

### 4.1a Why S5 does not overturn S1–S4

It is the single most important addition since the first draft, and it must not be
over-read in either direction.

- **Different model class.** Qwen3.5-35B-A3B is an open mid-size model. S1 and S2
  tested Claude Code and Codex. Under §11's principle, scaffolding pays where the
  model lacks the capability natively — and S5's own cross-model check shows the
  procedure failing on a *weaker* model still, so the window is bounded on both
  sides.
- **Different artefact provenance.** The **static knowledge base** — the condition
  closest to what `/init` writes — gained **2.8 pp and did not reach
  significance**. Only the file *tuned against observed failures* moved the
  needle. That is a defect log, not a repository tour.
- **It corroborates S2's failure triage.** Khatri found agents fail on
  implementation skill, not missing repo knowledge. S5 measures exactly that split
  and agrees: coverage moved, precision did not.
- **It does not close the decisive gap.** S5 splits coverage from precision, not
  *instructions* from *overview*. §11's first open experiment stands.

### 4.1b What S6 adds, and what it does not

- **It is the only controlled study of a frontier agent with a positive
  direction on success** — but on an enriched subset, with no single contrast
  significant. Diluted over all 500 tasks it is ≈+1.6 pp, inside every noise
  estimate in §4.3.
- **Its most robust result is about content, not presence:** random, shuffled and
  wrong-domain rules match curated ones. That is independent support for §5's
  reading of S1 — whatever a file does for success, it is not the repository
  description.
- **Its polarity result supports the "prohibitions" advice** (§12) and matches Cai
  et al.'s observation that developers add negative constraints — but it is
  suggestive (one individually significant rule), not established.
- **Its count result agrees with S4:** 0 to 50 rules, flat pass rate, as McMillan
  found no effect of file size on adherence.

### 4.2 Reconciling the apparent contradiction

S1 says +20% cost; S3 says −17 to −28% cost. This reads as a flat contradiction and
is cited as one all over the grey literature. It mostly is not:

- **They measured different things.** S1 measured total inference cost including
  reasoning tokens on tasks selected for difficulty. S3 measured wall-clock and
  output tokens on deliberately *small* PRs (≤100 LOC, ≤5 files) — exactly the
  regime where knowing the test command up front saves a long exploration detour
  and the agent stops earlier.
- **Different file provenance.** S3 used developer-committed files. S1's penalty
  was worst for LLM-generated ones.
- **S3 never gated on correctness.** "Finished faster using fewer tokens" and
  "stopped early without doing the work" are indistinguishable in S3's design. Its
  own abstract claims only *"comparable task completion behavior"*.
- **S2 offers a direct explanation for why prior studies disagree:** borderline
  task difficulty is *agent-specific* (Spearman ρ=0.75), so single-agent studies
  draw their tasks from different agents' informative bands and get different
  answers to what looks like the same question.

**The honest synthesis:** on easy, well-scoped tasks a good instructions file
saves an exploration detour and therefore time and tokens. On hard tasks it adds
reasoning overhead without adding capability, because the binding constraint is
implementation skill, not repository knowledge (S2's central finding). Nobody has
yet run a study that measures success rate **and** cost **and** latency together
with repeated runs per condition. **That is the single clearest gap in the
literature as of September 2026.**

### 4.3 Repeated runs are not optional

The Agentic AI Foundation ran GitHub Copilot CLI five times per condition
(*"Measuring AGENTS.md: What Five Runs Show That One Doesn't"*, 2026-07-22) on two
tasks. The author's first, single-run attempt on the harder, multi-file task
showed AGENTS.md *"44% slower and 41% more expensive for identical output."* The
five-run median on **that same task** showed AGENTS.md winning by *"9 to 10%"*.
(The often-quoted *"27% … 24% … 26% smaller"* figures are the **other**,
ambiguous task. Earlier versions of this dossier paired them with the 44% run —
corrected in round 7.)

The direction flipped between one run and five. The noise exceeds the effect. **Every single-run before/after
blog demo in this space — in either direction — is uninformative.** Treat AAIF as
vendor-adjacent (it now stewards AGENTS.md), but the methodological point stands
independent of the numbers.

### 4.4 Large-N observational evidence (grade B)

**Arabat & Sayagh**, *Toward Instructions-as-Code* ([arXiv:2606.13449](https://arxiv.org/abs/2606.13449),
MSR 2026) — **15,549 agentic PRs across 148 projects** from the AIDev dataset,
comparing merge rate before and after a project adopted an instruction file:

- **27.7%** of projects: merge rate up by ≥20 points
- **26.35%** of projects: merge rate **down** by ≥20 points

A coin flip. The moderator is quality, not presence: *"Projects that managed to
increase their merge rate have substantially longer instruction files, which are
also well structured into a higher number of sections and sub-sections."*

Note this cuts *against* naive "keep it short" advice and *with* S1's
human-written-beats-generated finding. It is observational — projects that write
good instruction files are probably better-run projects generally — so it cannot
carry causal weight on its own.

---

## 5. Cross-harness: does this generalise beyond Claude Code?

Yes, and the pattern is uniform: **every harness has an instruction file; almost
none of their vendors has measured whether it works.**

| Harness | Mechanism | Published effectiveness evidence |
|---|---|---|
| **OpenAI Codex** | `AGENTS.md` (and `AGENTS.override.md`), root-to-cwd walk, 32 KiB cap (`project_doc_max_bytes`); other names only via `project_doc_fallback_filenames` — the current docs never mention `CLAUDE.md` (corrected round 7) | **None.** OpenAI's own framing is notably defensive: *"codex-1 shows strong performance even without AGENTS.md files or custom scaffolding."* |
| **GitHub Copilot** | `.github/copilot-instructions.md`, path-scoped `.github/instructions/*.instructions.md` with `applyTo` globs; also reads AGENTS.md/CLAUDE.md/GEMINI.md | **None quantitative.** GitHub analysed 2,500+ AGENTS.md files qualitatively (grade C). |
| **Cursor** | `.cursor/rules/*.mdc` with four application modes; legacy `.cursorrules`; AGENTS.md | **Deliberately none.** Jiang & Nam, [arXiv:2512.18925](https://arxiv.org/abs/2512.18925), MSR '26, 401 repos / 1,876 files: *"the rules we observed are primarily based on developer intuition; their actual impact on LLM performance remains an open question."* 28.70% of rule lines are duplicated across repos; avg 462.67 lines/file. |
| **Aider** | `CONVENTIONS.md` via `--read` | **None for the conventions file.** Only a qualitative before/after demo. |
| **OpenHands** | `.openhands/microagents/repo.md`, `trigger_type: always\|keyword\|manual` | **None**, despite a research-heavy posture. Notable absence. |
| **Gemini CLI** | `GEMINI.md`, global→project→subdirectory, all concatenated | None |
| **Windsurf / Cline / Amp / Devin / Roo / Kilo / Junie** | rules dirs, memory banks, AGENT.md, knowledge+playbooks, guidelines.md | None isolating the file's contribution |

### 5.1 The most interesting cross-harness result is not about instruction files

Aider's **repo map** — tree-sitter parsing plus PageRank-style ranking, budgeted at
1,000 tokens by default — **identified the correct file to edit in 70.3% of
SWE-bench Lite tasks**, and Aider credited it for a then-SOTA 26.3% score
(vs. Amazon Q 20.3%, OpenDevin unhinted 16.7%), May 2024.

That is the strongest "context helps" number anywhere in this review, and it is
**automatic, structural, computed context** — not hand-written prose. Similarly,
Aider's unified-diff edit format took gpt-4-1106 from **20% → 61%**.

**The lesson:** the measurable wins in agentic coding have come from better
*retrieval and formatting* machinery, not from better *prose instructions*. This is
consistent with arXiv:2603.20432's finding that coding agents which externalise
long-context work into tool calls (grep, file navigation) beat published SOTA by
17.3% — the agent searching beats the agent being pre-loaded.

### 5.2 Standardisation

`AGENTS.md` launched 2025-08-19 (OpenAI + Amp, Jules, Cursor, Aider, RooCode, Zed,
Factory), ~20,000 repos at launch, **60,000+** claimed by 2026 (unaudited). On
2025-12-09 OpenAI, Anthropic and Block founded the **Agentic AI Foundation** under
the Linux Foundation; OpenAI donated AGENTS.md, Anthropic donated MCP, Block
donated Goose.

Claude Code added native AGENTS.md reading in **v2.1.277** — one version before the
binary examined here. Default mode `claude-md-or-agents-md`: AGENTS.md is used only
where there is no CLAUDE.md. Other modes: `claude-md`, `claude-md-and-agents-md`,
`managed-only`.

---

## 6. Mechanism: why extra context can hurt

The direct studies say "no effect". The mechanism literature explains why more
context is not free, and predicts *which* content is harmful.

### 6.1 Long context degrades before the window is full

| Finding | Number | Source |
|---|---|---|
| All 18 models tested degrade continuously with input length; none is flat | — | [Chroma, *Context Rot*](https://www.trychroma.com/research/context-rot), 2025-07-14 (industry, vendor interest in retrieval) |
| With lexical overlap removed, ~10–11 of 12 long-context models fall below 50% of their short-context baseline **at 32K tokens**. GPT-4o: 99.3% → 69.7% | −29.6pp | NoLiMa, [arXiv:2502.05167](https://arxiv.org/abs/2502.05167), ICML 2025 |
| Only ~half of models claiming ≥32K context clear a basic competence bar at 32K | — | RULER, [arXiv:2404.06654](https://arxiv.org/abs/2404.06654), NVIDIA |
| U-shaped accuracy by position: facts at the start or end are retrieved far better than facts in the middle | ~22pp gap at 2.3K tokens | Lost in the Middle, [arXiv:2307.03172](https://arxiv.org/abs/2307.03172), TACL |

**Caveat for this dossier:** a 2,000-token CLAUDE.md is nowhere near 32K. This
literature explains why a *10,000-line* instruction file fails; it does not by
itself condemn a 150-line one.

### 6.2 Instruction adherence decays with the *number* of instructions

This is the mechanism that actually bites at realistic CLAUDE.md sizes.

| Finding | Number | Source |
|---|---|---|
| Hard Satisfaction Rate falls as constraints are added, steepest past 3 | ~77% (L1) → ~33% (L4) | FollowBench, [arXiv:2310.20410](https://arxiv.org/abs/2310.20410) |
| At 500 simultaneous instructions, even the best frontier models reach only 68% accuracy; bias toward earlier-positioned instructions | 68% | IFScale, [arXiv:2507.11538](https://arxiv.org/abs/2507.11538) |
| Compliance degrades consistently with instruction count across all 10 models; count alone predicts compliance to ~10% error | — | ManyIFEval, [arXiv:2509.21051](https://arxiv.org/abs/2509.21051), EMNLP 2025 |
| Multi-turn "instruction forgetting": o1-preview turn 1 → turn 3 | 88% → 71% | Multi-IF, [arXiv:2410.15553](https://arxiv.org/abs/2410.15553), Meta |
| Expert-written SOPs of 20–124 pages as governing policy: strict pass rate | best model 36.2%; most frontier models <25% | HANDBOOK.md, [arXiv:2607.25398](https://arxiv.org/abs/2607.25398) |

**The practical translation.** A CLAUDE.md is mechanically a simultaneous-constraint
set. Every "always X" / "never Y" bullet competes for the same compliance budget.
Reference material — file paths, commands, architecture facts — does *not* compete
the same way, because it is not scored for compliance. So the sizing rule is not
"keep the file under N tokens". It is:

> **Keep the number of imperatives small. Reference material is cheap; rules are
> expensive.**

This also reconciles S4 (file *size* had no detectable effect) with the folk wisdom
(long files get ignored): size is the wrong variable. Rule *count* and session
*length* are the right ones.

### 6.3 Plausible-but-irrelevant context is worse than noise

| Finding | Number | Source |
|---|---|---|
| Adding relevant-but-insufficient context raises Gemma's incorrect-answer rate | 10.2% → **66.1%** | Sufficient Context, [arXiv:2411.06037](https://arxiv.org/abs/2411.06037), ICLR 2025 |
| Accuracy under added irrelevant items (1→15): Grok-3-Beta 43%→19%; GPT-4.1 26%→2% | — | [arXiv:2302.00093](https://arxiv.org/abs/2302.00093) (ICML 2023) and [arXiv:2505.18761](https://arxiv.org/abs/2505.18761) |
| Models perform **worse** when the irrelevant haystack preserves natural logical flow than when it is shuffled | — | Chroma, *Context Rot* |

That last row is the sharpest result in this whole section. **Coherent, plausible,
not-quite-relevant prose is a worse distractor than random noise** — and that is
precisely the shape of an auto-generated architecture overview. It gives a
mechanism for S1's finding that repository overviews are not merely useless but
mildly harmful.

---

## 7. The cost arithmetic

Published Anthropic pricing, fetched and then **independently re-verified against
both `platform.claude.com` and `claude.com/pricing`** on 2026-09-19; every figure
below was confirmed, none corrected. Cache write 1.25× base input (5-min TTL) or
2× (1-hour); **cache read 0.1× base input**.

| Model | Input | Output | 5m cache write | 1h cache write | Cache read | Min cacheable prefix |
|---|---|---|---|---|---|---|
| Claude Opus 5 | $5 | $25 | $6.25 | $10 | $0.50 | 512 tok |
| **Claude Sonnet 5** | **$2** | **$10** | **$2.50** | **$4** | **$0.20** | 1,024 tok |
| Claude Haiku 4.5 | $1 | $5 | $1.25 | $2 | $0.10 | 4,096 tok |

(Per MTok. Sonnet 5's $2/$10 was introductory pricing through 2026-08-31 and is
now the standard price; the scheduled increase to $3/$15 was cancelled.)

**CLAUDE.md sits in the cached project-context layer (§3.4).** So over a 50-turn
session it is written to cache once and read 49 times:

| CLAUDE.md size | Cached, 50 turns | Uncached, 50 turns | Marginal cost per later turn |
|---|---|---|---|
| 500 tokens | **$0.0062** | $0.0500 | $0.0001 |
| 2,000 tokens (Anthropic's ~200-line ceiling) | **$0.0246** | $0.2000 | $0.0004 |
| 10,000 tokens (far past every guideline) | **$0.123** | $1.00 | $0.002 |

Two consequences that fall out of the arithmetic rather than intuition:

1. **The cache discount is a constant ≈**8.13×** regardless of file size** — it is a
   property of the multipliers alone. Algebraically the ratio is
   `50 / (1.25 + 49×0.1) = 50/6.15 = 8.130`; **both N and the base rate cancel**,
   verified numerically at N = 500 / 2,000 / 10,000.
   *This assumes the 5-minute cache tier.* On the 1-hour tier (2× write), which is
   the default on a Claude subscription within plan usage, the ratio is
   `50/(2 + 4.9) = 7.25×`. Either way the conclusion holds: "shrink the file to save
   money" is a far weaker lever than "make sure it is actually being cached."
   Check `cache_read_input_tokens` in `/usage`, or the `Prompt cache (main)` line.
2. **Even a 10,000-token CLAUDE.md costs about 12 cents across a 50-turn session.**
   *The dollar argument against a large CLAUDE.md is basically dead.* The real cost
   is the attention and compliance tax in §6, not the invoice.

### 7.1 Against the alternative: self-discovery

The counterfactual is not "free". Without a context file the agent runs `ls`,
`cat package.json`, reads the README, greps for the test command, inspects lint
config, checks `git log`. Modelled bottom-up at ~4,800 input tokens of tool results
plus ~1,600 output tokens across ~8 round trips:

| Approach | Session cost (50 turns, Sonnet 5) | Extra round trips |
|---|---|---|
| 500-token CLAUDE.md | $0.0062 | 0 |
| 2,000-token CLAUDE.md | $0.0246 | 0 |
| 10,000-token CLAUDE.md | $0.123 | 0 |
| **Self-discovery, no file** | **$0.075** | **~8** |

A curated 2,000-token file is roughly **3× cheaper per session than rediscovery**,
and the gap widens with repetition because authoring cost is sunk once while
discovery is paid by every fresh session. Over 100 sessions: ~$2.46 vs ~$7.50.

**Caveats, stated plainly.** These are modelled figures, not measured telemetry —
assumptions are shown so they can be redone. Published trajectory analyses put
reading and searching at **56.2% of tool-use turns and 46.5% of total tokens** on
SWE-bench Verified, and token usage on an identical task varies **up to 30×
run-to-run** ([arXiv:2604.22750](https://arxiv.org/abs/2604.22750)), so the
discovery figure is a lower bound with wide error bars.

**This is the strongest argument for having a file at all** — and note it is an
argument for the *commands and gotchas* half, not the architecture-overview half.
It is also the only part of the case that S3's latency finding (−28.64% median
runtime) independently supports.

---

## 8. Practitioner evidence and the failure modes

Grade E, but valuable for *how* it fails rather than *whether* it works.

**The "it gets ignored" cluster.** Multiple independently-filed GitHub issues on
`anthropics/claude-code` converge on the same pattern: #18660 (rules read but not
reliably followed; closed "not planned"), #87318 (a "mandatory startup protocol" is
loaded but "not behaviorally internalized"), #15443 (Claude confirms understanding,
then immediately violates), **#29746 (after context-window compaction, CLAUDE.md and
memory files are not re-read, so standing rules silently stop applying)**, #78697
(`@path` imports only expand for the launch-directory file). #91880 reports a
~900-line CLAUDE.md re-sent on every tool round-trip.

#29746 is worth flagging: it is a *mechanism* complaint, and the `compact`
`load_reason` in §3.3 suggests re-injection is supposed to happen. Whether it
reliably does is exactly the kind of thing no published study has measured.

**Community-converged practice**, arrived at independently of any experiment:

- Mitchell Hashimoto (Ghostty): every line in the file traces to a real past agent
  mistake; nothing aspirational.
- Armin Ronacher: document the Makefile targets the agent can't guess.
- GitHub's 2,500-repo analysis: specific personas, executable commands with exact
  flags, real code examples over prose, explicit "never do X" boundaries; ~50–60
  lines for the effective template.
- Philipp Schmid (Google DeepMind DevRel): *"Don't use `/init` or let the agent
  write its own AGENTS.md, as the data shows this hurts more than it helps"* —
  citing S1 accurately.

**The offload consensus.** Anthropic's docs, Builder.io, and several independent
posts converge on the same routing, which is exactly what the new, opt-in `/init`
implements:

- **CLAUDE.md** — facts true in ~80%+ of sessions.
- **Skills** — occasional or domain-specific procedures; body loads on demand.
- **Hooks** — anything you want *enforced* rather than *suggested*. A hook runs
  outside the model's context and cannot be reasoned around.
- **Subagents** — isolated context for research, keeping the main session lean.

If a rule keeps being ignored, the fix is usually not a louder rule. It is a hook.

---

## 9. Local measurement

35 agent instruction files under `~/repos` (5 `CLAUDE.md`, 30 `AGENTS.md`),
measured 2026-09-19. Tokens estimated at ~4 bytes/token.

| Statistic | Bytes | ≈ tokens |
|---|---|---|
| Median | 6,359 | **~1,590** |
| Mean | 7,556 | ~1,889 |
| p90 | 13,200 | ~3,300 |
| Max (`clothesSearch/AGENTS.md`, 296 lines) | 27,230 | **~6,800** |
| Min | 76 | ~19 |
| Total across all 35 | 264,469 | ~66,100 |

**Reading.** The median file is comfortably inside Anthropic's ~200-line guidance
and costs about $0.02 per 50-turn Sonnet 5 session — irrelevant. The p90 and max
are the ones worth auditing, not because of cost but because of §6.2: a 296-line
file is likely carrying a lot of imperatives. None of the 35 approaches the
~40,000-character in-product warning threshold.

The 30:5 ratio of `AGENTS.md` to `CLAUDE.md` is itself notable — this machine has
already voted for the cross-vendor standard, which Claude Code only began reading
natively in v2.1.277.

---

## 10. Claims rejected

Circulating widely, and wrong or untraceable. Full reasoning in
[`evidence/verification-log.md`](evidence/verification-log.md).

| Claim | Verdict |
|---|---|
| *"No CLAUDE.md performed better in 5 of 8 tests"*, attributed to ETH Zurich (chaseai.io) | **Not in arXiv:2602.11988.** Publisher sells Claude Code consulting. Do not cite. |
| *"A 2025 GitHub developer survey found 30%+ fewer throwaway completions"* | Traces to no GitHub survey. Apparent fabrication. Do not cite. |
| *"Hundredfold gap in tool-invocation rates (1.6× vs <0.01×)"* | The 1.6× half matches S1's tool-adoption figure; the `<0.01×` half has no traceable source. Cite only the 1.6×, second-hand. |
| *"+2.7% from an auto-generated file even with no pre-existing docs"* | One research pass reported this from S1's body; it contradicts the abstract and the other pass. Not used. |
| S1 authors have an undisclosed LogicStar.ai conflict | The ETH SRI Lab publication page lists **ETH Zürich only**. Some co-authors are commercially active; no undisclosed COI is asserted here. |
| *"Splitting CLAUDE.md into @imports reduces context"* | **False.** Anthropic's docs: imports load at launch. Only `nested_traversal` and `path_glob_match` are lazy. |

---

## 11. What nobody has measured

1. **Success rate, cost and latency jointly, with repeated runs per condition.**
   S1 has success+cost but single runs; S3 has cost+latency but no correctness
   gate; S2 has correctness with repeats but not cost. AAIF (§4.3) showed the noise
   exceeds the effect, which makes every single-run study in this list suspect.
2. **`/init` output quality against ground truth.** Everyone asserts it is generic
   and goes stale. Nobody has diffed N `/init` files against what the repo actually
   requires.
3. **The two halves separately.** S1 found instructions help and overviews don't,
   but no study has ablated *commands-and-gotchas only* vs *overview only*. This is
   the single most decision-relevant experiment nobody has run — and it is cheap.
   S5 splits **coverage from precision**, which is a different axis, so the gap
   survives round 5 intact.
4. **Staleness decay.** No measurement of how a context file's value changes as the
   repo drifts away from it.
5. **Whether `compact` re-injection actually works**, given issue #29746 and S4's
   session-length decay finding.
6. **Anything at all for Copilot, Windsurf, Cline, Amp, Devin, Junie or OpenHands.**
7. **Non-Python, non-TypeScript.** S1's authors note Python's heavy training
   representation may nullify context-file effects; S4 was TypeScript-only.
8. **The capability window.** S5 pays on a 35B model and S1–S2 do not on frontier
   agents, while S5's own cross-model check has the procedure *failing* on a
   weaker model still. Nobody has run one design across a capability ladder, so
   "does it help?" is missing its qualifier: **help whom?**
9. **Probe-and-refine on a frontier agent.** The only procedure that produced a
   significant gain has never been tried on Claude Code or Codex. Cheapest
   high-value experiment now open.

---

## 12. Recommendation

For a working developer, the evidence supports this:

1. **Run `/init` once, as a draft.** It is a cheap first pass at the commands.
2. **Then delete the architecture tour.** It is the part S1 measured as unhelpful
   and the part Anthropic's own audit doctrine calls "dead weight". Apply the
   derivability test: *could a session reconstruct this with `ls`, `cat`, the
   manifest and `--help`?* If yes, cut it.
3. **Keep only what is not derivable:** non-standard build/test commands, required
   env setup, gotchas and failure contracts, conventions that *differ* from
   defaults, repo etiquette, safety prohibitions, domain glossary. Phrase rules as
   prohibitions where you can: in S6 every individually helpful rule was a "do
   not" and every harmful one a "do" (suggestive, not established). And keep them
   current — a stale convention *"costs more than no file"* (Mohammadi et al.).
4. **Write down what the agent got *wrong*.** This is the one intervention with a
   significance-tested positive result behind it (S5), and independently the one
   that lifts rule compliance from 49.14% to 72.13% (Cai et al.). A line earns its
   place by having prevented a specific failure — the same test Anthropic's own
   new, opt-in `/init` applies. It is also the only part of this list that gets
   *better* the longer you use the repo.
5. **Count your imperatives, not your lines.** §6.2 says rule count is the variable
   that degrades compliance. Reference material is cheap.
6. **Move enforcement to hooks.** A rule that keeps being ignored was never a
   CLAUDE.md problem. Hooks run outside the model's context and cannot be skipped.
7. **Move occasional procedures to skills, and module-specific guidance to
   subdirectory `CLAUDE.md` or `paths:`-scoped `.claude/rules/*.md`.** These are the
   only genuinely lazy loading mechanisms; `@imports` are not.
8. **Don't shrink it to save money.** §7 — the dollars are negligible. Shrink it to
   protect compliance.
9. **Expect no success-rate miracle *from a frontier agent*.** The two studies
   that measured correctness on Claude Code and Codex both put the effect
   indistinguishable from zero. The realistic wins there are **latency,
   compliance and avoided rediscovery**, not capability. S2's failure triage is
   blunt about why: agents fail on implementation skill, and no amount of
   repository documentation fixes that — S5 measures the same split and agrees,
   moving coverage by 14.5 pp while patch precision does not budge.
10. **If you drive a smaller or local model, weight this list differently.** The
    only measured success gain in the literature (S5) is on an open 35B model.
    Everything above is advice for pruning a frontier agent's context; on a
    weaker model a repository guidance file is load-bearing, and §4.1a explains
    why that is the same finding rather than a contradiction.

---

## 13. Sources

### Controlled ablations (grade A)
- Gloaguen, Mündler, Müller, Raychev, Vechev. *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?* [arXiv:2602.11988](https://arxiv.org/abs/2602.11988). MemAgents @ ICLR 2026, Oral & Runner-up Best Paper. SRI Lab, ETH Zürich. [Lab page](https://www.sri.inf.ethz.ch/publications/gloaguen2026agentsmd)
- Khatri. *Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories.* [arXiv:2607.27250](https://arxiv.org/abs/2607.27250)
- Lulla, Mohsenimofidi, Galster, Zhang, Baltes, Treude. *On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents.* [arXiv:2601.20404](https://arxiv.org/abs/2601.20404). JAWs @ ICSE 2026
- McMillan. *Instruction Adherence in Coding Agent Configuration Files: A Factorial Study of Four File-Structure Variables.* [arXiv:2605.10039](https://arxiv.org/abs/2605.10039)
- Shepard & Albrecht. *Probe-and-Refine Tuning of Repository Guidance for Coding Agents.* [arXiv:2606.20512](https://arxiv.org/abs/2606.20512) — **added round 5**
- Zhang, Wang, Cui, Qiu, Li, Zhu, He. *Guardrails Beat Guidance: A Large-Scale Study of Rules, Skills, and Persistent Configuration for Coding Agents.* [arXiv:2604.11088](https://arxiv.org/abs/2604.11088) — **added round 7**
- Griffiths. *Measuring AGENTS.md: What Five Runs Show That One Doesn't.* Agentic AI Foundation, 2026-07-22, [aaif.io](https://aaif.io/blog/measuring-agents-md-what-five-runs-show-that-one-doesn-t)

### Added in round 7 (mechanism and adjacent)
- Mohammadi, Klein, Chadha, Arora, Bindschaedler. *The Working Set of a Coding Agent: Coherence Debt in Repository-Scale Tasks.* [arXiv:2608.16630](https://arxiv.org/abs/2608.16630) — 7 models × 5 harnesses; *"where standard and code disagree, agents follow the standard even when it prescribes the worse code, so a stale convention file costs more than no file."*
- Huang et al. *Harness-IF: Evaluating Instruction Following Across Instruction Surfaces in Coding Agents.* [arXiv:2608.11727](https://arxiv.org/abs/2608.11727) — 12 frontier models, 256 rules; accuracy 72.1–85.9%, *"every model is worse on against-prior rules, by 3.6 to 7.4 points (mean 5.81)"*
- Kozyrev, Kozyrev, Podkopaev. *Skill Issue: Lessons from Optimizing Repository SKILLs for Coding Agents.* [arXiv:2609.12742](https://arxiv.org/abs/2609.12742) — Claude Code, 3 Kotlin repos; optimised documents +4.9 pp, which *"cannot be separated from the agent's run-to-run variance"*
- Bjarnason, Silva, Monperrus. *On Randomness in Agentic Evals.* [arXiv:2602.07150](https://arxiv.org/abs/2602.07150) — 60,000 trajectories; *"single-run pass@1 estimates vary by 2.2 to 6.0 percentage points"*
- Yang & Ding. *Signal or Noise? A Benchmark Study of Agent Skills in Web Development.* [arXiv:2608.23067](https://arxiv.org/abs/2608.23067) — injecting a matched skill *"reduces mean Pass@2 by 1.3% to 4.2%"* and raises token cost 72–394%: skills are not free when injected eagerly
- Wen et al. *MTAC-IFBench.* [arXiv:2609.14992](https://arxiv.org/abs/2609.14992) — instruction-following *"degrading rapidly as the interaction session grows longer"* (supports S4's session-length result; no effect size in the abstract)
- Yang, He, Zhou. *A First Look at Coding Agents' Compliance with AI Contribution Rules.* [arXiv:2607.26819](https://arxiv.org/abs/2607.26819) — agents *"almost never proactively retrieve the contribution rules"*

### Observational and descriptive (grades B–C)
- Arabat & Sayagh. *Toward Instructions-as-Code.* [arXiv:2606.13449](https://arxiv.org/abs/2606.13449). MSR 2026
- Jiang & Nam. *Beyond the Prompt: An Empirical Study of Cursor Rules.* [arXiv:2512.18925](https://arxiv.org/abs/2512.18925). MSR 2026
- Chatlatanagulchai et al. *Agent READMEs: An Empirical Study of Context Files for Agentic Coding.* [arXiv:2511.12884](https://arxiv.org/abs/2511.12884)
- Chatlatanagulchai et al. *On the Use of Agentic Coding Manifests: An Empirical Study of Claude Code.* [arXiv:2509.14744](https://arxiv.org/abs/2509.14744)
- Mohsenimofidi, Galster, Treude, Baltes. *Context Engineering for AI Agents in Open-Source Software.* [arXiv:2510.21413](https://arxiv.org/abs/2510.21413)
- Santos et al. *Decoding the Configuration of AI Coding Agents.* [arXiv:2511.09268](https://arxiv.org/abs/2511.09268)
- *Harness Engineering for Agentic AI Coding Tools.* [arXiv:2602.14690](https://arxiv.org/abs/2602.14690)
- Cai, Li, Liang, Li, Shahin. *Rule Taxonomy and Evolution in AI IDEs: A Mining and Survey Study.* [arXiv:2606.12231](https://arxiv.org/abs/2606.12231) — 83 projects, 7,310 rules, 1,540 evolution events, 99 practitioners; **compliance 49.14% → 72.13% after a rule update**. *Added round 5*
- Vasilopoulos. *Codified Context: Infrastructure for AI Agents in a Complex Codebase.* [arXiv:2602.20478](https://arxiv.org/abs/2602.20478) — single-project case study (108k-line C#, 283 sessions), observational only. *Added round 5*
- Lulla et al. *Loop Engineering: Building Blocks, Adoption, and Impact.* [arXiv:2608.21884](https://arxiv.org/abs/2608.21884) · Gao et al. *From Registry to Repository: How AI Agent Skills Are Written, Adapted, and Maintained.* [arXiv:2607.00911](https://arxiv.org/abs/2607.00911) · Abubakar et al. *An Exploratory Study of Agent Plans.* [arXiv:2608.04661](https://arxiv.org/abs/2608.04661) — adjacent artefacts (loops, skills, plans) by the same group; **none measures task success**, so none bears on the question. *Checked round 5*
- Nigh. *How to write a great agents.md: Lessons from over 2,500 repositories.* GitHub Blog, 2025-11-19

### Long-context and instruction-adherence mechanism
- Liu et al. *Lost in the Middle.* [arXiv:2307.03172](https://arxiv.org/abs/2307.03172), TACL
- Modarressi et al. *NoLiMa.* [arXiv:2502.05167](https://arxiv.org/abs/2502.05167), ICML 2025
- Hsieh et al. *RULER.* [arXiv:2404.06654](https://arxiv.org/abs/2404.06654), NVIDIA
- *LongBench v2.* [arXiv:2412.15204](https://arxiv.org/abs/2412.15204), ACL 2025
- Chroma Research. *Context Rot.* https://www.trychroma.com/research/context-rot
- *FollowBench.* [arXiv:2310.20410](https://arxiv.org/abs/2310.20410)
- *IFScale.* [arXiv:2507.11538](https://arxiv.org/abs/2507.11538)
- *ManyIFEval / When Instructions Multiply.* [arXiv:2509.21051](https://arxiv.org/abs/2509.21051), EMNLP 2025
- *Multi-IF.* [arXiv:2410.15553](https://arxiv.org/abs/2410.15553), Meta
- *SIFo.* [arXiv:2406.19999](https://arxiv.org/abs/2406.19999), EMNLP 2024 Findings
- *HANDBOOK.md.* [arXiv:2607.25398](https://arxiv.org/abs/2607.25398), WAB @ COLM 2026
- Shi et al. *LLMs Can Be Easily Distracted by Irrelevant Context.* [arXiv:2302.00093](https://arxiv.org/abs/2302.00093), ICML 2023; follow-up [arXiv:2505.18761](https://arxiv.org/abs/2505.18761)
- *Sufficient Context.* [arXiv:2411.06037](https://arxiv.org/abs/2411.06037), ICLR 2025

### Agent cost, exploration and context engineering
- *How Do AI Agents Spend Your Money?* [arXiv:2604.22750](https://arxiv.org/abs/2604.22750)
- Al Awad & Ivanov. *Cost-Effective Repository Exploration for Agentic Issue Localization.* [arXiv:2608.29675](https://arxiv.org/abs/2608.29675)
- *Same Task, Different Work: Prompt-Induced Waste in Coding Agents.* [arXiv:2608.01347](https://arxiv.org/abs/2608.01347) — preregistered; prompt wording multiplies reasoning cost 1.6–7.4× without improving correctness
- *Coding Agents are Effective Long-Context Processors.* [arXiv:2603.20432](https://arxiv.org/abs/2603.20432)
- *SWE Context Bench.* [arXiv:2602.08316](https://arxiv.org/abs/2602.08316)
- *RepoMirage.* [arXiv:2605.26177](https://arxiv.org/abs/2605.26177)
- *SWE-Pruner: Self-Adaptive Context Pruning for Coding Agents.* [arXiv:2601.16746](https://arxiv.org/abs/2601.16746)
- Zhang, Hu et al. *Agentic Context Engineering (ACE).* [arXiv:2510.04618](https://arxiv.org/abs/2510.04618) — SambaNova co-authored
- Chen et al. *How can we assess human-agent interactions?* [arXiv:2510.09801](https://arxiv.org/abs/2510.09801) — CMU + All-Hands-AI

### Vendor primary sources (grade D)
- Claude Code docs: [memory](https://code.claude.com/docs/en/memory), [best-practices](https://code.claude.com/docs/en/best-practices), [costs](https://code.claude.com/docs/en/costs), [prompt-caching](https://code.claude.com/docs/en/prompt-caching), [context-window](https://code.claude.com/docs/en/context-window), [commands](https://code.claude.com/docs/en/commands)
- [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Anthropic Engineering: [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (2025-09-29), [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) (2025-09-11), [Multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system) (2025-06-13)
- [Lessons from building Claude Code: prompt caching is everything](https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything) (2026-04-30)
- [How Claude Code is used in practice](https://www.anthropic.com/research/claude-code-expertise) (2026-06-16)
- [anthropics/claude-code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- OpenAI Codex: [AGENTS.md configuration](https://developers.openai.com/codex/agent-configuration/agents-md)
- [agents.md](https://agents.md); [Agentic AI Foundation](https://openai.com/index/agentic-ai-foundation/) (2025-12-09)
- [Cursor rules docs](https://cursor.com/docs/rules); [Aider repo map](https://aider.chat/docs/repomap.html); [Aider SWE-bench Lite](https://aider.chat/2024/05/22/swe-bench-lite.html); [Aider unified diffs](https://aider.chat/2023/12/21/unified-diffs.html)
- [OpenHands repo microagents](https://docs.openhands.dev/modules/usage/prompting/microagents-repo)

### This repository's own primary extraction
- [`evidence/primary-binary-extracts.md`](evidence/primary-binary-extracts.md) — `/init` prompt, the opt-in second `/init`, audit doctrine, load semantics, extracted from Claude Code v2.1.278
- [`evidence/verification-log.md`](evidence/verification-log.md) — what was re-verified, what conflicted, what was rejected
