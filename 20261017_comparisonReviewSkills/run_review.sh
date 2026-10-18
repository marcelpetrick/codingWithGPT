#!/usr/bin/env bash
# Run one review skill on one fixture in a fresh clone of its source repo and keep the transcript.
# Usage: run_review.sh <fixture: gource|factions|hrsafety|hrsectionx> <arm: RB|CR> <rep: 1|2>
# Idempotent: a run whose transcript already ends in a result event is skipped.
set -euo pipefail

FIXTURE=$1 ARM=$2 REP=$3
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-/tmp/claude-1000/reviewcmp}
OUT=$HERE/runs/${FIXTURE}_${ARM}_${REP}
mkdir -p "$OUT" "$WORK"

# A usage-limit stop also ends in a result event; that is a dead session and must be re-run.
if [[ -s $OUT/transcript.jsonl ]] && tail -n1 "$OUT/transcript.jsonl" | grep -q '"type":"result"' &&
   ! tail -n1 "$OUT/transcript.jsonl" | grep -q 'hit your session limit'; then
  echo "skip $OUT (done)"; exit 0
fi

# BASE_BRANCH is the integration branch name the repo really uses, so each skill meets its usual setup.
case $FIXTURE in
  gource)     SRC=$HOME/repos/AlliumAssault; BASE_BRANCH=master; BASE=master;   HEAD_REF=mpe/gource ;;
  factions)   SRC=$HOME/repos/AlliumAssault; BASE_BRANCH=master; BASE=99fbe2e^; HEAD_REF=99fbe2e ;;
  hrsafety)   SRC=$HOME/repos/hr-doccontrol; BASE_BRANCH=main;   BASE=9dacfb1^; HEAD_REF=9dacfb1 ;;
  hrsectionx) SRC=$HOME/repos/hr-doccontrol; BASE_BRANCH=main;   BASE=b026e3e;  HEAD_REF=2dd0b80 ;;
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
git -C "$CLONE" branch -f "$BASE_BRANCH" "$BASE_SHA"
for b in $(git -C "$CLONE" for-each-ref --format='%(refname:short)' refs/heads); do
  [[ $b == "$BASE_BRANCH" || $b == review/$FIXTURE ]] || git -C "$CLONE" branch -q -D "$b"
done
for d in node_modules .venv; do
  if [[ -e $SRC/$d ]]; then ln -s "$SRC/$d" "$CLONE/$d"; fi
done

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
