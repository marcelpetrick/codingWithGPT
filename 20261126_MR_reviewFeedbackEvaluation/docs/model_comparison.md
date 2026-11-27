# Model comparison for review-thread classification (D-029)

State: 2026-11-27. 180 real findings with blind Claude Opus labels (120 + 60), prompt p5 for every model, temperature 0,
thinking off, one model at a time on the Ollama box, box idle before each run. Agreement with Opus in %, kappa in brackets.
The rule was fixed before the runs (D-029): mean of outcome and response at least +5 points, no dimension down more than 3,
at least 99% valid replies, at most 3 times the time per thread of qwen3.6.

| Model | Outcome | Response | Validity | Intent | Actionability | Tone kappa (n=60) | Valid | s/thread | Rule |
|---|---|---|---|---|---|---|---|---|---|
| qwen3.6 35B-A3B (in use) | 54.4 (0.45) | 48.9 (0.39) | 68.3 | 66.5 | 73.7 | 0.30 | 177/178 | 2.8 | baseline |
| **qwen3.8-pi 27B** | **63.9 (0.56)** | **58.3 (0.49)** | 73.3 | 66.5 | 74.9 | 0.36 | 178/178 | 10.6 | quality passes (+9.5 / +9.4); **speed fails: 3.8×** |
| gemma4 26B-A4B | 61.1 (0.53) | 50.6 (0.40) | 65.6 | 62.6 | 74.3 | **0.46** | 174/178 | 4.4 | fails: mean +4.2, intent −3.9, 97.8% valid |
| KAT-Coder-V2.5 | 57.2 (0.48) | 47.2 (0.38) | 63.3 | 60.9 | 71.5 | 0.29 | 177/178 | 3.0 | fails: mean +0.6, intent −5.6 |
| occamy-1.0 | 51.7 (0.42) | 50.6 (0.42) | 58.3 | 61.5 | 72.6 | 0.25 | 176/178 | 3.1 | fails: mean −0.5, validity −10.0 |

- The qwen3.6 row is a fresh run in the same harness (median 2.8 s). An earlier run of the same model gave the same outcome figure (54.4), so the harness is stable.
- Coding benchmarks did not predict this task: KAT and occamy lead the coding round (ollamaClaudeCode v4/v6) but trail here.
- qwen3.8-pi is the only candidate that improves the judgement of outcome and response. A full rerun takes about 16.5 hours
  (5,600 threads × 10.6 s); after that, daily new threads take minutes. The speed limit was set by the agent, so the switch is the owner's decision.
- Ornith-1.5 was not measured: the register records looping and broken tool calls, and it trails on the coding round.

## Decision and quality evaluation after the switch (D-034)

Owner decision 2026-11-27: switch to qwen3.8-pi 27B (`qwen3.8-pi:27b-q4km-ctx200k-nothink`) and accept the 3.8× time.
Threads without a valid result are classified first, then all others again. The qwen3.6 results stay in
`out/real/mrreview_qwen36_p5.sqlite3` (local only) as the fallback and for the comparison below.

The 180 items above chose the model, so their figures favour the winner. The rules below were fixed before any qwen3.8-pi production result existed.

| Check | Data | Rule | Action if it fails |
|---|---|---|---|
| Q1 run health | the full rerun | at least 99% valid replies; no outage booked as a result | stop, analyse the harness first |
| Q2 production equals harness | stored results on the 180 items | outcome and response within ±3 points of the harness figures (63.9, 58.3) | find the difference before the data is used |
| Q3 fresh holdout | 90 new findings, stratified by the qwen3.6 outcome, blind Opus labels, never used to choose the model | mean of outcome and response: qwen3.8-pi minus qwen3.6 on the same items ≥ 0 confirms; between −3 and 0 is a tie (switch kept); below −3 reopens D-034 | reopen D-034, restore the snapshot on the owner's word |
| Q4 drift | all threads with both results | agreement qwen3.6 vs qwen3.8-pi per dimension; change of the outcome shares and of the person-level tone and response columns | a shift above 10 points is explained with examples before a figure is published |

The holdout is stratified, so its figures are not population shares; rare outcomes are over-represented on purpose.
Baselines, measured before any qwen3.8-pi production result (scorer: stored findings, matched to the labelled finding by summary overlap):

| Set | Model | Outcome | Response | Validity | Intent | Actionability | Tone |
|---|---|---|---|---|---|---|---|
| fresh holdout, n=90 | qwen3.6 (snapshot) | 54.4 (0.48) | 42.2 (0.32) | 65.6 | 68.9 | 82.2 | 80.0 (0.61) |
| first 180, production | qwen3.6 (snapshot) | 56.1 (0.47) | 47.2 (0.38) | 69.4 | 65.4 | 74.9 | not labelled for all |

The qwen3.6 production figures on the 180 items are within 2 points of its harness figures (54.4, 48.9), so the Q2 scorer agrees with the harness.
Q3 confirms the switch when the qwen3.8-pi mean on the fresh holdout is at least 48.3. Results are added here when the rerun ends.
