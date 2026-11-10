#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Drive a host-tool run: one fresh `codex exec` session per generation.
# Usage: codex-chain.sh RUN_DIR
# Env: MAX_REFUSALS (3), CALL_TIMEOUT (600 s), COMMIT_CHECKPOINTS (1), REFUSAL_PAUSE (60 s),
#      CODEX_IMAGES (~/.codex/generated_images), CHAIN_README (project README.md)
# Exit: 0 target reached, 2 refusal limit, 3 failure (the request stays pending for review).
set -euo pipefail
run_dir=$(realpath "${1:?RUN_DIR is required}")
here=$(dirname "$(realpath "$0")")
project=$(realpath "$here/../..")
host=(node "$here/host.mjs")
max_refusals=${MAX_REFUSALS:-3}
call_timeout=${CALL_TIMEOUT:-600}
images=${CODEX_IMAGES:-$HOME/.codex/generated_images}
readme=${CHAIN_README:-$project/README.md}
refusal_pause=${REFUSAL_PAUSE:-60}
prompt=$(sed -n 's/^> //p' "$here/../SKILL.md" | head -n 1)
[[ -n $prompt ]] || { echo "No fixed prompt found in SKILL.md" >&2; exit 3; }

say() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*"; }
field() { node -e 'const s=JSON.parse(process.argv[1]);console.log(s[process.argv[2]])' "$1" "$2"; }

publish() {
  "${host[@]}" readme --run-dir "$run_dir" --readme "$readme" > /dev/null
  [[ ${COMMIT_CHECKPOINTS:-1} == 1 ]] || return 0
  git -C "$project" add -- "$run_dir" "$readme"
  git -C "$project" commit -q -m "$1" -- "$run_dir" "$readme" || true
  say "committed: $1"
}

say "start: run $run_dir, refusal pause ${refusal_pause}s, max refusals $max_refusals"
while :; do
  status=$("${host[@]}" status --run-dir "$run_dir")
  completed=$(field "$status" completed); target=$(field "$status" target)
  if [[ $(field "$status" pending) == true ]]; then say "STOP: a request is pending; reconcile it first"; exit 3; fi
  if (( completed >= target )); then publish "docs: complete $completed generations of the Wirth chain"; say "DONE: $completed / $target"; exit 0; fi
  refusals=$(field "$status" refusalsForNext)
  if (( refusals >= max_refusals )); then
    publish "docs: stop the Wirth chain after $refusals refusals at generation $((completed + 1))"
    say "STOP: $refusals refusals for generation $((completed + 1))"; exit 2
  fi

  input=$("${host[@]}" next --run-dir "$run_dir")
  n=$((completed + 1))
  work=$(mktemp -d -t recreate101.XXXXXX)
  cp -- "$input" "$work/input.png"
  say "gen $n: start (input $(basename "$input"), refusals so far $refusals)"
  rc=0
  timeout "$call_timeout" codex exec --skip-git-repo-check --ephemeral -s read-only -C "$work" --json -i "$work/input.png" -- \
    "Use the image generation tool exactly once. Use the attached image as the only input image. Use this prompt verbatim: $prompt Do not run shell commands. Do not edit files." \
    < /dev/null > "$work/events.jsonl" 2> "$work/stderr.txt" || rc=$?
  thread=$(node -e 'for(const l of require("fs").readFileSync(process.argv[1],"utf8").split("\n")){try{const e=JSON.parse(l);if(e.thread_id){console.log(e.thread_id);break;}}catch{}}' "$work/events.jsonl")
  usage=$(node -e 'let u="";for(const l of require("fs").readFileSync(process.argv[1],"utf8").split("\n")){try{const e=JSON.parse(l);if(e.type==="turn.completed")u=JSON.stringify(e.usage);}catch{}}console.log(u)' "$work/events.jsonl")
  mapfile -t pngs < <( [[ -n $thread && -d $images/$thread ]] && find "$images/$thread" -maxdepth 1 -name '*.png' | sort )
  extra=()
  [[ -n $thread ]] && extra+=(--thread-id "$thread")
  [[ -n $usage ]] && extra+=(--agent-usage "$usage")

  if (( rc == 0 && ${#pngs[@]} == 1 )); then
    "${host[@]}" accept --run-dir "$run_dir" --image "${pngs[0]}" "${extra[@]}" > /dev/null
    say "gen $n: accepted (thread $thread, usage $usage)"
    rm -rf -- "$work"
    if (( n % 10 == 0 )); then publish "docs: checkpoint $n generations of the Wirth chain"; fi
  elif (( ${#pngs[@]} == 0 )) && grep -q 'moderation_blocked' "$work/stderr.txt" "$work/events.jsonl"; then
    request=$(grep -ohE 'request ID [0-9a-f-]{36}' "$work/stderr.txt" "$work/events.jsonl" | head -n 1 | cut -d' ' -f3 || true)
    [[ -n $request ]] && extra+=(--request-id "$request")
    "${host[@]}" refuse --run-dir "$run_dir" --outcome moderation_blocked "${extra[@]}" > /dev/null
    say "gen $n: REFUSED (thread $thread, request ${request:-unknown}); evidence kept in $work"
    sleep "$refusal_pause"
  else
    say "STOP gen $n: rc=$rc, ${#pngs[@]} images, thread '$thread'; evidence in $work; request left pending"
    exit 3
  fi
done
