# Annotation rubric for the manual quality check (REQ-LLM-4)

Use this rubric to fill the `human_*` columns of the sample file. The categories and their meanings are the
same as in the dashboard (Methodology → Definitions).

## Procedure

1. Write the sample: `uv run mrreview sample --n 60 --out out/annotation_sample.csv`.
2. Open each `url` in GitLab. Read the whole thread and the code change after it.
3. Fill `human_intent`, `human_actionability`, `human_validity`, `human_primary_response` and `human_outcome`.
   Use the exact category names. Leave a cell empty if you cannot decide.
4. Do not look at the `model_*` columns before you decide. Hide them in your spreadsheet.
5. Write a note in `human_note` for every disagreement you are sure about.
6. Compute the figures: `uv run mrreview agreement out/annotation_sample.csv`.
7. Record the result, the model, the prompt version and the date in `WORKLOG.md`.

You can see that the check is complete when every row has at least `human_outcome` filled.

## Rules for hard cases

- A promise ("will fix") is `promised` in the text, so the outcome is `open` unless the code shows the change.
- A declined nit is `optional_declined`, with or without a reason.
- `declined_unjustified` needs a rejection with no technical reason at all.
- An answered question with no change needed is `justified_no_change`.
- If two issues are in one comment, judge the first one and write the second in `human_note`.

## Reading the figures

- Report agreement and Cohen's kappa per dimension, with n.
- Kappa below 0.6 means the dimension is not reliable enough for person-level reading.
- Look at the top confusions. They show which rule in the prompt needs work.
- Cover all projects, languages and outcomes, including ambiguous and negative cases.
