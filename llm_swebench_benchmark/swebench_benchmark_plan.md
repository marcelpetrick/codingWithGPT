# Plan: SWE-bench Lite Local Benchmark

## Context

Benchmark the local model (`qwen3.6:35b-a3b-q4_K_M-agentic` on server `192.168.100.67`) against SWE-bench Lite to measure real-world coding capability. Same model, same harness approach (Ollama + Anthropic-compatible API).

## Prerequisites (already satisfied)

- Model loaded on `192.168.100.67:11434` (33.1 GB VRAM, verified resident)
- Docker running (active containers confirmed)
- `openai` and `datasets` Python packages installed
- Model verified: produces clean unified diffs, responds to Anthropic `/v1/messages` format

## File Structure

```
llm_swebench_benchmark/
├── inference.py      # Main inference script
├── requirements.txt  # swebench, datasets, openai
└── README.md         # Setup + run instructions
```

## Step 1: `requirements.txt`

```
swebench>=2.5
datasets
openai
```

## Step 2: `inference.py` — single self-contained script

### Key components

**Dataset loading** (lines ~1-30):
```python
from datasets import load_dataset
ds = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')
# 300 instances, fields: repo, instance_id, base_commit, patch, test_patch,
# problem_statement, hints_text, created_at, version, FAIL_TO_PASS, PASS_TO_PASS, environment_setup_commit
```

**Per-instance loop** (lines ~30-150):
For each instance:
1. Clone `repo` at `base_commit` into a temp dir
2. Build prompt: issue (`problem_statement` + `hints_text`) + repo tree + full content of files in `FAIL_TO_PASS` (these are the files that need changes)
3. Send to Ollama via `openai` client at `http://192.168.100.67:11434/v1`:
   ```python
   client = OpenAI(base_url="http://192.168.100.67:11434/v1", api_key="ollama")
   response = client.chat.completions.create(
       model="qwen3.6:35b-a3b-q4_K_M-agentic",
       messages=[{"role": "user", "content": prompt}],
       max_tokens=8192,
   )
   ```
4. Extract unified diff from response text (try markdown fence first, then bare `--- a/`)
5. Write `{instance_id, model_patch, model_name_or_path}` to output JSON incrementally

**CLI args**: `--instances` (subset JSON), `--output` (predictions path), `--start_from` (resume index), `--tmp_dir` (temp repo location).

**Prompt format** — gives the model:
- The issue description (problem_statement + hints_text)
- The repo structure (git ls-files)
- Full content of files mentioned in FAIL_TO_PASS (the files that need changes)
- Instruction: "Generate a unified diff to fix this issue. Output ONLY the diff."

**Resumability**: incremental JSON writes, `--start_from` to resume, retry with exponential backoff (3 retries).

**Context budget**: ~150K tokens max (well within the 262K window).

## Step 3: Evaluation

```bash
python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path predictions.json \
    --max_workers 4 \
    --run_id qwen36-agentic-$(date +%Y%m%d) \
    --timeout 600
```

Docker containers spin up per instance, apply the patch, run tests, report pass/fail. Start with `--max_workers 2`, increase if RAM allows.

## Step 4: Verification

1. **Smoke test**: run first 3 instances, verify predictions JSON has valid non-empty patches
2. **Smoke eval**: evaluate the 3 predictions, verify Docker containers run and results JSON produced
3. **Full run**: all 300 instances

## Estimated Wall Time

~4-11 hours total (model at ~131 tok/s, ~1-3 min per instance).
