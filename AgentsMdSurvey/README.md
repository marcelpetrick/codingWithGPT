# AgentsMdSurvey

Survey every agent instruction file under a directory of repositories — every
`AGENTS.md`, `agents.md`, `CLAUDE.md`, `GEMINI.md`, `SKILL.md`, `.cursorrules`,
`copilot-instructions.md` and `.claude/` config — and answer three questions:

1. What exists, where, and how much of it.
2. What the house style actually is, measured by what recurs across independent
   repositories rather than by what you believe you always do.
3. What the canonical `AGENTS.md` would be if it were written down.

The rationale, the design and the deterministic-versus-LLM argument are in
[Vision.md](Vision.md).

## Run it

```bash
./run.py                      # scans ~/repos, writes out/report.html
./run.py /path/to/repos       # somewhere else
./run.py --out /tmp/survey    # different output directory
./run.py --no-git             # skip git history: faster, loses the staleness findings
./run.py --redact             # mask customer repository names before writing anything
```

`--redact` is for output that leaves the machine. Some repository names identify
a customer or a product; the survey still counts them, because dropping them
would falsify coverage, but every occurrence is masked in the report, the
canonical file and the JSON alike — first character kept, the rest blocked out,
length preserved:

```
acmeanalyzer  ->  a███████████
```

The stems are themselves the sensitive part, so they are **not in the code**:
bare `--redact` reads them from `redact.stems` beside `run.py`, one per line,
which is untracked on purpose. Without that file the flag stops with an error
rather than writing an unredacted report. Pass `--redact stem1,stem2` to supply
them directly. A stem matches a whole name token, so `abc` masks `abc` and
`abc_tooling` without touching ordinary prose.

**Everything in `media/` and anything published is generated with `--redact`.**

Standard library only. No install step, no virtualenv, nothing to fetch. Three
files land in `out/`:

| File | What it is |
|---|---|
| `report.html` | The report: charts, findings, tables. One file, no external assets, opens from disk. |
| `AGENTS.canonical.md` | The synthesized house standard, every line carrying its scope count and source. |
| `survey.json` | Every file, directive and classification, for anything you want to ask afterwards. |

## How it works

Three layers, and only the third is genuinely ambiguous.

**Layer 1 — collection.** Walks the tree, matches the filename conventions the
harnesses read, attributes each file to a *scope* (the directory it governs), a
project and a git repository, and records size, hash and git history. Vendored
clones, submodules and byte-identical build copies are separated out, or the
house-style statistics would be measuring somebody else's rules.

**Layer 2 — segmentation.** Parses markdown into a heading tree and emits one
*directive* per bullet, numbered item or imperative sentence, each with its
heading path, its hardness (`must`/`never` versus `should`/`prefer`) and a
fingerprint over its normalized form. The directive, not the file, is the unit
of analysis: "40 files, 200 KB" says nothing, "16 of 29 scopes mandate
Conventional Commits" is a finding.

**Layer 3 — classification.** A versioned lexicon of ~50 topics handles the head
of the distribution, where vocabulary is stable and patterns are auditable. It
does not reach the tail, and it is not supposed to:

```bash
./run.py --llm ollama --llm-host http://192.168.178.67:11434
```

adds an optional pass that embeds the unclassified directives, clusters them,
and asks a model only to *name* each cluster — plus a yes/no question per
polarity candidate, since real contradictions need semantics. Every call is
cached under the SHA-256 of its input, so a second run is free and byte-identical,
and an unreachable model degrades to the deterministic report with every number
unchanged.

The rule that keeps this honest: **the model may label, cluster and phrase; it
never counts.** Every figure in the report comes from layers 1 and 2.

## Known limits

- Lexicon precision is imperfect. A sentence can match a topic it only brushes
  against, so a handful of rows in the canonical file carry a label that is
  close rather than exact. The semantic pass exists to fix this; without it,
  read the label as a hint and the quoted rule as the fact.
- Scope resolution assumes an instruction file governs its own directory. A file
  buried deep inside a project is treated as its own scope.
- Coverage counts repositories directly under the scan root. Submodules,
  worktrees, vendored clones and generated fixtures are reported separately
  rather than diluting the denominator.
- Token figures are `bytes / 4`. Good enough to rank a context budget, not a
  billing statement.

## Tests

```bash
python3 -m unittest discover -s tests
```

Discovery and segmentation are pinned against fixtures, because they are the
layers every number rests on. The semantic pass is tested through an injected
transport, so the cache contract and the offline path are covered without a model.
