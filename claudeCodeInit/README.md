# claudeCodeInit

An evidence review of one question:

> Claude Code's `/init` writes a `CLAUDE.md`, and the agent loads that file into
> every later session. Does that make the agent better — or is it clutter?

**Short answer: not reliably better at solving tasks.** Agents follow the rules in
the file, but a tour of the codebase does not help them, and rewriting it will not
fix that. The one clear gain comes from a file that records the agent's own
mistakes, on a model weak enough to need the help. Run `/init` once, then delete
most of it.

## Read this first

| File | What it is |
|---|---|
| **[`whitepaper.md`](whitepaper.md)** | **The review in plain language.** Five findings first, then what to do, then the evidence. Start here. |
| [`LI.pdf`](LI.pdf) | 5-slide LinkedIn carousel (1080×1350). Built from [`LI.html`](LI.html). |
| [`paper.pdf`](paper.pdf) | 3-page paper with figures. Built from [`paper.tex`](paper.tex). |
| [`results.md`](results.md) | The full dossier: every study, grade, table and source from all seven rounds. |
| [`whitepaper_authors.md`](whitepaper_authors.md) | Who to credit and tag, with a confidence grade per person. |
| [`evidence/`](evidence/) | Binary extracts, verification log, self-review, round-3 notes. |
| [`fig/`](fig/) | Figure sources ([`make_figs.py`](fig/make_figs.py)) and vector PDFs. |
| [`tools/readability.py`](tools/readability.py) | The clear-writing check every document here must pass. |

## The findings in brief

1. **No reliable gain on frontier agents.** Six controlled studies exist. On full
   benchmarks the effects on Claude Code, Codex and similar agents run from −5.9
   to +4 points, all within chance. The largest study (Claude Code, Opus 4.6)
   found a small nudge on borderline tasks, but **random rules scored exactly as
   well as expert ones** ([arXiv:2604.11088](https://arxiv.org/abs/2604.11088)).
2. **It costs more.** +20–23% per task in the ETH Zürich study. In money that is
   small, because Claude Code caches the file: about 12 cents for a 10,000-token file over
   a 50-turn session.
3. **The file is two files.** Agents follow the rules: when the file names a tool,
   the agent uses it **1.6×** per task, against **<0.01×** when it does not. The codebase tour does
   not help: a summary of code answers **4 of 45** questions about what it does;
   the code itself answers **27**.
4. **Writing down the agent's mistakes helped.** A file tuned against the agent's
   failures raised tasks solved from **25.5% to 33.0%** (*p*<0.001, four trials),
   on an open 35B model. It helped the agent find the right file, not write better
   fixes ([arXiv:2606.20512](https://arxiv.org/abs/2606.20512)).
5. **The files only grow, and stale lines do harm.** Files grow **+226%** over
   their life and old lines are almost never deleted. When file and code disagree,
   agents follow the file — *"a stale convention file costs more than no file"*
   ([arXiv:2608.16630](https://arxiv.org/abs/2608.16630)).
6. **Most published numbers are noise.** About **9%** of results flip between two
   identical runs, and many studies ran each task once. Only repeated trials can
   tell a small gain from luck.

## How the research was done

Seven rounds between 19 and 24 September 2026, most with several AI research
agents in parallel, plus two sources we produced ourselves:

- **Binary extraction.** We read the prompt text inside the shipped Claude Code
  program (v2.1.278, re-checked on v2.1.282): the literal `/init` prompt, a second
  `/init` that is now a documented opt-in (`CLAUDE_CODE_NEW_INIT=1`) but still off
  by default, and the exact loading rules.
- **Corpus measurement.** All 35 agent instruction files in our own repositories
  (median ≈1,590 tokens, p90 ≈3,300).

Rounds 1–3 mapped the field, read every controlled study in full, and asked why
`/init` exists. Round 4 verified the authors. Round 5 found a study three rounds
had missed, which changed a headline claim. **Round 7 (24 September) found the
largest study of all**, public since April and missed by every earlier round, and
caught one of our own errors (below).

### On not trusting the research

We did not take any agent's output at face value. We fetched every important
number again from the original source. This caught two agents giving conflicting
numbers from one paper; one inventing p-values; one dismissing a real paper as a
fake citation; two widely circulated statistics with no real source; and one vendor
figure missing from its own source. Round 7 caught a mistake of ours: we had
paired numbers from **two different tasks** in the Agentic AI Foundation example.
Every case is in [`evidence/verification-log.md`](evidence/verification-log.md)
and [`evidence/self-review.md`](evidence/self-review.md).

## Is any of this readable?

We measure it rather than argue about it. `tools/readability.py` scores sentence
length, passive voice and word complexity, and fails if a document slips:

```bash
python3 tools/readability.py whitepaper.md    # or paper.tex, or any .md here
```

| Document | Flesch | Median sentence | Over 30 words | Passives / 100 |
|---|---|---|---|---|
| `whitepaper.md` | 64.4 | 11 w | 3.2% | 6.0 |
| `README.md` | 62.9 | 12 w | 6.1% | 4.1 |
| `paper.tex` | 47.5 | 13 w | 4.8% | 6.7 |
| `results.md` | 45.3 | 12 w | 8.3% | 10.8 |
| *target* | *≥ 35* | *≤ 20 w* | *≤ 12%* | *≤ 12* |

Higher Flesch is easier; academic prose usually scores 15–30. A formula cannot
prove that anyone understood anything. It only shows that the mechanics are not in
the reader's way. The tool skips quotations, because shortening one would misquote
it.

## Rebuilding the artefacts

```bash
python3 fig/make_figs.py                       # figures -> fig/*.pdf
pdflatex paper.tex && pdflatex paper.tex       # -> paper.pdf (3 pages, A4)
chromium --headless --no-pdf-header-footer \
  --print-to-pdf=LI.pdf LI.html                # -> LI.pdf (5 pages, 1080x1350)
```

Binary extraction:

```bash
BIN=~/.local/share/claude/versions/<version>
strings -n 20 "$BIN" > strings.txt
grep -n "Please analyze this codebase and create a CLAUDE.md" strings.txt
```

Minified symbol names differ between builds, so grep for prompt text, not
identifiers.

## Limits

- **The evidence is six unrepeated 2026 preprints**, most too small for the
  effects they report. None is journal-published; none has been rebutted.
- **Two of the six were found late**, by luck, months after they went online.
  Assume this version is incomplete in the same way.
- **We ran no experiment of our own.** The cost tables are calculations, and the
  corpus measurement is descriptive.
- **Recency.** Claude Code shipped several versions during the week we wrote this.

## Related

[`../AgentsMdSurvey`](../AgentsMdSurvey) surveys the agent instruction files that
exist across a directory of repositories. That project asks *what people write*;
this one asks *whether it helps*.
