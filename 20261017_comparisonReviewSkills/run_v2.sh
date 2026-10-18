#!/usr/bin/env bash
# Round 2: the reviewBranchV2 candidate, one run after the other (parallel runs hit the usage limit).
HERE=$(cd "$(dirname "$0")" && pwd)
for f in hrsafety hrsectionx factions; do for r in 1 2; do
  "$HERE/run_review.sh" $f RB2 $r > "$HERE/runs/log_${f}_RB2_${r}.txt" 2>&1
done; done
echo ALLDONE
