# Classification quality on real data (REQ-LLM-4)

State: 2026-11-27. Owner input D-023: Claude Opus annotates instead of a person. Aggregates only, no names.

## Method

1. `mrreview sample --n 120` drew 120 findings, stratified over projects and outcomes, from the run over all 76 active projects.
2. Six Opus agents labelled them blind (no model columns), with the codebook and the rubric (docs/annotation_rubric.md).
   They got the same masked context as Qwen, with links and project paths also removed.
3. Opus labels the stated text outcome. The outcome column uses the same code-evidence rule as the tool (`evaluate.decide`).
4. A second Opus pass on 40 items measured the stability of the reference.
5. Decision rule, fixed before p4 and p5 ran: a new prompt replaces p2 only if text-outcome agreement rises by at least
   5 points and no other dimension drops by more than 3 points.

Note: the sample over-weights rare outcomes, so the figures are not population accuracy. Opus is a second model, not human truth.

## Results (agreement with Opus, Cohen's kappa in brackets)

| Dimension | Opus vs Opus (n=40) | Qwen p2 | p3 | p4 | **p5 (adopted)** |
|---|---|---|---|---|---|
| intent | 87.5% (0.84) | 64.7% (0.59) | 58.0% (0.51) | 58.0% (0.51) | 62.2% (0.56) |
| actionability | 84.6% (0.74) | 73.1% (0.57) | 73.1% (0.55) | 71.4% (0.54) | 77.3% (0.63) |
| validity | 87.5% (0.81) | 66.7% (0.40) | 63.3% (0.35) | 59.2% (0.29) | 69.2% (0.45) |
| primary_response | 85.0% (0.83) | 44.2% (0.35) | 45.8% (0.35) | 40.8% (0.29) | 52.5% (0.43) |
| text_outcome | 90.0% (0.88) | 51.7% (0.44) | 49.2% (0.36) | 53.3% (0.41) | 56.7% (0.48) |

- p3 and p4 added decision rules in prose. They over-corrected (answered questions became "open"). Rejected.
- All figures are in-sample: p3 to p5 were written from the confusions in the same 120 items. A fresh sample confirms p5 (next section, after the p5 rerun).
- p5 adds eleven short synthetic worked examples and drops the p2 rule that read silence on a nit as a decline.
  It meets the rule. The text-outcome gain (6 of 120 items) is within the noise of this sample size.
- Coarse classes with p2 (change / promised / no change / deferred / open): outcome 61.7% (0.50), actionability 89.9% (0.75), intent 76.5% (0.60).

## Confirmation on a fresh sample (n=60)

60 new findings (not in the first 120 threads), stratified by stated outcome, labelled blind by Opus. p2 values were saved before the rerun.

| Dimension | Qwen p2 | Qwen p5 |
|---|---|---|
| intent | 78.3% (0.74) | 75.0% (0.70) |
| actionability | 75.0% (0.52) | 76.7% (0.55) |
| validity | 65.0% (0.39) | 70.0% (0.46) |
| primary_response | 30.0% (0.22) | 45.0% (0.35) |
| text_outcome | 45.0% (0.39) | 50.0% (0.41) |

Result: the gains on response (+15.0) and outcome (+5.0) hold out of sample. Intent drops 3.3 points (2 of 60 items),
just outside the 3-point limit. Decision: keep p5, because response and outcome feed the outcome figures and intent does not.
This is a judgement call against the letter of the rule; the owner can reverse it (rerun with p2).

## Reading

- Kappa stays below 0.6 for response, validity and outcome. Do not read these per person. Project and trend level is the safe use.
- The main remaining confusion: Qwen labels a reply that reports a fix as "explanation", where Opus labels "agreement".
- Reproduce: `out/annotation/` holds the sample and the labels (local, real data, git-ignored).
