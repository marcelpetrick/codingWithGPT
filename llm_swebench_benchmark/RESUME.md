# Run Notes — SWE-bench Lite evaluation

**Status: COMPLETE.** Run 2 (`qwen36-repaired-20260807`) finished on 2026-08-07.
All 300 dataset instances are accounted for; nothing is pending. This file is
kept for the operational notes below, which are the parts worth remembering next
time.

Final result: **24/300 = 8.0% resolved**, up from 5.7% before the patch repair.
See [README.md](README.md) for the full analysis and the per-repo breakdown.

## Reproducing the analysis

```bash
python analyze_results.py --run logs/run_evaluation/qwen36-repaired-20260807 \
    --baseline logs/run_evaluation/qwen36-agentic-20260807-reboot
```

## How the run was actually executed

Not in one shot. The sequence, because it matters for anyone re-running it:

1. 146 instances at `--max_workers 4`, stopped deliberately with `SIGTERM`.
2. The remaining 153 (of 154; one has an empty patch) at `--max_workers 4`,
   41 minutes.
3. 10 instances that step 1's `SIGTERM` had left with no verdict at all —
   neither a `report.json` nor a `Patch Apply Failed` marker. Found by
   reconciling `graded + apply-failed` against the instance-directory count.
4. Of those 10, the last 4 had to drop to `--max_workers 1` after matplotlib
   images filled the root partition.

All four phases reuse `--run_id qwen36-repaired-20260807`, so they merge into a
single log tree and `analyze_results.py` reads them as one run.

## Environment notes

- **Docker needs kernel 7.1.6-1-MANJARO** (has the `veth` module). Kernel
  7.1.4 lacks it and Docker bridge networking fails outright. Check `uname -r`
  before starting.
- **Root filesystem is the binding constraint.** `/` is 98 GB and separate from
  `/home`. Budget roughly `max_workers x 8 GB` of free space: matplotlib env
  images are ~7.7 GB each, about 3x django or sympy. Two workers on matplotlib
  exhausted 18 GB of free space and drove `/` to 0 bytes.
- **Free space oscillating by several GB is normal** — the harness removes each
  image right after grading. Only two things indicate a real problem: an
  absolute floor (under ~3 GB), or a `no space left on device` line inside
  `logs/run_evaluation/<run_id>/*/*/run_instance.log`. This run finished with
  **0** such lines.
- **`docker system df` under-reports.** After a full prune showing 0 images,
  ~23 GB on `/` was still unreadable to a non-root user — orphaned `overlay2`
  layer data from `SIGKILL`ed builds that Docker's own accounting does not see
  and `docker system prune` does not reclaim. Inspect with
  `sudo du -sh /var/lib/docker/* | sort -rh`.
- Clearing orphans after a killed run:
  `docker rm -f $(docker ps -aq --filter name=sweb.eval)` and
  `docker rmi -f $(docker images -q 'swebench/sweb.eval*')`. Note the
  `swebench/` filter — a bare `docker system prune -a` will also delete
  unrelated project images.

## Where the remaining failures come from

179 of 299 patches (60%) still never reached a test. Sampling 60 of them after
repair: 12 now apply, 48 do not. The 48 are genuine model errors, not pipeline
defects:

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
