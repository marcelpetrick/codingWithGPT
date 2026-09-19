# Self-review of round 1

Critical re-reading of `results.md` by the lead session before round 2, looking
for places where the dossier overstates its own evidence.

## Corrections applied

| # | Problem | Fix |
|---|---|---|
| 1 | Claimed "**3 independent controlled studies agree**" that CLAUDE.md does not raise task success. **Only two measured success.** S1 (Gloaguen) and S2 (Khatri) measured correctness. S3 (Lulla) explicitly did *not* gate on correctness — its own abstract claims only "comparable task completion behavior". S4 (McMillan) measured *instruction adherence*, which is a different construct from task success. | Downgraded to "Medium-high — two studies measured success directly and agree; a third reports comparable completion without gating on correctness." |
| 2 | Asserted Anthropic "**is A/B testing**" a replacement `/init`. What was actually observed is a prompt gated behind `CLAUDE_CODE_NEW_INIT` and `tengu_slate_harbor_experiment`. That a flag named "experiment" exists does not prove a live A/B test is running. | Reworded to "has built, and gated behind an experiment flag". |
| 3 | Same overstatement repeated in the recommendation section ("Three controlled studies say…"). | Reworded to "the two studies that measured correctness directly". |

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
