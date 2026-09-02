# LinkedIn post — surveying my own AGENTS.md files

Draft plus the numbers behind it. Every figure comes from
`./run.py ~/repos`, scanned on 2026-09-02; nothing here is estimated by hand.
Regenerate before posting if the tree has moved on.

**Everything published from this survey — the images in `media/`, any hosted
copy of the report — is generated with `./run.py --redact`,** which masks
customer repository names while keeping every count intact. Regenerate the same
way; a plain `./run.py` writes the real names, which is right for the local
report and wrong for a post.

---

## The post

**I have been writing AGENTS.md files for months. I had never read them side by side.**

So I wrote a tool that does: it walks a directory of repositories, finds every
`AGENTS.md`, `CLAUDE.md`, `SKILL.md` and harness config, splits them into atomic
rules, and counts what recurs. 120 repositories, 38 first-party instruction
files, 1,156 rules.

Five things I did not expect.

**1. My most-repeated rule is not about commits.**
It is *"verify before you claim it works"* — present in 18 of 30 instructed
scopes (60%), ahead of Conventional Commits (57%). I would have guessed the
opposite order. Apparently what I mostly need from an agent is not tidy commits
but honesty about what it has actually checked.

**2. Only 39% of my active repositories have any instructions at all.**
Counting only repositories with a commit in the last 182 days — the ones where
it costs something — 25 of 64 are instructed. Narrowed to an AGENTS.md
specifically: 20 of 64, or 31%. Nearly seven in ten of the repositories I am
actually working in start every agent session from zero context.

**3. I spell the filename three different ways.**
`AGENTS.md` (19), `agents.md` (6), `agent.md` (1) — on a case-sensitive
filesystem, with tools that match exactly. And they live in three different
places: repository root (10), a docs folder (8), somewhere nested (8). Some of
those files are simply never read, and nothing tells you.

**4. 72% of what I wrote is not actually a rule.**
Only 24% of the 1,156 directives use binding language (must / never / always).
The rest is description and command cheat-sheets sharing a filename with the
rules. Three documents wearing one name — which is exactly why an AGENTS.md
cannot just be copied to the next project.

**5. The instructions cost ~52,000 tokens.**
Spread over 30 scopes, paid before any work happens. The heaviest single scope
is 6,807 tokens — a file I wrote to save time.

Two repositories turned out to share 70% of their headings. I had been copying a
template for months without noticing I had one. So the tool now writes it down:
it synthesizes a canonical AGENTS.md from the rules that recur across four or
more repositories, each line quoting wording already in service, with the count
that justifies it.

The interesting part was deciding what needs a language model. Finding the files
and splitting them into rules is a parser — deterministic, testable, no model.
Recognising *"use Conventional Commits"* is a regex. But recognising that
*"one concern per commit"*, *"atomic commits"* and *"each commit has one reason
to change"* are one rule in three costumes is not. My lexicon classified 38% of
the rules; the other 62% is the tail that needs semantics.

So: deterministic core, optional cached semantic pass, and one rule that keeps
it honest — **the model may label, cluster and phrase. It never counts.**
Every number above survives the model being switched off.

Tooling: Python, standard library only, ~2,800 lines plus tests. One command,
one self-contained HTML report.

#AI #SoftwareEngineering #DeveloperTools #Python #ClaudeCode #Codex

---

## Suggested images

| Order | File | Why it earns the slot |
|---|---|---|
| 1 | `media/03-topic-frequency.png` | The headline chart — leads with the surprise in point 1. |
| 2 | `media/02-coverage-of-active-repos.png` | The 39% finding with its evidence list. |
| 3 | `media/01-headline-numbers.png` | Scale of the corpus in one row. |
| 4 | `media/04-themes-and-binding.png` | The 24% binding-language split. |
| 5 | `media/06-canonical-agents-md.png` | The payoff: the generated house standard. |

Alternates: `05-context-budget.png` (token cost), `07-naming-inconsistency.png`
(the three spellings), `09-repeated-wordings.png` (rules copied by hand between
repos), `08-topic-frequency-dark.png` (dark-mode version of image 1).

---

## The numbers, verbatim

### Corpus
| | |
|---|---|
| Repositories scanned | 120 (plus 30 nested checkouts excluded: submodules, worktrees, vendored clones, build artefacts) |
| Repositories with instructions | 25 |
| Active repositories (commit in last 182 days) | 64 |
| **Active and instructed** | **25 (39%)** |
| **Active with an AGENTS.md specifically** | **20 (31%)** |
| Dormant repositories | 56 |
| Instruction files found | 60 |
| First-party | 38 |
| Vendored or duplicate, excluded | 22 |
| Instructed scopes | 30 |
| Atomic directives | 1,156 |
| Matched by the lexicon | 443 (38%) |
| Total instruction budget | ~51,912 tokens |
| Median scope | ~1,264 tokens |
| Heaviest scope | `personalNotes/clothesSearch`, 6,807 tokens |

### The house style, ranked by how many scopes state it
| Rank | Topic | Scopes | Share |
|---|---|---|---|
| 1 | Verify before claiming success | 18 / 30 | 60% |
| 2 | Conventional Commits | 17 / 30 | 57% |
| 3 | CI must be green | 15 / 30 | 50% |
| 4 | Run the gate before committing | 15 / 30 | 50% |
| 5 | Formatting and linting | 13 / 30 | 43% |
| 6 | Toolchain and environment | 11 / 30 | 37% |
| 7 | Tests must pass / write tests | 9 / 30 | 30% |
| 8 | Architecture boundaries | 9 / 30 | 30% |

29 topics recur across four or more scopes; 7 appear exactly once. The first
group is the house standard, the second is project-specific and must stay local.

### Language
- Binding (must / never / always): 281 directives, 24%
- Advisory (should / prefer): 42, 4%
- Unmarked: 833, 72%
- Sections that are rules: 73%. Description: 13%. Command cheat-sheets: 6%.
  Reference: 7%.

### Inconsistencies
- Filename: `AGENTS.md` 19, `agents.md` 6, `agent.md` 1.
- Location: root 10, docs folder 8, nested 8 — across `docs/`, `documents/` and
  `documentation/`.
- 3 sets of byte-identical files, including one mirrored into `build/`.
- 1 pair of scopes sharing 70% of their headings — the template I did not know
  I had.
- 2 files stale by 90+ days of repository activity, the worst by 847 days.
- 19 instruction files in the tree belong to vendored dependencies — roughly
  16,770 tokens of other people's rules, which an agent started in those
  directories would still read.

### The CLAUDE.md convention
Where both files exist, CLAUDE.md is a 3–8 line pointer to AGENTS.md — applied
in 3 of 3 cases. One scope still has a standalone CLAUDE.md with no AGENTS.md.

---

## A footnote worth its own paragraph

While reviewing the tool that produced these numbers, the review found a bug in
it: the activity filter read `(days_since_last_commit or 1_000_000) <= 182`. A
repository committed to **today** is zero days old, zero is falsy, so the
fallback fired and the most active repositories were classified as dormant. The
figure moved underneath me as my own commits landed during the session.

Two lessons, and the second one is the real one. First: `or` as a null-check is
a trap wherever zero is a legitimate value. Second: the bug was found because
the number changed when nothing that should affect it had changed — and the
number was cheap enough to recompute independently. Build the thing that lets
you check the thing.
