# Resume Notes — SWE-bench Lite evaluation

**Stopped:** 2026-08-07, 19:0x, deliberately (`SIGTERM` to the harness), at 146/300
instances. Not a crash. Nothing is corrupted; no cleanup is pending.

## How to resume

The harness has no resume flag — it re-runs whatever is in the predictions file.
`remaining_instances.json` holds the 154 instance IDs that were never attempted,
so filter the predictions down to those and run only them:

```bash
cd llm_swebench_benchmark

python3 - <<'EOF'
import json
remaining = set(json.load(open("remaining_instances.json")))
preds = [p for p in json.load(open("predictions_repaired.json"))
         if p["instance_id"] in remaining]
json.dump(preds, open("predictions_remaining.json", "w"), indent=2)
print(len(preds), "instances to run")
EOF

nohup python3 -m swebench.harness.run_evaluation \
    --dataset_name SWE-bench/SWE-bench_Lite \
    --predictions_path "$PWD/predictions_remaining.json" \
    --max_workers 4 \
    --run_id qwen36-repaired-20260807 \
    --timeout 600 > eval_repaired_part2.log 2>&1 &
```

Reusing the same `--run_id` writes into the same log tree, so the two halves
merge and `analyze_results.py` reads them as one run.

Then summarise the whole thing:

```bash
python analyze_results.py --run logs/run_evaluation/qwen36-repaired-20260807 \
    --baseline logs/run_evaluation/qwen36-agentic-20260807-reboot
```

## State at the stop

| | Run 1 (baseline) | Run 2 (repaired, partial) |
|---|---|---|
| Instances attempted | 299 | 146 |
| Patch apply failures | 213 (71%) | 75 (51%) |
| Graded (reached tests) | 82 | 61 |
| Resolved | 17 | 15 |

**Do not read a score off run 2 yet.** It is 49% complete and the instances run
so far are alphabetical (astropy → django → matplotlib), not a representative
sample. `15/61` is not comparable to run 1's `17/300`.

The one figure that *is* meaningful so far: the repair cut patch-apply failures
from **71% → 51%**, so substantially more patches now reach the test stage.

## Environment notes for next session

- **Docker needs kernel 7.1.6-1-MANJARO** (has the `veth` module). Kernel
  7.1.4 lacks it and Docker bridge networking fails outright. Check with
  `uname -r` before starting.
- **Root filesystem is tight.** `/` is 98G and separate from `/home`; it was at
  87% with 13G free after cleanup. The harness builds a ~2-3GB image per
  instance and deletes it after grading, so free space oscillates by several GB
  during a run — a momentary dip toward 0G is normal and self-correcting, not a
  leak. Only a `no space left on device` line inside
  `logs/run_evaluation/<run_id>/*/*/run_instance.log` indicates a real problem.
- `docker image prune` reclaims nothing here; the harness already removes its
  own images. Orphans only survive if a run is killed mid-instance — clear them
  with `docker rm -f $(docker ps -aq --filter name=sweb.eval)` and
  `docker rmi -f $(docker images -q 'swebench/sweb.eval*')`.

## Where the remaining failures come from

Sampled 60 previously-failing instances after repair: 12 now apply, 48 do not.
The 48 are genuine model errors, not pipeline defects:

| Reason | Count |
|---|---|
| Removes lines that appear nowhere in the target file (hallucinated) | 30 |
| Context partially hallucinated | 5 |
| Lines exist but context does not match | 8 |
| Target file does not exist at the base commit | 4 |
| Pure-insert hunk misplaced | 1 |

These are deliberately left unrepaired — forcing them to apply would
manufacture a score rather than measure one. See README.md for the full
root-cause analysis and prevention notes.
