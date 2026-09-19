# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read `HANDOFF.md` first — it states the current task and the repository's remote state.

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

## Rebuilding artefacts

```bash
python3 fig/make_figs.py                    # figures -> fig/*.pdf
pdflatex paper.tex && pdflatex paper.tex    # -> paper.pdf (must stay <= 3 pages)
chromium --headless --no-pdf-header-footer --print-to-pdf=LI.pdf LI.html
```

`paper.tex` avoids `titlesec` and `enumitem` — neither is installed on this machine.
