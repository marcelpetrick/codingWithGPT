# Comparison with published code review studies

State: 2026-11-27, real run over all active projects with prompt p5 (4,946 findings). Aggregates only, no names.
Purpose: put the figures of this tool next to published baselines. A match supports the classification; a difference is a question, not a verdict.

## Source

Czerwonka, Greiler, Tilford: "Code Reviews Do Not Find Bugs. How the Current Code Review Best Practice Slows Us Down."
ICSE 2015, Software Engineering in Practice, Microsoft. [PDF](https://microsoft.com/en-us/research/wp-content/uploads/2015/05/PID3556473.pdf).
It summarises the Microsoft study of Bosu, Greiler and Bird (MSR 2015). All baseline figures below come from that PDF, read on 2026-11-26.

## Results

| Question | Microsoft baseline | This run | Reading |
|---|---|---|---|
| Share of review comments that point at a possible defect | about 15% | 838 / 4,946 = **16.9%** (intent `defect`) | Close. The codebook counts possible defects, as the baseline does. |
| Share of comments about long-term maintainability | at least 50% | 2,480 / 4,946 = **50.1%** (intent `style`, `design`, `maintainability`) | Match. |
| Usefulness grows with the reviewer's prior exposure: 33% at first contact, about 67% at the third | strong learning curve | 67.4% (first comment on a file), 66.7%, 64.5%, 73.9% (3 or more earlier comments) | Weak rise only after 3 earlier comments. See limit 2. |
| Usefulness falls in reviews with 20 or more files | lower for 20+ files | 51.2% (1–4 files), 60.1% (5–9), 66.3% (10–19), **67.1% (20+)** | Opposite trend. See limit 3. |
| Median time to all sign-offs | about 24 hours (Rigby and Bird 2013) | not compared | This tool times findings, not sign-offs. |

"Useful" here is a proxy: an actionable finding (change request or optional suggestion) from a human that has a stated change,
or an open outcome with a direct code change (the commented lines changed later). Microsoft asked the change authors.

## Limits

1. The proxies differ. Microsoft used the author's judgement; this tool uses the text outcome and the code. Compare trends, not levels.
2. Prior exposure counts only comments in the 12-month window, per reviewer, project and file. Earlier history is not visible, so many "first" comments are not first contacts.
3. The size trend is not explained by chance hits alone: the placebo rate does not grow steadily with MR size (next section). The cause is open.
4. Intent comes from the LLM (prompt p5 for the figures above; the p2 run gave 18.6% and 50.6%). The Opus annotation (docs/annotation_result.md) gives intent kappa 0.56–0.59, so the shares are approximate.

## Placebo check of the direct-evidence rule

Question: how often does a change within 2 lines of a comment happen by chance?
Method: for 1,595 diff comments whose file changed later, apply the same rule to a line k lines above the comment.
Only upward shifts are used: those lines exist in the file for sure. Chance share = placebo rate / rate at the commented line.
Command: `uv run python scripts/placebo_check.py out/real/mrreview.sqlite3`.

| Line tested | Hit rate | Chance share of a direct hit |
|---|---|---|
| The commented line | **91.7%** | |
| 10 lines above | 33.4% | 0.36 |
| 25 lines above | 24.5% | 0.27 |
| 50 lines above | 17.5% | 0.19 |
| 100 lines above | 9.3% | 0.10 |

| MR size (files) | Commented line | 50 lines above |
|---|---|---|
| 1–4 | 92.2% | 13.6% |
| 5–9 | 87.6% | 24.0% |
| 10–19 | 94.7% | 17.0% |
| 20+ | 95.1% | 18.6% |

Result: a direct hit is about 5 times more frequent at the commented line than 50 lines above it.
Roughly 10–20% of the "direct" hits can be chance. Read "direct" as strong evidence, not proof.

Limit: a comment sits on a line that the MR already edits, and such lines change again more often, with or without the review.
The placebo lines share this only partly, so the chance share is a lower bound.
