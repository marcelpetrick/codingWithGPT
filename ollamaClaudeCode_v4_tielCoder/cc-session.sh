#!/usr/bin/env bash
# cc-session.sh — does this model actually drive Claude Code, end to end?
#
# Runs the real CLI non-interactively against a fixture repository with real
# bugs in it, and scores the repository afterwards rather than believing the
# model's summary. v3's design, with five changes, each forced by v3's record:
#
#  1. --fixture hard. v3's one-function `stats` fixture was PASSed by 19 of 19
#     sessions, so it could not separate models on capability. `ledger` spreads
#     three bugs and a missing function over three modules, and is also scored
#     against 18 HELD-OUT tests the model never sees (fixtures/ledger-hidden):
#     a model that fixed the code to the docstrings passes them, one that only
#     chased the visible asserts does not.
#  2. --runs N. v3 was n=1 per model, and its own control moved 46 s -> 58 s
#     with no throughput change. One run is an anecdote.
#  3. The model is PRE-WARMED before the clock starts, the way every claude-ol*
#     shell function does. v3 started timing on an empty server, so every
#     session's wall clock included a 10-30 s cold load (its transcripts show
#     time-to-first-token of 23-162 s). The warm-load time is recorded
#     separately instead of hidden inside the session.
#  4. All four model slots point at the tag (v3 set only HAIKU). Subagents
#     resolve `opus`; unset, Claude Code sends `claude-opus-5` to Ollama -> 404.
#  5. Evidence for WHERE the time went: every transcript line is stamped with
#     "_t", /api/ps is sampled at 1 Hz for the whole session (a reload or an
#     eviction by someone else shows up there), and cc-analyse.py splits the
#     result into calls, tokens, thinking volume and the longest model wait.
#
# --thinking off appends "<|think_off|>" to the system prompt. How that was
# arrived at, because the obvious switches do not work (measured 2026-09-17 with
# a capture server standing in for Ollama, Claude Code 2.1.274):
#   * by default Claude Code sends thinking:{type:"adaptive"} + effort "high"
#   * MAX_THINKING_TOKENS=0 and alwaysThinkingEnabled:false only OMIT the field,
#     and Ollama treats an omitted field as "think" -- a Tiel session run that way
#     still emitted 7,614 thinking characters
#   * Claude Code never sends thinking:{type:"disabled"}, the one value Ollama honours
#   * the Sharp/froggeric template (Tiel) reads "<|think_off|>" from the system
#     message and wins even over "adaptive": 126 thinking chars -> 0
# It is a TEMPLATE switch, so it only works where the template implements it.
# think_chars in the results is the check: nonzero under "off" means ignored.
#
# Scoring, from the repository:
#   PASS   visible tests green AND source changed AND tests/ untouched
#   CHEAT  green but tests/ edited (or green with no source change)
#   FAIL   still red, or timed out
#   hidden k/N for the hard fixture, reported alongside the verdict
#
# Working trees live OUTSIDE this repository ($CC_WORKROOT, default
# /tmp/ollama-v4-cc) so a model exploring with `ls ..` cannot find the held-out
# tests or the reference solution. The transcript, a 1 Hz ps log and the final
# diff are kept under results/cc/.
#
# Usage: ./cc-session.sh [--host H] [--port P] [--timeout S] [--fixture easy|hard]
#                        [--runs N] [--thinking on|off] <model> [<model>...]
set -uo pipefail

HOST="192.168.100.67"; PORT="11434"; TMO=1800; FIXTURE="easy"; RUNS=1; THINKING="on"
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --timeout) TMO="$2"; shift 2 ;;
    --fixture) FIXTURE="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --thinking) THINKING="$2"; shift 2 ;;
    *) break ;;
  esac
done
[ $# -ge 1 ] || { echo "usage: cc-session.sh [opts] <model>..." >&2; exit 2; }
case "$FIXTURE" in easy|hard) ;; *) echo "--fixture easy|hard" >&2; exit 2 ;; esac
case "$THINKING" in on|off) ;; *) echo "--thinking on|off" >&2; exit 2 ;; esac

D="$(dirname "$(readlink -f "$0")")"
API="http://${HOST}:${PORT}"
OUT="$D/results/cc"; mkdir -p "$OUT"
TSV="$D/results/cc-session.tsv"
WORKROOT="${CC_WORKROOT:-/tmp/ollama-v4-cc}"; mkdir -p "$WORKROOT"
[ -s "$TSV" ] || printf 'date\tollama\tmodel\tfixture\tthinking\trun\tverdict\thidden\twall_s\twarm_s\tcalls\tturns\tin_tok\tout_tok\tthink_chars\tapi_s\tttft_s\tmax_gap_s\ttools\treloads\tforeign\tnote\n' > "$TSV"

command -v claude >/dev/null || { echo "no claude CLI on PATH" >&2; exit 2; }
command -v pytest >/dev/null || { echo "no pytest on PATH" >&2; exit 2; }
VERSION=$(curl -s -m 10 "$API/api/version" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null || echo "?")

make_easy() {  # v3's fixture, byte-identical, so easy-fixture numbers stay comparable
  local dir="$1"
  mkdir -p "$dir/tests"
  cat > "$dir/stats.py" <<'PY'
"""Small statistics helpers."""


def mean(values):
    if not values:
        raise ValueError("mean() requires at least one value")
    return sum(values) / len(values)


def median(values):
    if not values:
        raise ValueError("median() requires at least one value")
    ordered = sorted(values)
    return ordered[len(ordered) // 2]
PY
  cat > "$dir/tests/test_stats.py" <<'PY'
import pytest

from stats import mean, median


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    # With an even number of values the median is the mean of the two middle
    # values, not the upper one.
    assert median([1, 2, 3, 4]) == 2.5


def test_median_does_not_mutate():
    values = [3, 1, 2]
    median(values)
    assert values == [3, 1, 2]
PY
  printf '[pytest]\npythonpath = .\n' > "$dir/pytest.ini"
  printf '__pycache__/\n*.pyc\n.pytest_cache/\n' > "$dir/.gitignore"
}

make_fixture() {
  local dir="$1"
  rm -rf "$dir"; mkdir -p "$dir"
  if [ "$FIXTURE" = easy ]; then make_easy "$dir"; SRC="stats.py"
  else command cp -r "$D/fixtures/ledger/." "$dir/"; SRC="ledger"; fi
  ( cd "$dir" && git init -q && git add -A && git -c user.email=bench@local \
      -c user.name=bench commit -qm "fixture" )
}

if [ "$FIXTURE" = easy ]; then
PROMPT='The test suite in this repository is failing. Run it, find the cause, fix the
source code, and run the tests again to confirm they pass. Do not change any file
under tests/ -- the tests describe the behaviour that is wanted.'
else
PROMPT='The test suite in this repository is failing. Run it, find the causes, and fix
the source code so that it does what its docstrings specify -- the tests check only
part of that specification. Some functionality may be missing entirely. Run the tests
again to confirm they pass. Do not change any file under tests/.'
fi

ps_sampler() {  # 1 Hz /api/ps log: epoch, then name|size|size_vram|ctx|expires per model
  while :; do
    printf '%s\t%s\n' "$(date +%s)" "$(curl -s -m 2 "$API/api/ps" | python3 -c '
import sys,json
try: ms=json.load(sys.stdin).get("models",[])
except Exception: print("ERR"); raise SystemExit
print(" ".join("%s|%d|%d|%s|%s"%(m["name"],m.get("size",0),m.get("size_vram",0),m.get("context_length"),m.get("expires_at","")) for m in ms) or "-")' 2>/dev/null)"
    sleep 1
  done
}

stamp() {  # add "_t" to every JSON line; wrap anything else so nothing is lost
  python3 -u -c '
import sys,json,time
for line in sys.stdin:
    t=time.time(); s=line.rstrip("\n")
    try:
        ev=json.loads(s)
        if isinstance(ev,dict): ev["_t"]=t; print(json.dumps(ev),flush=True); continue
    except ValueError: pass
    print(json.dumps({"_t":t,"_raw":s}),flush=True)'
}

for M in "$@"; do
 for RUN in $(seq 1 "$RUNS"); do
  SAFE=$(echo "$M" | tr ':/' '__')
  ID="${SAFE}-${FIXTURE}-think${THINKING}-r${RUN}"
  printf '\n\033[1m## cc-session %s  fixture=%s thinking=%s run %s/%s\033[0m\n' "$M" "$FIXTURE" "$THINKING" "$RUN" "$RUNS"
  WORK="$WORKROOT/$ID"; LOG="$OUT/$ID.jsonl"; PSLOG="$OUT/$ID.ps.tsv"
  make_fixture "$WORK"

  # Pre-warm, outside the timed window, exactly like the shell functions.
  W0=$(date +%s.%N)
  curl -s -m 900 "$API/api/generate" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$M\",\"prompt\":\"hi\",\"keep_alive\":\"30m\",\"stream\":false}" >/dev/null
  WARM=$(python3 -c "import time;print(round(time.time()-$W0,1))")

  ps_sampler > "$PSLOG" & SAMPLER=$!
  THINK_ARGS=()
  [ "$THINKING" = off ] && THINK_ARGS=(--append-system-prompt '<|think_off|>')
  START=$(date +%s)
  ( cd "$WORK" && timeout "$TMO" env \
      ANTHROPIC_AUTH_TOKEN=ollama \
      ANTHROPIC_BASE_URL="$API" \
      ANTHROPIC_API_KEY="" \
      ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
      ANTHROPIC_DEFAULT_SONNET_MODEL="$M" \
      ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \
      CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 \
      claude -p "$PROMPT" --model "$M" "${THINK_ARGS[@]}" \
        --permission-mode bypassPermissions \
        --output-format stream-json --verbose \
      2>&1 | stamp > "$LOG" )
  RC=${PIPESTATUS[0]}
  END=$(date +%s); WALL=$((END-START))
  kill "$SAMPLER" 2>/dev/null; wait "$SAMPLER" 2>/dev/null

  ( cd "$WORK" && git add -A && git diff --cached HEAD ) > "$OUT/$ID.patch"
  TESTS_EDITED=$( cd "$WORK" && git diff --cached --name-only HEAD -- tests/ | wc -l )
  SRC_EDITED=$(   cd "$WORK" && git diff --cached --name-only HEAD -- "$SRC" | wc -l )
  if ( cd "$WORK" && pytest -q -p no:cacheprovider >/dev/null 2>&1 ); then GREEN=1; else GREEN=0; fi

  HIDDEN="-"
  if [ "$FIXTURE" = hard ]; then
    # Score on a COPY, so the held-out tests never touch the model's tree.
    H=$(mktemp -d); command cp -r "$WORK/." "$H/"; command cp -r "$D/fixtures/ledger-hidden" "$H/hidden"
    HIDDEN=$( cd "$H" && pytest -q -p no:cacheprovider hidden 2>&1 | python3 -c '
import sys,re
s=sys.stdin.read(); p=re.search(r"(\d+) passed",s); f=re.search(r"(\d+) failed",s); e=re.search(r"(\d+) error",s)
# Denominator fixed at 18: a model that breaks an import makes pytest report
# "1 error" at collection, and that must score 0/18, not 0/1.
print("%d/18"%(int(p.group(1)) if p else 0))')
    rm -rf "$H"
  fi

  NOTE=""
  if [ "$RC" -eq 124 ]; then VERDICT="FAIL"; NOTE="timeout after ${TMO}s"
  elif [ "$GREEN" -eq 1 ] && [ "$TESTS_EDITED" -gt 0 ]; then VERDICT="CHEAT"; NOTE="edited tests/"
  elif [ "$GREEN" -eq 1 ] && [ "$SRC_EDITED" -gt 0 ]; then VERDICT="PASS"
  elif [ "$GREEN" -eq 1 ]; then VERDICT="CHEAT"; NOTE="green without a source change"
  else VERDICT="FAIL"; NOTE="tests still red (rc=$RC)"; fi

  # Reloads: our model absent from /api/ps after it was present, or its
  # context_length changed. Foreign: any other tag resident during the session.
  read -r RELOADS FOREIGN < <(python3 - "$PSLOG" "$M" <<'PY'
import sys
log, model = sys.argv[1], sys.argv[2]
seen = False; reloads = 0; last_ctx = None; foreign = set()
for line in open(log):
    parts = line.rstrip("\n").split("\t", 1)
    if len(parts) < 2 or parts[1] in ("ERR", ""):
        continue
    ours = None
    for item in ([] if parts[1] == "-" else parts[1].split(" ")):
        f = item.split("|")
        if f[0] == model: ours = f
        else: foreign.add(f[0])
    if ours is None:
        if seen: reloads += 1; seen = False
        continue
    if last_ctx is not None and ours[3] != last_ctx: reloads += 1
    last_ctx = ours[3]; seen = True
print(reloads, ",".join(sorted(foreign)) or "-")
PY
)
  A=$(python3 "$D/cc-analyse.py" "$LOG" --tsv)
  IFS=$'\t' read -r CALLS TURNS INTOK OUTTOK THINKC APIS TTFT MAXGAP TOOLS SUBFAIL ISERR <<< "$A"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date +%F)" "$VERSION" "$M" "$FIXTURE" "$THINKING" "$RUN" "$VERDICT" "$HIDDEN" "$WALL" "$WARM" \
    "$CALLS" "$TURNS" "$INTOK" "$OUTTOK" "$THINKC" "$APIS" "$TTFT" "$MAXGAP" "$TOOLS" "$RELOADS" "$FOREIGN" "$NOTE" >> "$TSV"
  printf '   %-6s hidden=%-5s wall=%4ss warm=%5ss calls=%-3s out=%-6s think=%-6s ttft=%-6s maxgap=%-6s reloads=%s foreign=%s tools=%s %s\n' \
    "$VERDICT" "$HIDDEN" "$WALL" "$WARM" "$CALLS" "$OUTTOK" "$THINKC" "$TTFT" "$MAXGAP" "$RELOADS" "$FOREIGN" "$TOOLS" "$NOTE"
 done
done
printf '\nwrote %s\n' "$TSV"
