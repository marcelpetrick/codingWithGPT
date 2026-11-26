# Comparison with published code review studies

State: 2026-11-26, real run over all 76 active projects (5,078 findings). Aggregates only, no names.
Purpose: put the figures of this tool next to published baselines. A match supports the classification; a difference is a question, not a verdict.

## Source

Czerwonka, Greiler, Tilford: "Code Reviews Do Not Find Bugs. How the Current Code Review Best Practice Slows Us Down."
ICSE 2015, Software Engineering in Practice, Microsoft. [PDF](https://microsoft.com/en-us/research/wp-content/uploads/2015/05/PID3556473.pdf).
It summarises the Microsoft study of Bosu, Greiler and Bird (MSR 2015). All baseline figures below come from that PDF, read on 2026-11-26.

## Results

| Question | Microsoft baseline | This run | Reading |
|---|---|---|---|
| Share of review comments that point at a possible defect | about 15% | 943 / 5,078 = **18.6%** (intent `defect`) | Close. The codebook counts possible defects, as the baseline does. |
| Share of comments about long-term maintainability | at least 50% | 2,567 / 5,078 = **50.6%** (intent `style`, `design`, `maintainability`) | Match. |
| Usefulness grows with the reviewer's prior exposure: 33% at first contact, about 67% at the third | strong learning curve | 60.4% (first comment on a file), 58.9%, 55.0%, 64.3% (3 or more earlier comments) | No learning curve. See limit 2. |
| Usefulness falls in reviews with 20 or more files | lower for 20+ files | 47.6% (1–4 files), 52.9% (5–9), 59.9% (10–19), **65.3% (20+)** | Opposite trend. See limit 3. |
| Median time to all sign-offs | about 24 hours (Rigby and Bird 2013) | not compared | This tool times findings, not sign-offs. |

"Useful" here is a proxy: an actionable finding (change request or optional suggestion) from a human that has a stated change,
or an open outcome with a direct code change (the commented lines changed later). Microsoft asked the change authors.

## Limits

1. The proxies differ. Microsoft used the author's judgement; this tool uses the text outcome and the code. Compare trends, not levels.
2. Prior exposure counts only comments in the 12-month window, per reviewer, project and file. Earlier history is not visible, so many "first" comments are not first contacts.
3. The size trend is not a chance effect of the 2-line rule: the placebo rate does not grow with MR size (next section). The cause is open.
4. Intent comes from the LLM. The real-data annotation sample (docs/annotation_rubric.md) is still open, so the intent shares are not checked by a human.

## Placebo check of the direct-evidence rule

Question: how often does a change within 2 lines of a comment happen by chance?
Method: for 1,595 diff comments whose file changed later, apply the same rule to a line shifted by k lines up and down.
Command: `uv run python scripts/placebo_check.py out/real/mrreview.sqlite3`.

| Line tested | Hit rate |
|---|---|
| The commented line | **91.7%** |
| Shifted by 10 lines | 33.4% |
| Shifted by 25 lines | 21.6% |
| Shifted by 50 lines | 13.6% |
| Shifted by 100 lines | 7.8% |

| MR size (files) | Commented line | Shifted by 50 |
|---|---|---|
| 1–4 | 92.2% | 11.5% |
| 5–9 | 87.6% | 17.3% |
| 10–19 | 95.9% | 12.1% |
| 20+ | 94.0% | 14.4% |

Result: a direct hit is about 7 times more frequent at the commented line than 50 lines away. The rule measures the review, not chance.
About 8–14% of all "direct" hits can still be coincidence (large rewrites of a file). Read "direct" as strong evidence, not proof.
