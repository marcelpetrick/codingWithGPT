# Kolibri Q3 experiment

[![Kolibri Q3 checks](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/kolibri-q3.yml/badge.svg)](https://github.com/marcelpetrick/codingWithGPT/actions/workflows/kolibri-q3.yml)

This experiment tests Kolibri-1 Q3_K_S on the shared Ollama server. See [the run record](KOLIBRI_Q3_RUN.md) for the plan, evidence, status and resume commands. See [the vision](vision.md) for the goal.

## Run checks

Install Python 3, `coverage` 7.14.0 and ShellCheck. Run `./localPipeline.sh`. This checks shell syntax, ShellCheck, Python compilation and unit tests. It requires at least 95% statement coverage across `residency.py` and `refine.py`. The tests do not contact the server.

## Scripts

- `pull-model.sh` checks that the server is idle and downloads the selected model. It uses `results/pull.lock` to prevent duplicate local pulls.
- `after-pull.sh` waits on the pull lock and starts the residency probe. Run it only after starting the pull.
- `after-residency.sh` waits for the ladder and starts `refine.py`.
- `refine.py` searches the remaining context interval in steps of 1,024 tokens.
- `residency.py` checks the server, tests context sizes and writes `results/residency.jsonl`. It resumes matching results and refuses to unload another model.
- `localPipeline.sh` runs the local checks.
- `test_refine.py` checks the context search.
- `test_residency.py` tests the probe with mocked responses and a local HTTP server.

The scripts use `192.168.100.67:11434`. Do not run them while another user occupies the server. Check `results/pull.log` and `results/chain.log` after a detached run. The probe stops on errors or the first GPU spill. A successful allocation does not establish retrieval or tool-use quality.

The experiment code is GPL-3.0-or-later. The model and upstream runtimes have separate licenses. See [LICENSE](LICENSE) and the model publisher's license.
