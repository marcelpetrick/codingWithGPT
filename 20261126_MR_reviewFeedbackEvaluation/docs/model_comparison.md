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
