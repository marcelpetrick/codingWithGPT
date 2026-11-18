#!/usr/bin/env bash
# v6-q8.sh -- P7, the quant-drift arm: the merged pi model at Q8_0 (the card's precision), 65536 window.
# Waits for v6-run.sh to end, then: residency, T5 x8, and the three session tasks x3 with the same
# cc-session.sh calls as s15 (arm pi1118q8). No summary task: its 150k prompt does not fit 65536.
# Idempotent: a valid run is skipped. Deletes nothing. A foreign model is waited out (idle.sh).
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; V4="$HERE/../ollamaClaudeCode_v4_tielCoder"
HOST=192.168.100.67; BASE="http://$HOST:11434"; ARM=pi1118q8; M=qwen3.8-pi:27b-q8-ctx64k-nothink
LOG="$V4/results/s15-$ARM.log"
export NO_PROXY="$HOST,${NO_PROXY:-}" no_proxy="$HOST,${no_proxy:-}" DISABLE_AUTOUPDATER=1
say () { printf '[%s] %s\n' "$(date +%T)" "$*" | tee -a "$LOG"; }
cd "$V4"
until grep -q 'V6-RUN-END' results/s15-pi1118.log 2>/dev/null; do sleep 60; done
curl -sf -m 10 "$BASE/api/show" -d "{\"name\":\"$M\"}" | grep -q modelfile || { say "STOPPED: $M is not on the box"; exit 3; }
./idle.sh --host "$HOST" >>"$LOG" 2>&1 || { say "STOPPED: box busy"; exit 2; }
curl -s -m 900 "$BASE/api/generate" -d "{\"model\":\"$M\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1}}" >/dev/null
r="$(curl -s -m 10 "$BASE/api/ps" | python3 -c 'import sys,json;m=[x for x in json.load(sys.stdin)["models"] if x["name"]==sys.argv[1]];print("%d %d"%(m[0]["size"],m[0]["size_vram"]) if m else "ABSENT")' "$M")"
set -- $r; [ "${1:-}" = "${2:-x}" ] || { say "STOPPED: $M not 100% GPU: $r"; exit 3; }
say "START $M resident $(( $1 / 1000000000 )) GB, 100% GPU"
grep -qxF "$M" "results/refresh-$ARM.t5done" 2>/dev/null || {
  python3 ./gate-rerun.py --host "$BASE" --n 8 --gate T5 "$M" 2>&1 | tail -2 | tee -a "$LOG"; echo "$M" >>"results/refresh-$ARM.t5done"; }
for R in 1 2 3; do for TASK in hard qtcpp gitlab; do
  python3 ./refresh-compare.py --arm "$ARM" --valid "$M" "$TASK" "$R" >/dev/null 2>&1 && continue
  for try in 1 2; do
    say "round $R: $TASK (try $try)"
    CC_ARM=$ARM ./cc-session.sh --host "$HOST" --fixture "$TASK" --runs 1 --first-run "$R" \
      --timeout 600 --thinking on "$M" 2>&1 | grep -E '^ +(PASS|FAIL|CHEAT)' | tee -a "$LOG"
    python3 ./refresh-compare.py --arm "$ARM" --valid "$M" "$TASK" "$R" >>"$LOG" 2>&1 && break
  done
done; done
curl -s "$BASE/api/generate" -d "{\"model\":\"$M\",\"keep_alive\":0}" >/dev/null
say "V6-Q8-END"
timeout 5 notify-send "v6 q8 arm ended" "$LOG" 2>/dev/null || true
