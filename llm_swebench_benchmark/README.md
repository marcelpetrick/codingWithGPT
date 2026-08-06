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
    --dataset_name princeton-nlp/SWE-bench_Lite \
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
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path subset_preds.json \
    --max_workers 1 \
    --run_id smoke-test
```

## File Structure

```
llm_swebench_benchmark/
├── inference.py              # Inference script
├── requirements.txt          # Dependencies
├── swebench_benchmark_plan.md  # Full plan
└── README.md                 # This file
```

## Estimated Wall Time

~4–11 hours for all 300 instances (~1–3 min per instance at ~131 tok/s).
