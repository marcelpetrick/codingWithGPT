#!/usr/bin/env bash
# s15-refresh.sh -- which model is best for agentic Qt/C++, Python, GitLab and long summaries.
# Arm rb1102, Ollama 0.40.x. Plan and reasons: ROUND_2026-11-02.md. The rule is in refresh-compare.py.
#
# Order: residency check, T5 x8, summary probe (speed, cache, context), then round-robin
# sessions: Python ledger, Qt/C++, GitLab. A time cut therefore leaves balanced data.
# A void run is retried once and is never counted. The job stops when the server is
# unreachable, a read is empty, a foreign model stays, or a version changes.
# It deletes nothing on the box. Idempotent: a re-run skips everything already valid.
#
# Usage: ./s15-refresh.sh --dry-run    print the plan, touch nothing
#        ./s15-refresh.sh --prepare    pull and bake the new models (no time limit), then stop
#        setsid nohup systemd-inhibit --what=sleep:idle ./s15-refresh.sh >/dev/null 2>&1 & disown
#        ARM=smoke MODELS_OVERRIDE="tag" RUNS=1 ./s15-refresh.sh    one small pass
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
HOST="192.168.100.67"; BASE="http://$HOST:11434"; ARM="${ARM:-rb1102}"
LOG="$HERE/results/s15-$ARM.log"; T5DONE="$HERE/results/refresh-$ARM.t5done"
# tag|source|extra parameters (the vendor sampler)
NEW=(
  "minicpm-v-4.7-35b:q5km-ctx256k-agentic|hf.co/openbmb/MiniCPM-V-4.7-35B-A3B-gguf:Q5_K_M|\"temperature\":0.7,\"top_p\":0.95,\"top_k\":100,\"min_p\":0"
  "qwen3.8-35b-distill:q5km-ctx256k-agentic|hf.co/empero-ai/Qwen3.8-35B-A3B-Distill-GGUF:Q5_K_M|\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20,\"min_p\":0"
)
MODELS=(
  qwen3.6:35b-a3b-q4_K_M-agentic            # the control, required by the harness rules
  kat-coder-v2.5:q5km-ctx256k-agentic
  occamy-1.0:q5km-ctx256k-agentic
  minicpm-v-4.7-35b:q5km-ctx256k-agentic
  qwen3.8-35b-distill:q5km-ctx256k-agentic
  tiel-coder:35b-q5-ctx256k-agentic
  gemma4:26b-a4b-it-q4_K_M-ctx256k-agentic
  ornith-1.5-35b:q5km-ctx256k-agentic
)
[ -n "${MODELS_OVERRIDE:-}" ] && read -r -a MODELS <<<"$MODELS_OVERRIDE"
TASKS=(hard qtcpp gitlab)
RUNS="${RUNS:-3}"
SESSION_TIMEOUT=600   # the slowest Python median is 156 s; a longer session is a failed session
BUDGET_S=6480         # 108 min: last session start; with the timeout, the end is before 2 h
PULL_TIMEOUT=3600

if [ "${1:-}" = "--dry-run" ]; then
  echo "arm $ARM, $RUNS rounds, tasks ${TASKS[*]}, session timeout ${SESSION_TIMEOUT}s, no new session after ${BUDGET_S}s"
  printf '  %s\n' "${MODELS[@]}"; exit 0
fi

export NO_PROXY="$HOST,${NO_PROXY:-}" no_proxy="$HOST,${no_proxy:-}" DISABLE_AUTOUPDATER=1
say () { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }
api () { curl -s -m "$1" "$BASE$2" ${3:+-d "$3"}; }
server_version () { api 10 /api/version | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null; }
client_version () { claude --version 2>/dev/null | head -1; }
valid () { python3 ./refresh-compare.py --arm "$ARM" --valid "$@"; }
stop () { say "STOPPED: $1"; finish "$2"; }
finish () {
  trap - INT TERM
  python3 ./refresh-compare.py --arm "$ARM" 2>&1 | tee -a "$LOG"
  [ "$ARM" = smoke ] || python3 ./make-dashboard.py >>"$LOG" 2>&1 || say "dashboard failed"
  timeout 5 notify-send "s15 refresh: exit $1" "Result: results/refresh-$ARM.md" 2>/dev/null || true
  say "S15-REFRESH-END exit $1"; exit "$1"
}
trap 'stop "signal" 143' INT TERM

V0="$(server_version)"; C0="$(client_version)"
[ -n "$V0" ] || { say "STOPPED: server unreachable, check the USB ethernet adapter"; exit 3; }
say "START arm $ARM, Ollama $V0, $C0, laptop load: $(cut -d' ' -f1-3 /proc/loadavg)"
PREV=""   # the one tag this job loaded; only that tag counts as ours under --mine
go_idle () {
  local a=(); [ -n "$PREV" ] && a=(--mine "$PREV")
  ./idle.sh --host "$HOST" "${a[@]}" >>"$LOG" 2>&1 || stop "box is busy with a foreign model" 2
  PREV=""
}
assert_state () {
  local v; v="$(server_version)"
  [ -n "$v" ] || stop "server unreachable" 3
  [ "$v" = "$V0" ] || stop "server moved $V0 -> $v" 4
  [ "$(client_version)" = "$C0" ] || stop "client version changed" 4
}
exists () { api 10 /api/show "{\"name\":\"$1\"}" | grep -q '"modelfile"'; }

prepare () {
  local e tag src par fam rp
  for e in "${NEW[@]}"; do
    IFS='|' read -r tag src par <<<"$e"
    exists "$tag" && { say "  $tag exists"; continue; }
    say "pull $src (limit ${PULL_TIMEOUT}s; a re-run resumes it)"
    api "$PULL_TIMEOUT" /api/pull "{\"name\":\"$src\",\"stream\":false}" | grep -q '"status":"success"' \
      || { say "  pull not finished: $tag is left out"; continue; }
    fam="$(./s9-parse.py family "$BASE" "$src")"; rp=""
    [ "$fam" = "qwen35moe" ] && rp='"renderer":"qwen3.5","parser":"qwen3.5",'
    say "  family ${fam:-?}; bake $tag"
    api 600 /api/create "{\"model\":\"$tag\",\"from\":\"$src\",\"parameters\":{\"num_ctx\":262144,\"presence_penalty\":0,$par},${rp}\"stream\":false}" \
      | grep -q '"status":"success"' || say "  bake failed: $tag is left out"
  done
}
if [ "${1:-}" = "--prepare" ]; then prepare; say "PREPARE-DONE"; exit 0; fi

# Returns 0 fully resident, 1 did not load or spilled. An empty read stops the job.
residency () {
  local m="$1" r reply
  go_idle
  reply="$(api 900 /api/generate "{\"model\":\"$m\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1}}")"
  PREV="$m"
  r="$(api 10 /api/ps | python3 -c '
import sys,json
try: ms=json.load(sys.stdin)["models"]
except Exception: print("READ-FAILED"); raise SystemExit
x=[(i["size"],i.get("size_vram",0)) for i in ms if i["name"]==sys.argv[1]]
print("%d %d"%x[0] if x else "ABSENT")' "$m")"
  case "$r" in
    READ-FAILED|"") stop "empty read from /api/ps" 3 ;;
    ABSENT) say "  $m did not load: $(printf '%s' "$reply" | head -c 300)"; return 1 ;;
  esac
  set -- $r
  [ "$1" = "$2" ] && { say "  $m resident: $(( $1 / 1000000000 )) GB, 100% GPU"; return 0; }
  say "  $m spilled: size $1, size_vram $2"; return 1
}

say "A. new models and residency check"
prepare
ACTIVE=()
for M in "${MODELS[@]}"; do
  exists "$M" || { say "  $M is not on the box: left out"; continue; }
  assert_state
  if residency "$M"; then ACTIVE+=("$M"); else say "  $M is left out of this run; nothing deleted"; fi
done
[ "${#ACTIVE[@]}" -gt 0 ] || stop "no model is usable" 3

say "B. T5 x8"
touch "$T5DONE"
for M in "${ACTIVE[@]}"; do
  grep -qxF "$M" "$T5DONE" && { say "  $M: T5 done in this arm"; continue; }
  assert_state; [ "$PREV" = "$M" ] || go_idle
  python3 ./gate-rerun.py --host "$BASE" --n 8 --gate T5 "$M" 2>&1 | tail -2 | tee -a "$LOG"
  [ "${PIPESTATUS[0]}" -eq 0 ] || stop "T5 transport error on $M" 3
  PREV="$M"; echo "$M" >>"$T5DONE"
done

say "C. summary, speed, cache, context"
for M in "${ACTIVE[@]}"; do
  python3 ./refresh-compare.py --arm "$ARM" --summary-done "$M" && { say "  $M: done in this arm"; continue; }
  assert_state; [ "$PREV" = "$M" ] || go_idle
  python3 ./summary-probe.py --host "$BASE" --arm "$ARM" "$M" 2>&1 | tee -a "$LOG"
  [ "${PIPESTATUS[0]}" -eq 0 ] || stop "summary transport error on $M" 3
  PREV="$M"
done

say "D. sessions, $RUNS rounds, round-robin"
LAST_ROUND=0; DROPPED=" "
one_session () {  # <tag> <task> <run>; returns 0 if the run is valid
  CC_ARM=$ARM ./cc-session.sh --host "$HOST" --fixture "$2" --runs 1 --first-run "$3" \
    --timeout "$SESSION_TIMEOUT" --thinking on "$1" 2>&1 | grep -E '^ +(PASS|FAIL|CHEAT)' | tee -a "$LOG"
  PREV="$1"
  valid "$1" "$2" "$3" >>"$LOG" 2>&1
}
for R in $(seq 1 "$RUNS"); do
  T0=$SECONDS
  [ $(( SECONDS + LAST_ROUND )) -gt "$BUDGET_S" ] && stop "time budget: round $R does not fit" 0
  N=${#ACTIVE[@]}
  for i in $(seq 0 $(( N - 1 ))); do
    M="${ACTIVE[$(( (i + R - 1) % N ))]}"   # rotate the start, so no model always follows the same one
    case "$DROPPED" in *" $M "*) continue ;; esac
    for TASK in "${TASKS[@]}"; do
      valid "$M" "$TASK" "$R" >/dev/null 2>&1 && continue
      [ "$SECONDS" -gt "$BUDGET_S" ] && stop "time budget in round $R" 0
      assert_state; [ "$PREV" = "$M" ] || go_idle
      say "round $R: $M $TASK"
      one_session "$M" "$TASK" "$R" && continue
      say "  void, one retry: $(valid "$M" "$TASK" "$R")"
      assert_state; [ "$PREV" = "$M" ] || go_idle
      one_session "$M" "$TASK" "$R" && continue
      say "  void twice: $M is left out of the remaining rounds"; DROPPED="$DROPPED$M "; break
    done
  done
  LAST_ROUND=$(( SECONDS - T0 ))
  [ "$ARM" = smoke ] || python3 ./make-dashboard.py >>"$LOG" 2>&1 || say "dashboard failed"
done
go_idle
say "S15-REFRESH-DONE"
finish 0
