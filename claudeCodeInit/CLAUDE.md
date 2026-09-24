# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`HANDOFF.md` describes a task that is **complete** (author lookups, closed
2026-09-20); keep it as the record, but there is no open task in it.

## What this project is

An evidence review of whether `/init`-generated context files help coding agents.
`whitepaper.md` is the synthesis, `paper.pdf`/`paper.tex` the 3-page paper,
`LI.pdf`/`LI.html` a 5-slide LinkedIn carousel (1080×1350), `LI-post.md` its post text, `results.md` the full dossier, `evidence/`
the primary extracts and verification logs. **These five must agree with each
other** — a claim changed in one has to be changed in all of them, including the
figures.

## Non-obvious constraints

- **Verify remote state with `git ls-remote origin refs/heads/master`, not
  `origin/master`.** A previous session reported a file as unpushed when it was
  already public. Never tell the user something is unpublished without checking.
- **Never push without asking.** This repository is public.
- **Never publish a profile URL, statistic or citation that was not verified
  against a primary source.** Two statistics circulating about this topic are
  fabricated, and one research pass invented p-values for a paper that contains no
  significance testing. `evidence/verification-log.md` records each case.
- **Grade confidence explicitly** (HIGH / MEDIUM / absent) on any claim about a
  real person's identity, and prefer an empty slot to a plausible guess.
- **A confirmed absence of evidence is a result**, not a gap to paper over.
- **The evidence base moves.** Round 5 (2026-09-20) found a controlled ablation
  three earlier rounds had missed — public for three months, and it overturned an
  inference in the TL;DR. Round 7 (2026-09-24) found another, the largest of all
  (arXiv:2604.11088), public for five months. Before trusting any count ("six
  controlled ablations"), re-sweep. Assume the current version is incomplete.
- **Check pairings, not just numbers.** Round 7 found every number in the AAIF
  example correct and the comparison wrong: two figures from different tasks.
- **Quote abstracts from the raw source.** `curl` the arXiv abstract page and read
  the `<blockquote class="abstract">`; for PDFs the fetch tool cannot decode, use
  `pdftotext`. Do not log a quotation that passed through a summarising model.

## Rebuilding artefacts

```bash
python3 fig/make_figs.py                    # figures -> fig/*.pdf
pdflatex paper.tex && pdflatex paper.tex    # -> paper.pdf (must stay <= 3 pages)
chromium --headless --no-pdf-header-footer --print-to-pdf=LI.pdf LI.html   # 5 pages, 1080x1350
```

`paper.tex` avoids `titlesec` and `enumitem` — neither is installed on this
machine. Figure 1's height drives the paper's page count. It is 2.86 inches, and
at that height page 3 is exactly full: any added line of prose, or a taller
figure, pushes the bibliography onto a fourth page.

**Every document here must pass the clear-writing check.**

```bash
python3 tools/readability.py paper.tex     # .tex or .md; exits 1 if a target slips
```

It reads `.tex` and `.md` only; for `LI.html`, extract the slide text to a
scratch `.md` first. It measures sentence length, passive voice and word complexity, excluding
quotations (rewriting a quotation would misquote it). The paper states its own
scores in §2 -- if you change the prose, re-run the tool and update those
numbers, or the paper misreports itself.

**Always look at what you rebuilt.** `pdftoppm -r 130 -png paper.pdf out` and read
the images. Two defects in the carousel (a decorative blob painting over the
verdict bar, a heading colliding with a card) were invisible in the source and
obvious in the render.
