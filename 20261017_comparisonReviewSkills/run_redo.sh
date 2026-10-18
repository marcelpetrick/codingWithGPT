#!/usr/bin/env bash
# Re-run the two hr sessions that the usage limit killed on 2026-10-17, one after the other.
HERE=$(cd "$(dirname "$0")" && pwd)
"$HERE/run_review.sh" hrsectionx CR 2 > "$HERE/runs/log_hrsectionx_CR_2.txt" 2>&1
"$HERE/run_review.sh" hrsectionx RB 1 > "$HERE/runs/log_hrsectionx_RB_1.txt" 2>&1
echo ALLDONE
