#!/usr/bin/env bash
# Launch the 8 hr-doccontrol runs in parallel, wait for all.
HERE=$(cd "$(dirname "$0")" && pwd)
for f in hrsafety hrsectionx; do for a in RB CR; do for r in 1 2; do
  "$HERE/run_review.sh" $f $a $r > "$HERE/runs/log_${f}_${a}_${r}.txt" 2>&1 &
done; done; done
wait
echo ALLDONE
