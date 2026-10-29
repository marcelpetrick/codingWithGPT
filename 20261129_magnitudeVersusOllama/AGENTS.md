# AGENTS.md: magnitudeVersusOllama

This project measures if Magnitude (https://github.com/magnitudedev/magnitude) is faster than Ollama
for the same model on the same hardware. The root `../AGENTS.md` applies. This file adds the
project rules. Where they differ, this file wins.

## Living document

- `PLAN.md` is the one living document. Update it after every step.
- `PLAN.md` holds the verdict, the decision rule, the plan, the status table and "Resume here".

## Measurement rules

- The decision rule in `PLAN.md` is fixed. Do not change it after the first result exists.
  If a change is necessary, add a new dated rule and keep the old one visible.
- Measure on the client side, through the OpenAI-compatible streaming API of each engine.
  Record the counters of each engine too, but do not use them for the verdict.
- Run one engine at a time. Before each arm, unload all models of the other engine and check the
  free VRAM with `nvidia-smi`.
- Use the same prompts, the same output length, the same sampler (greedy, `temperature=0`) and the
  same thinking setting for both engines.
- Record per row: engine, engine version, model tag, quantization, drafter on/off, context, GPU,
  driver, date, and the git commit of this project.
- A row with an error, an empty answer or a timeout is a failed row. It is never a speed result.
- Label each A/B arm (for example `ollama-mtp-off`). Arms never pool.

## Code rules

- Python 3, standard library first. Scripts in `scripts/`, tests in `tests/`.
- `./localPipeline.sh` must pass before every commit (format, lint, type check, tests, coverage ≥ 95%).
- Every script has a docstring with purpose, usage and exit codes.
- Results go to `results/*.jsonl` (append only). The report is generated from them, never edited by hand.
- License: GPLv3. Put the SPDX header `# SPDX-License-Identifier: GPL-3.0-or-later` in each source file.
- No Docker in this project. The engines need the GPU of the host.

## Shared resources

- The box `192.168.100.67` is shared. Do not install Magnitude there without the owner's approval.
- Do not change the Ollama install on this laptop. Use `keep_alive: 0` to unload models.
