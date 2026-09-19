# claudeCodeInit

An evidence review of one narrow question:

> Claude Code's `/init` writes a `CLAUDE.md` that is then loaded into every later
> session. Does that make follow-up work faster, cheaper or better — or is it
> clutter that costs tokens and dilutes attention?

**Short answer: the practice is sound, the default artefact is not.** Instructions
in a context file are followed and earn their tokens. The repository overview that
`/init` also writes does not — and cannot be fixed by writing a better one.

## Read this first

| File | What it is |
|---|---|
| **[`whitepaper.md`](whitepaper.md)** | **The meta-study.** A 5-sentence TL;DR, then the full synthesis. Start here. |
| [`paper.pdf`](paper.pdf) | 3-page journal-style paper with figures — Petrick & Claude Opus 5. Built from [`paper.tex`](paper.tex). |
| [`LI.pdf`](LI.pdf) | 5-page LinkedIn carousel, two bullets per page. Built from [`LI.html`](LI.html). |
| [`results.md`](results.md) | The raw dossier: every finding, grade, table and source from all three research rounds. |
| [`evidence/`](evidence/) | Primary extracts, verification log, self-review, round-3 notes. |
| [`fig/`](fig/) | Figure sources ([`make_figs.py`](fig/make_figs.py)) and vector PDFs. |

## The findings in brief

1. **The effects are smaller than the noise.** Temperature-0 inference flips ~9% of
   per-instance outcomes between *byte-identical* runs. Every published point
   estimate (−5.9 to +4.0 pp) sits inside that band, and the study producing several
   of them sampled each instance once, with no significance testing.
2. **The file is two artefacts with opposite signs.** A tool named in the file is
   used **1.6×** per task versus **<0.01×** unmentioned. Repository overviews do not
   measurably speed up file-finding, yet appear in **100%** of LLM-generated files.
3. **Prose about code is a lossy encoding of code.** Natural-language summaries
   answer **4/45** behavioural questions where the source answers **27/45** — and a
   frontier model's summaries score *exactly as poorly* as a 3B model's.
4. **The artefact has no brake.** Context files grow **+226%** over their lifetime
   (+4.9 instructions per commit, 247,694 lifetimes), and the older a line is, the
   *less* likely it is ever deleted.
5. **Cost is real; money is not.** Context files cost +20–23% inference — but
   `CLAUDE.md` sits in a cached layer, so even a 10,000-token file costs ~$0.12 per
   50-turn session. Shrink it to protect compliance, not to save money.
6. **The principle.** Scaffolding decays when it *substitutes* for a capability the
   model now has natively; it persists when it *supplies* information the model
   cannot derive or *enforces* a constraint it cannot infer. The overview
   substitutes. The gotchas supply. That is why the halves differ.

## How the research was done

Three rounds, ten parallel agents, plus two local primary-source efforts.

- **Round 1** mapped the field: academic literature, vendor docs, practitioner grey
  literature, cross-harness comparison, context economics.
- **Round 2** closed round 1's gaps: read the **full text** of every controlled
  study rather than the abstract, hunted for missed work, and re-verified pricing.
- **Round 3** asked why `/init` exists, and tested the scaffolding-decay hypothesis.

Produced locally rather than searched for:

- **Binary extraction.** The shipped Claude Code executable (v2.1.278) was mined
  with `strings` and byte-offset reads, recovering the literal `/init` prompt, an
  **unreleased second `/init`** gated behind a feature flag, the CLAUDE.md audit
  doctrine, and exact loading semantics. This proved to be the most decisive
  evidence in the review.
- **Corpus measurement.** All 35 agent instruction files under `~/repos`
  (median ≈1,590 tokens, p90 ≈3,300, max ≈6,800).

### On not trusting the research

Agent output was **not** taken at face value. Every load-bearing paper was
re-fetched from arXiv and checked. This caught:

- two passes reporting **incompatible numbers** from the same paper body;
- one pass reporting **p-values that do not exist** in the paper it cited;
- one pass **dismissing a real, verified paper** as an untraceable mis-citation;
- one pass **mischaracterising** the single most relevant paper in the dossier;
- two **fabricated** statistics in wide circulation;
- one **vendor figure absent from its own source**.

All recorded in [`evidence/verification-log.md`](evidence/verification-log.md).
[`evidence/self-review.md`](evidence/self-review.md) records three overstatements
found in *our own* first draft and corrected.

## Rebuilding the artefacts

```bash
python3 fig/make_figs.py                       # figures -> fig/*.pdf
pdflatex paper.tex && pdflatex paper.tex       # -> paper.pdf (3 pages, A4)
chromium --headless --no-pdf-header-footer \
  --print-to-pdf=LI.pdf LI.html                # -> LI.pdf (5 pages, 1080x1080)
```

Binary extraction:

```bash
BIN=~/.local/share/claude/versions/<version>
strings -n 20 "$BIN" > strings.txt
grep -n "Please analyze this codebase and create a CLAUDE.md" strings.txt
```

Minified symbol names differ between builds — grep for prompt text, not identifiers.

## Caveats

- **The causal base is four unreplicated 2026 preprints**, three underpowered for
  the effects they report. None is journal-published; none has been rebutted.
- **No experiment of our own.** This is a synthesis; the local corpus measurement
  is descriptive only.
- **Cost tables are modelled**, with assumptions stated inline.
- **Single binary version** on one machine; the gated `/init` may never ship.
- **The search budget was exhausted** (200/200 queries) during round 3, which
  therefore relied on targeted fetches of known sources rather than open search.
- **Recency.** Claude Code shipped three versions during the week this was written.

## Related

[`../AgentsMdSurvey`](../AgentsMdSurvey) surveys the agent instruction files that
actually exist across a directory of repositories. That project asks *what people
write*; this one asks *whether it helps*.
