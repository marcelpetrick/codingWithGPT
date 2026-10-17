#!/usr/bin/env bash
# Launch all 8 runs in parallel (independent clones, read-only reviews), wait for all.
HERE=$(cd "$(dirname "$0")" && pwd)
for f in gource factions; do for a in RB CR; do for r in 1 2; do
  "$HERE/run_review.sh" $f $a $r > "$HERE/runs/log_${f}_${a}_${r}.txt" 2>&1 &
done; done; done
wait
echo ALLDONE
