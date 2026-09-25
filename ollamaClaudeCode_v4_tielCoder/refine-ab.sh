#!/usr/bin/env bash
# refine-ab.sh -- the post-round refinements (ROUND_2026-09-24.md, "Refinements
# to test after the round"), each as an A/B on the pick, one variable at a time.
#
#   R1 caching   CLAUDE_CODE_TOTAL_TOKENS_REMINDER unset vs "off" (ollama#18431)
#                ledger x3 per arm; the number is the UNCACHED share of input
#   R3 penalty   presence_penalty 0 vs 1.5 on the same weights (ollama#14493 says
#                the Go engine ignores it; v4 measured -41..52% generation)
#   R5 overflow  the new pick (KAT) past its window: refuses or silently halves?
#                decides whether claude-ol-kat's 200k cap can move up
#
# R2 (Tiel re-upload) was settled by digest: our blob IS the 09-10 v22.5.0 file.
# R4 (KV cache q8_0) needs OLLAMA_KV_CACHE_TYPE on the server -- no API sets it,
#    and there is no SSH to .67 -- so it is the owner's step, not this script's.
#
# Waits for the box like s10-one.sh does. Idempotent per arm via cc-session's
# own transcripts. Usage: ./refine-ab.sh [r1|r3|r5|all]
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"
HOST="192.168.100.67"; BASE="http://$HOST:11434"
TAG="kat-coder-v2.5:q5km-ctx256k-agentic"   # the pick since 2026-09-25
LOG="$HERE/results/refine-ab.log"
WHAT="${1:-all}"
say () { printf '\n\033[1m[%s] %s\033[0m\n' "$(date +%H:%M)" "$*" | tee -a "$LOG"; }

say "waiting for the box"
while pgrep -f '^bash \./(GO_official_tb|s9-candidates|s10-one|run-all)\.sh' >/dev/null 2>&1; do sleep 60; done
curl -s -m 10 "$BASE/api/version" >/dev/null || { say "server unreachable -- stopping"; exit 3; }

uncached () {  # <arm> -> per-run "fresh_in cache_read share% wall" from the transcripts
  python3 - "$1" <<'PY'
import glob, json, sys
arm = sys.argv[1]
pat = f"results/cc/kat-coder-v2.5_q5km-ctx256k-agentic-hard-thinkon-{arm}-r*.jsonl"
for f in sorted(glob.glob(pat)):
    for line in open(f):
        i = line.find("{")
        if i < 0:
            continue
        try:
            d = json.loads(line[i:])
        except ValueError:
            continue
        if d.get("type") == "result":
            u = d.get("usage") or {}
            fresh, cached = u.get("input_tokens", 0), u.get("cache_read_input_tokens", 0)
            tot = fresh + cached
            print(f"  {f.rsplit('-', 1)[1]:>8}  fresh {fresh:>7}  cached {cached:>8}  "
                  f"uncached {100 * fresh / tot if tot else 0:5.1f}%  wall {d.get('duration_ms', 0) / 1000:.0f}s  "
                  f"turns {d.get('num_turns')}")
PY
}

if [ "$WHAT" = r1 ] || [ "$WHAT" = all ]; then
  say "R1 caching: reminder default vs off, ledger x3 each"
  CC_ARM=remindon ./cc-session.sh --host "$HOST" --fixture hard --runs 3 --thinking on "$TAG" 2>&1 | grep -E 'PASS|FAIL' | tee -a "$LOG"
  CC_ARM=remindoff CLAUDE_CODE_TOTAL_TOKENS_REMINDER=off \
    ./cc-session.sh --host "$HOST" --fixture hard --runs 3 --thinking on "$TAG" 2>&1 | grep -E 'PASS|FAIL' | tee -a "$LOG"
  { echo "  -- reminder default"; uncached remindon; echo "  -- reminder off"; uncached remindoff; } | tee -a "$LOG"
fi

if [ "$WHAT" = r3 ] || [ "$WHAT" = all ]; then
  say "R3 presence_penalty: 0 (the pick) vs 1.5, same weights, tokrate"
  PP="kat-coder-v2.5:q5km-ctx256k-agentic-pp15"
  curl -s -m 120 "$BASE/api/create" -d "{\"model\":\"$PP\",\"from\":\"$TAG\",\"parameters\":{\"presence_penalty\":1.5},\"stream\":false}" >/dev/null
  ./tokrate.sh --host "$HOST" "$TAG" 2>&1 | tail -3 | tee -a "$LOG"
  ./tokrate.sh --host "$HOST" "$PP" 2>&1 | tail -3 | tee -a "$LOG"
  curl -s -X DELETE "$BASE/api/delete" -d "{\"model\":\"$PP\"}" >/dev/null
fi
if [ "$WHAT" = r5 ] || [ "$WHAT" = all ]; then
  say "R5 overflow behaviour of the pick"
  python3 ./overflow-probe.py --host "$BASE" "$TAG" 2>&1 | tail -8 | tee -a "$LOG"
fi
say "REFINE-AB-DONE"
