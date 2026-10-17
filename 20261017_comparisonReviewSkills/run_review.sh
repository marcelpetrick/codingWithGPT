#!/usr/bin/env bash
# Run one review skill on one fixture in a fresh clone of AlliumAssault and keep the transcript.
# Usage: run_review.sh <fixture: gource|factions> <arm: RB|CR> <rep: 1|2>
# Idempotent: a run whose transcript already ends in a result event is skipped.
set -euo pipefail

FIXTURE=$1 ARM=$2 REP=$3
SRC=$HOME/repos/AlliumAssault
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-/tmp/claude-1000/reviewcmp}
OUT=$HERE/runs/${FIXTURE}_${ARM}_${REP}
mkdir -p "$OUT" "$WORK"

if [[ -s $OUT/transcript.jsonl ]] && tail -n1 "$OUT/transcript.jsonl" | grep -q '"type":"result"'; then
  echo "skip $OUT (done)"; exit 0
fi

case $FIXTURE in
  gource)   BASE=master;    HEAD_REF=mpe/gource ;;
  factions) BASE=99fbe2e^;  HEAD_REF=99fbe2e ;;
  *) echo "unknown fixture $FIXTURE" >&2; exit 2 ;;
esac
case $ARM in
  RB) PROMPT=/reviewBranch ;;
  CR) PROMPT=/code-review ;;
  *) echo "unknown arm $ARM" >&2; exit 2 ;;
esac

CLONE=$WORK/${FIXTURE}_${ARM}_${REP}
rm -rf "$CLONE"
git clone -q "$SRC" "$CLONE"
git -C "$CLONE" remote remove origin
BASE_SHA=$(git -C "$SRC" rev-parse "$BASE")
HEAD_SHA=$(git -C "$SRC" rev-parse "$HEAD_REF")
git -C "$CLONE" checkout -q -B "review/$FIXTURE" "$HEAD_SHA"
git -C "$CLONE" branch -f master "$BASE_SHA"
for b in $(git -C "$CLONE" for-each-ref --format='%(refname:short)' refs/heads); do
  [[ $b == master || $b == review/$FIXTURE ]] || git -C "$CLONE" branch -q -D "$b"
done
ln -s "$SRC/node_modules" "$CLONE/node_modules"

{
  echo "fixture=$FIXTURE arm=$ARM rep=$REP base=$BASE_SHA head=$HEAD_SHA"
  echo "claude=$(claude --version) start=$(date -Is)"
} > "$OUT/meta.txt"

cd "$CLONE"
start=$(date +%s)
claude -p "$PROMPT" --model claude-opus-5-5 --output-format stream-json --verbose \
  --dangerously-skip-permissions --no-session-persistence \
  > "$OUT/transcript.jsonl.part" 2> "$OUT/stderr.txt" || echo "exit=$?" >> "$OUT/meta.txt"
end=$(date +%s)
mv "$OUT/transcript.jsonl.part" "$OUT/transcript.jsonl"
echo "wall_s=$((end-start)) end=$(date -Is)" >> "$OUT/meta.txt"
git -C "$CLONE" status --porcelain > "$OUT/worktree_after.txt"
