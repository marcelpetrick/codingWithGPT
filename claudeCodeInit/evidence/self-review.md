# Self-review

Critical re-reading of the review's own claims, looking for places where it
overstates its evidence. Round 1 is the original pass; the round-5 entry was added
on 2026-09-20 after new evidence falsified an inference.

## Corrections applied (round 1)

| # | Problem | Fix |
|---|---|---|
| 1 | Claimed "**3 independent controlled studies agree**" that CLAUDE.md does not raise task success. **Only two measured success.** S1 (Gloaguen) and S2 (Khatri) measured correctness. S3 (Lulla) explicitly did *not* gate on correctness — its own abstract claims only "comparable task completion behavior". S4 (McMillan) measured *instruction adherence*, which is a different construct from task success. | Downgraded to "Medium-high — two studies measured success directly and agree; a third reports comparable completion without gating on correctness." |
| 2 | Asserted Anthropic "**is A/B testing**" a replacement `/init`. What was actually observed is a prompt gated behind `CLAUDE_CODE_NEW_INIT` and `tengu_slate_harbor_experiment`. That a flag named "experiment" exists does not prove a live A/B test is running. | Reworded to "has built, and gated behind an experiment flag". |
| 3 | Same overstatement repeated in the recommendation section ("Three controlled studies say…"). | Reworded to "the two studies that measured correctness directly". |

## Correction applied (round 5, 2026-09-20)

| # | Problem | Fix |
|---|---|---|
| 4 | The review argued that because **every published point estimate sits inside the ±9 pp per-instance flip rate**, the effect "has not been measured". The premise is still true; **the inference was not.** A per-instance flip rate bounds what a *single run* establishes about a single instance — it is not a minimum detectable effect, and averaging over repeated trials shrinks the standard error of the mean. Shepard & Albrecht resolve a **+7.5 pp** difference at *p*<0.001 over four trials, from *inside* the band. Reading the floor as a blanket disqualifier was the same species of error the round-1 corrections caught: a real number pushed past what it supports. | Reframed throughout: the floor disqualifies **single-run point estimates**, not the practice. Whitepaper §4 states the distinction explicitly, §7 gives the positive result its own section, and figure 1 was rebuilt to group effects **by design** (single-run vs repeated-trial) rather than by study, because that is the split that decides which numbers are measurements. |

*Worth noting how this was caught: not by re-reading our own argument, but by
finding a paper that contradicted it. Three rounds of search had missed
[arXiv:2606.20512](https://arxiv.org/abs/2606.20512) for three months. The
self-review process found the round-1 errors; it did **not** find this one.*

## Verified by recomputation

The claimed **8.1× cache discount, independent of file size**, was recomputed from
first principles rather than trusted:

```
ratio = base x T / (cache_write + cache_read x (T-1))
      = 2.00 x 50 / (2.50 + 0.20 x 49)
      = 100 / 12.30
      = 8.130
```

N cancels out of the ratio entirely, so the discount genuinely is independent of
CLAUDE.md size. Numerically confirmed at N = 500 / 2,000 / 10,000: ratio 8.130 in
all three cases. **Note this is conditional on the pricing inputs, which round 2
is verifying independently.**

## Weaknesses acknowledged but not "fixed" (they are real limits, not errors)

- **The discovery-cost table (§7.1) is modelled, not measured.** No published study
  isolates "tokens spent on repo orientation with no context file". The assumptions
  are listed so the figure can be recomputed, but it should not be quoted as an
  empirical result.
- **Local token counts use a bytes/4 heuristic**, not a real tokenizer (`tiktoken`
  is not installed on this machine, and it would be the wrong tokenizer for Claude
  anyway). Fine for order-of-magnitude, not for precision.
- **The long-context literature (§6.1) is cited for mechanism, not for indictment.**
  NoLiMa's 32K degradation and Chroma's context-rot curves do not condemn a
  150-line CLAUDE.md. §6.2 (instruction-count decay) is the section that actually
  bites at realistic sizes, and the dossier says so.
- **Every grade-A study is a 2026 preprint or workshop paper.** None is
  journal-published or independently replicated. The whole evidence base is one
  cite-chase away from changing.

## Presentation problems to fix in the whitepaper

The dossier is thorough but dense. For the whitepaper the user asked for
"crisp and easy to understand":

- Lead with the answer, not the method.
- One idea per section; collapse §4.2 and §4.3 into a single "why the studies
  disagree" argument.
- Replace prose hedging with an explicit confidence column.
- Cut the harness-by-harness table to its one conclusion (everyone ships the
  feature, nobody measures it).
- Keep exactly two numbers in the TL;DR. More than that and nothing is remembered.
