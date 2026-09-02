# AgentsMdSurvey — Vision

## 1. The question this project answers

Over the last months a corpus of agent instruction files has accumulated across
`~/repos`: `AGENTS.md`, `agents.md`, `agent.md`, `CLAUDE.md`, `.claude/`
directories, skills, settings. They were written one at a time, mostly by hand,
sometimes by an agent, never against a shared template. Nobody has ever read
them side by side.

Three things follow from that, and this project exists to establish them:

1. **What is actually in there.** How many repositories carry instructions, in
   which files, under which names, in which locations, how long they are, and
   what they demand.
2. **What the house style really is.** Not the style I believe I have — the one
   that is empirically present, measured by how often a rule recurs across
   independent repositories.
3. **What the canonical file should be.** A synthesized `AGENTS.md` containing
   the rules that recur, with provenance, so future repositories start from the
   distilled version instead of from whatever the last repository happened to
   say.

## 2. Is a deterministic tool possible, or is an LLM required?

Both, in layers. The honest answer is that the pipeline splits into three
stages, and only the third is genuinely ambiguous.

### Layer 1 — Collection: fully deterministic, no LLM

Walking a directory tree, matching filenames against a known set of conventions,
hashing contents, resolving which git repository a file belongs to, reading
`git log` for last-modified dates, detecting vendored/third-party copies. There
is no judgement here. This layer must never call a model, must be exactly
reproducible, and must be fast enough to run on every repository root without
thinking about it.

### Layer 2 — Segmentation and normalization: deterministic

Parsing markdown into a heading tree, splitting each section into atomic
*directives* (a bullet, a numbered item, an imperative sentence), stripping
formatting, normalizing whitespace and casing, and hashing each directive.
This turns ~40 documents into a few thousand comparable units. Still no
judgement: it is a parser, and a parser is testable.

The important design consequence: **the unit of analysis is the directive, not
the file.** File-level statistics ("40 files, 190 KB") are almost content-free.
Directive-level statistics ("31 of 34 first-party files mandate Conventional
Commits") are the actual finding.

### Layer 3 — Classification: hybrid, and this is where the LLM earns its place

A deterministic lexicon classifier — regex and keyword rules per topic, kept in
a version-controlled taxonomy file — handles the head of the distribution very
well. Topics like *Conventional Commits*, *never push*, *bump the version*,
*exact dependency pins*, *English only*, *run the quality gate before commit*
have stable, low-variance vocabulary. They are recognizable with rules, the
rules are auditable, and the result is reproducible byte for byte.

What the lexicon cannot do:

- **Discover categories nobody anticipated.** A rule that appears in four repos
  in four different phrasings, on a topic not in the taxonomy, is invisible to a
  keyword matcher. That is precisely the interesting finding.
- **Resolve paraphrase.** "One concern per commit", "atomic commits", "each
  commit has one reason to change", and "do not mix refactoring with features"
  are one rule wearing four costumes. Lexical matching either misses three of
  them or over-matches half the corpus.
- **Detect contradiction.** Repo A says *never push*; repo B says *push after
  the gate is green*. Both classify as "push policy"; only semantics reveals
  that they disagree, and the canonical file has to pick one.
- **Write the synthesis.** Merging four phrasings into one crisp house rule is a
  writing task.

So the architecture is: **deterministic core, optional semantic enrichment.**

- The deterministic pipeline alone produces a complete report. `--no-llm` is a
  supported, first-class mode, and CI runs in it.
- The enrichment pass adds: embedding-based clustering of the directives the
  lexicon left unclassified, LLM labels for the clusters that emerge, paraphrase
  merging inside a topic, contradiction detection, and the prose of the
  synthesized `AGENTS.md`.
- Every model call is **cached on disk keyed by the SHA-256 of its input**. A
  second run costs nothing and returns identical output. The cache is a
  committed artifact, so the report is reproducible by someone without a model.
- Local first: Ollama on the existing hosts for both embeddings and labeling,
  with the model name recorded in the report. Nothing about this needs a
  frontier model; it needs a *consistent* one.

The design rule that keeps this honest: **the LLM may label, cluster, and
phrase. It may never count.** Every number in the report comes from the
deterministic layers. If the model disappears, the report loses its category
names for the long tail and its synthesized prose, and keeps every statistic.

## 3. What we are counting

### Corpus and coverage
- Repositories scanned, repositories with at least one instruction file, and the
  coverage ratio.
- File-name variants: `AGENTS.md` vs `agents.md` vs `agent.md` vs `CLAUDE.md`
  vs `.cursorrules` vs `copilot-instructions.md`, and casing inconsistencies
  that matter on a case-sensitive filesystem.
- Placement: repository root vs `docs/` vs `documents/` vs `documentation/`.
  Three different conventions for the same intent is itself a finding.
- Total instruction volume in bytes and estimated tokens — the *context budget*
  that every agent session in that repository silently pays.

### Provenance and hygiene
- **Third-party instructions.** Vendored dependencies (`node_modules`,
  submodules, `runtime/llama.cpp`) carry other people's `AGENTS.md`. These must
  be detected and excluded from the house-style statistics, or the results are
  contaminated — but counted separately, because they still get loaded into
  context.
- **Exact duplicates by content hash.** Build directories replicate `docs/`;
  the same file exists twice. Which copy is the source?
- **Near-duplicates.** Two repositories with the same section list and the same
  headings mean an implicit template already exists. Finding and naming it is
  half the deliverable.
- **Stub-and-pointer pattern.** A three-line `CLAUDE.md` next to a 400-line
  `AGENTS.md` is a deliberate pattern (one canonical file, one redirect).
  Measuring how consistently it is applied says whether it is a convention or an
  accident.
- **Staleness.** Last commit touching the instruction file vs last commit in the
  repository. An instruction file that has not moved in 200 commits is
  describing a project that no longer exists.

### Content
- Topic frequency across repositories: for each taxonomy topic, in how many
  *distinct first-party repositories* does it appear. Repository count, not
  directive count — one repository repeating itself must not outvote three
  repositories agreeing.
- Rule hardness: density of MUST / NEVER / ALWAYS / "non-negotiable" versus
  "prefer" / "should" / "consider".
- Structure: heading depth, directive count per file, and the share of the file
  that is *rules* versus *project description* versus *command cheat-sheet*.
  These are three different documents wearing one filename, and separating them
  is a prerequisite for a sane template.
- Universality: rules present in ≥ N repositories (candidates for the canonical
  file) versus rules present exactly once (project-specific, must stay local).

### Findings the report should be able to state
- The empirical house style, ranked.
- The rules I believe are universal but which are actually in a minority of
  repositories — the gap between intent and practice.
- Contradictions between repositories, listed as decisions to make.
- Repositories with no instructions but with active recent commits — the
  coverage backlog, ranked by repository activity.
- The context-budget outliers: the repositories where instructions are so long
  that they crowd out the actual work.

## 4. The deliverables

1. `agentsmdsurvey` — a Python package, no mandatory network access, no
   mandatory model.
2. A machine-readable `survey.json`: every file, every directive, every
   classification, with provenance. Everything downstream reads this, so the
   expensive scan happens once.
3. A self-contained HTML report — one file, inline CSS and SVG, no CDN, opens
   from the filesystem — with the charts and the findings.
4. `AGENTS.canonical.md` — the synthesized house-standard instruction file,
   built from rules that recur across repositories, each carrying a comment with
   the repository count that justifies it.
5. A test suite covering layers 1 and 2 against fixtures, because those layers
   are the ones that must never silently change.

## 5. Principles

- Deterministic by default; the model is an optional enrichment, never a
  dependency of the numbers.
- Cache every model call by input hash; a re-run must be free and identical.
- Count repositories, not lines, whenever the question is "what is my style".
- Separate first-party from vendored before computing anything.
- The report must survive being sent to someone with no access to this machine:
  one HTML file, no external assets.
- Read-only against the surveyed tree. The tool never writes into a scanned
  repository.
