# SWE-bench Lite Benchmark — Local Model Evaluation

Benchmark a local Ollama model against [SWE-bench Lite](https://github.com/princeton-nlp/SWE-bench) using the same approach as the existing `claude-ol2` setup.

## Model

| | |
|---|---|
| Model | `qwen3.6:35b-a3b-q4_K_M-agentic` |
| Backend | Ollama on `192.168.100.67:11434` (dual-GPU, ~36 GB VRAM) |
| Architecture | 36B MoE / 3B active per token |
| Context | 262144 tokens (fully in VRAM) |
| Sampling | temperature 0, presence_penalty 0 (baked in) |
| Throughput | ~131 tok/s (measured) |

## Setup

```bash
pip install -r requirements.txt
```

Verify prerequisites:

```bash
# Model server
curl -s http://192.168.100.67:11434/api/tags | python3 -m json.tool | head -5

# Docker
docker info | head -3
```

## Run Inference

Generate patches for all 300 SWE-bench Lite instances:

```bash
python inference.py
```

Options:

```bash
python inference.py --output my_preds.json          # custom output path
python inference.py --start_from 150                # resume at instance 150
python inference.py --instances subset.json         # run a subset
python inference.py --dry_run                       # print prompts, skip model calls
python inference.py --tmp_dir /mnt/data/swebench    # custom temp dir
```

Predictions are written incrementally to the output JSON (resumable).

## Run Evaluation

After inference completes:

```bash
python -m swebench.harness.run_evaluation \
    --dataset_name SWE-bench/SWE-bench_Lite \
    --predictions_path predictions.json \
    --max_workers 4 \
    --run_id qwen36-agentic-$(date +%Y%m%d) \
    --timeout 600
```

Results are written to a `results/` directory.

## Smoke Test (3 instances)

```bash
# Pick 3 instances from different repos
python3 -c "
from datasets import load_dataset
ds = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')
# one each from flask, sympy, scikit-learn
targets = [i for i in ds if i['repo'] in ('flask/flask', 'sympy/sympy', 'scikit-learn/scikit-learn')]
import json
json.dump([dict(i) for i in targets[:3]], open('subset.json','w'), indent=2)
"
python inference.py --instances subset.json --output subset_preds.json
python -m swebench.harness.run_evaluation \
    --dataset_name SWE-bench/SWE-bench_Lite \
    --predictions_path subset_preds.json \
    --max_workers 1 \
    --run_id smoke-test
```

## File Structure

```
llm_swebench_benchmark/
├── inference.py              # Inference script
├── repair_patches.py         # Fix malformed diffs before evaluation
├── analyze_results.py        # Summarise a run, diff against a baseline
├── requirements.txt          # Dependencies
├── swebench_benchmark_plan.md  # Full plan
└── README.md                 # This file
```

## Repairing Patches Before Evaluation

The harness rejects a diff outright if its envelope is malformed, before it ever
runs a test. `repair_patches.py` fixes the envelope without touching the model's
edits (it asserts the `+`/`-` lines stay byte-identical):

```bash
python repair_patches.py --input predictions.json --output predictions_repaired.json

# optional: also remap file paths that resolve to a unique real path
# (e.g. flask/app.py -> src/flask/app.py). Needs local clones named owner__repo.
python repair_patches.py --input predictions.json --output predictions_repaired.json \
    --repo-cache /path/to/clones
```

Then evaluate `predictions_repaired.json` and summarise:

```bash
python analyze_results.py --run logs/run_evaluation/<run_id> \
    --baseline logs/run_evaluation/<older_run_id>
```

## Results (2026-08-07)

> **Attribution — two different models are involved here, do not conflate them.**
>
> - **Model under test** (generated all 300 candidate patches, and is what the
>   resolution rate measures): `qwen3.6:35b-a3b-q4_K_M-agentic`, the local
>   36B MoE / 3B active model served by Ollama.
> - **Model that did the engineering** (diagnosed the failures, wrote
>   `repair_patches.py` and `analyze_results.py`, fixed `extract_patch()`, and
>   wrote this analysis): **Claude Opus 5**, via Claude Code.
>
> The benchmark scores below describe the MoE model only. The repair tooling and
> the corrected analysis are Opus 5's work and are **not** part of what is being
> benchmarked — the harness fixes changed how many patches reached the test
> stage, not what the MoE model wrote.

### Inference

| Metric | Value |
|--------|-------|
| Instances completed | 300/300 (100%) |
| Patch extraction rate | 299/300 (99.7%) |
| Valid hunk headers | 294/299 (98.3%) |
| Wall time | ~2.5 hours |

### Evaluation Run 1 — reboot run (2026-08-07)

| Metric | Value |
|--------|-------|
| Docker networking | Resolved — rebooted into kernel 7.1.6-1-MANJARO (veth module available) |
| Instances submitted | 300/300 |
| Reached the test stage | 82/300 (27.3%) |
| Never tested (patch apply failed) | 213/300 |
| Never tested (Docker image missing) | 4/300 |
| Resolved | 17/300 (5.7%) |
| Empty patches | 1/300 |

> **Correction.** An earlier revision of this file attributed the 217 untested
> instances to Docker image build failures and concluded the benchmark harness
> was at fault. That was wrong, and it was not verified before being written
> down — it was inferred from two log tails. Counting the failure reason in all
> 217 logs gives 213 patch-apply failures and only 4 missing images. The cause
> was this repo's own patch extraction, not the harness.
>
> The same revision reported the score as `17/82 = 20.7%`. That divides by the
> subset of instances that happened to survive the pipeline, which inflates the
> number. Over the full dataset it is `17/300 = 5.7%`.

### Evaluation Run 2 — repaired patches (2026-08-07, COMPLETE)

Re-evaluated `predictions_repaired.json` against the same harness. All 300
instances accounted for: 299 attempted (1 has an empty patch), 0 unaccounted,
0 disk-related failures.

| Metric | Run 1 (baseline) | Run 2 (repaired) |
|---|---|---|
| Instances attempted | 299 | 299 |
| Patch apply failures | 213 (71%) | 179 (60%) |
| Graded (reached tests) | 82 (27%) | 120 (40%) |
| **Resolved** | **17/300 = 5.7%** | **24/300 = 8.0%** |
| Resolved / applied | 20.7% | 20.0% |

**7 newly resolved, 0 regressions:** `django__django-11039`,
`django__django-11099`, `django__django-13658`, `django__django-15061`,
`mwaskom__seaborn-3010`, `pytest-dev__pytest-5227`, `sympy__sympy-17655`.

**qwen3.6:35b-a3b-q4_K_M-agentic resolves 8.0% of SWE-bench Lite.**

Note that `resolved / applied` is essentially unchanged (20.7% → 20.0%). This is
the honest reading of the repair work: fixing the diff envelope let 38 more
patches reach the test stage, and they converted at the same rate as the ones
that already applied. The repair recovered measurement that was being lost — it
did not make the model better, and it did not flatter the result.

### Per-repo breakdown (denominator = full dataset, not just graded)

| Repo | Dataset | Graded | Resolved | Rate |
|---|---:|---:|---:|---:|
| django/django | 114 | 51 | 15 | 13.2% |
| sympy/sympy | 77 | 27 | 7 | 9.1% |
| mwaskom/seaborn | 4 | 3 | 1 | 25.0% |
| pytest-dev/pytest | 17 | 8 | 1 | 5.9% |
| astropy/astropy | 6 | 2 | 0 | 0% |
| matplotlib/matplotlib | 23 | 12 | 0 | 0% |
| pallets/flask | 3 | 1 | 0 | 0% |
| psf/requests | 6 | 1 | 0 | 0% |
| pydata/xarray | 5 | 2 | 0 | 0% |
| pylint-dev/pylint | 6 | 1 | 0 | 0% |
| scikit-learn/scikit-learn | 23 | 8 | 0 | 0% |
| sphinx-doc/sphinx | 16 | 4 | 0 | 0% |
| **TOTAL** | **300** | **120** | **24** | **8.0%** |

The distribution matters more than the headline. **22 of 24 solutions come from
two repos** (django and sympy), which together are 64% of the dataset. On the
other ten repos the model scores 2/109. django and sympy issues in SWE-bench
Lite tend to be localised — a wrong comparison, a missing guard — while
scikit-learn, sphinx and matplotlib issues more often require understanding
state that spans several files. The model is not uniformly weak at 8%; it is
reasonable at small localised fixes and near zero at anything requiring wider
context.

The apply rate remains the bigger constraint: **60% of patches still never reach
a test.** That residue is dominated by the model hallucinating code that does
not exist at the base commit. It is a model limitation and is deliberately not
papered over — see below.

### Root Cause — three mechanical defects in the extracted diffs

None of these involve the model's reasoning. Each one causes `patch`/`git apply`
to reject a file before any test executes:

| Defect | Affected | Effect |
|---|---|---|
| `extract_patch()` called `.strip()`, removing the trailing newline | 299/299 | `patch unexpectedly ends in middle of line` |
| Markdown fence remnants and trailing prose left in the patch body | 32 | `malformed patch` |
| Hunk header line counts disagreeing with the hunk body | 245 | `malformed patch` |

The trailing-newline bug alone was enough to break every single patch: a unified
diff must end in a newline.

### The Fix

`repair_patches.py` rebuilds the diff envelope only — hunk counts are recomputed
from the body (they are redundant metadata), fences and prose are stripped, the
trailing newline is restored, and file paths are optionally remapped when they
resolve to exactly one real path. **The `+`/`-` edit lines are asserted
byte-identical: 0 of 300 changed.** `extract_patch()` is fixed at the source so
future runs do not reproduce the bug.

Measured on 60 previously-failing instances, using the harness's own command
chain (`git apply` → `git apply --reject` → `patch --fuzz=5`): **0/60 → 12/60
now apply.**

### What is genuinely the model's fault

The other 48 of those 60 were left alone deliberately — they are real model
errors, and fuzzing them into place would manufacture a score rather than
measure one:

| Reason | Count |
|---|---|
| Removes lines that appear nowhere in the target file (hallucinated) | 30 |
| Context partially hallucinated | 5 |
| Lines exist but context does not match | 8 |
| Target file does not exist at the base commit | 4 |
| Pure-insert hunk misplaced | 1 |

Example: for `sympy__sympy-15609` the model patched `_print_SparseMatrixElement`,
a function that does not exist in that file at that commit.

### How to prevent this class of failure

1. **Validate patches at generation time, not evaluation time.** A patch that
   cannot be parsed is a bug in the harness around the model. Run the structural
   check (`repair_patches.py`) immediately after extraction and fail loudly.
2. **Never `.strip()` a unified diff.** The trailing newline is load-bearing.
   `.lstrip()` or `.rstrip() + "\n"` are safe; `.strip()` is not.
3. **Verify against the real tree before evaluating.** Cheaply confirm each
   `--- a/<path>` exists at the base commit via `git ls-tree`; a missing path is
   knowable in milliseconds instead of after a multi-minute Docker build.
4. **Count failure reasons before diagnosing.** The wrong conclusion above came
   from reading two logs instead of classifying all 217. One `grep -c` per
   signature would have prevented it.
5. **Report `resolved / dataset_size`.** Dividing by the surviving subset silently
   inflates the score, and the inflation grows as the pipeline gets buggier —
   the metric looks best exactly when it is least trustworthy.
6. **Separate pipeline failures from model failures in the report.** "Did not
   apply" and "applied but did not fix the issue" are different findings and
   should never share a denominator.
7. **Size `--max_workers` against the largest repo image, not the average.**
   matplotlib env images are ~7.7 GB, roughly 3x django or sympy. Four workers
   is comfortable for most of the dataset and fatal on the matplotlib block:
   this run filled a 98 GB root partition to 0 bytes twice before being
   dropped to `--max_workers 1` for those instances. Budget
   `workers x 8 GB` of free space, or run the matplotlib/seaborn block
   separately.
8. **Reconcile the instance count before reporting.** `graded + apply-failed`
   must equal the number of instance directories. This run had 10 instances
   with neither a report nor a failure marker — killed mid-flight by an earlier
   `SIGTERM` — which would have silently vanished from the denominator. They
   were re-run to close the gap.
9. **Distinguish "free space oscillating" from "free space at zero".** The
   harness deletes each image after grading, so several GB of movement is
   normal. Alert on an absolute floor (e.g. under 3 GB) and on real
   `no space left on device` lines, not on the oscillation itself.

## Estimated Wall Time

~4–11 hours for all 300 instances (~1–3 min per instance at ~131 tok/s).
