#!/usr/bin/env bash
# tb-run.sh — run the Terminal-Bench-style suite against one or more models.
#
# Model-outer, task-inner (the box holds one model). Each task:
#   1. agent container: v4-tb-sandbox on the --internal network, egress ONLY to
#      the .67 relay; the model drives Claude Code with the toolchain available,
#      seeded with the task's seed/ files and given task.md as the prompt.
#   2. the finished /work tree comes back as a base64 tar on stdout (no host
#      mount, same trick as cc-session-sandboxed).
#   3. verify container: --network none, no model, extracts the tree and runs the
#      task's verify.sh. Kept separate so the agent can never read or game the
#      verifier, and so the compile/run is deterministic and offline.
#
# Scored: SOLVED (verify exit 0) / FAIL, plus turns/tools/wall/tokens from the
# transcript via cc-analyse.py. Thinking off by default (v4: 2.3x, no loss).
set -uo pipefail
HOST="192.168.100.67"; PORT="11434"; TMO=1800; THINKING="off"; RUNS=1
while [ $# -gt 0 ]; do case "$1" in
  --host) HOST="$2"; shift 2;; --port) PORT="$2"; shift 2;;
  --timeout) TMO="$2"; shift 2;; --thinking) THINKING="$2"; shift 2;;
  --runs) RUNS="$2"; shift 2;; *) break;; esac; done
[ $# -ge 1 ] || { echo "usage: tb-run.sh [opts] <model>..." >&2; exit 2; }

D="$(dirname "$(readlink -f "$0")")"; ROOT="$(dirname "$D")"
IMG="v4-tb-sandbox:latest"; NET="v4-egress-none"; RELAY="v4-relay"
API="http://${HOST}:${PORT}"
OUT="$ROOT/results/tb"; mkdir -p "$OUT"
TSV="$ROOT/results/terminalbench.tsv"
VER=$(curl -s -m10 "$API/api/version" | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null || echo "?")
[ -s "$TSV" ] || printf 'date\tollama\tmodel\tthinking\trun\ttask\tverdict\twall_s\tcalls\tout_tok\tthink_chars\tegress\n' > "$TSV"
docker image inspect "$IMG" >/dev/null 2>&1 || { echo "build the image: docker build -t $IMG -f $D/Dockerfile.tb $D" >&2; exit 2; }

# bring up the internal network + relay (idempotent)
docker network inspect "$NET" >/dev/null 2>&1 || docker network create --internal "$NET" >/dev/null
if ! docker inspect "$RELAY" >/dev/null 2>&1; then
  docker run -d --name "$RELAY" --network "$NET" alpine:latest \
    sh -c "apk add -q socat && socat TCP-LISTEN:11434,fork,reuseaddr TCP:${HOST}:${PORT}" >/dev/null
  docker network connect bridge "$RELAY" >/dev/null
  for _ in $(seq 1 30); do docker run --rm --network "$NET" "$IMG" \
    "curl -s -m3 -o /dev/null -w '%{http_code}' http://${RELAY}:11434/api/version" 2>/dev/null | grep -q 200 && break; sleep 1; done
fi
trap 'docker rm -f "$RELAY" >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1' EXIT
RELAY_URL="http://${RELAY}:11434"

for M in "$@"; do
 for RUN in $(seq 1 "$RUNS"); do
  "$ROOT/idle.sh" --host "$HOST" --port "$PORT" --mine "$M" || { echo "ABORT: busy" >&2; exit 1; }
  # warm the model once for this whole model block
  curl -s -m900 "$API/api/generate" -d "{\"model\":\"$M\",\"prompt\":\"hi\",\"keep_alive\":\"2h\",\"stream\":false}" >/dev/null
  for task in "$D"/tasks/*/; do
    name=$(basename "$task"); SAFE=$(echo "$M"|tr ':/' '__')
    ID="${SAFE}-${name}-think${THINKING}-r${RUN}"; LOG="$OUT/$ID.jsonl"
    printf '\n\033[1m## TB %s / %s (think %s, run %s)\033[0m\n' "$M" "$name" "$THINKING" "$RUN"
    STAGE=$(mktemp -d); mkdir -p "$STAGE/work"; cp -r "$task/seed/." "$STAGE/work/" 2>/dev/null || true
    PROMPT=$(cat "$task/task.md")
    TARGS=""; [ "$THINKING" = off ] && TARGS="--append-system-prompt <|think_off|>"
    CID="tb-$$-$name-$RUN"
    docker create --name "$CID" --network "$NET" \
      --read-only --tmpfs /work:rw,exec,size=512m,uid=1000,gid=1000 \
      --tmpfs /home/agent:rw,exec,size=256m,uid=1000,gid=1000 --tmpfs /tmp:rw,exec,size=256m,uid=1000,gid=1000 \
      --cap-drop ALL --security-opt no-new-privileges --pids-limit 512 --memory 4g \
      -e ANTHROPIC_AUTH_TOKEN=ollama -e ANTHROPIC_BASE_URL="$RELAY_URL" -e ANTHROPIC_API_KEY= \
      -e ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" -e ANTHROPIC_DEFAULT_SONNET_MODEL="$M" -e ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \
      -e CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000 -e CC_PROMPT="$PROMPT" -e CC_MODEL="$M" -e CC_TARGS="$TARGS" \
      -e CC_FIX="$(tar czf - -C "$STAGE/work" . | base64 -w0)" "$IMG" \
      'cd /work && printf %s "$CC_FIX" | base64 -d | tar xzf -;
       timeout '"$TMO"' claude -p "$CC_PROMPT" --model "$CC_MODEL" $CC_TARGS --permission-mode bypassPermissions --output-format stream-json --verbose;
       echo "__RC__$?"; echo "__WORKTAR__$(tar czf - -C /work . | base64 -w0)"' >/dev/null
    docker start -a "$CID" 2>&1 | python3 -u -c '
import sys,json,time
for line in sys.stdin:
    t=time.time(); s=line.rstrip("\n")
    try:
        ev=json.loads(s)
        if isinstance(ev,dict): ev["_t"]=t; print(json.dumps(ev),flush=True); continue
    except ValueError: pass
    print(json.dumps({"_t":t,"_raw":s}),flush=True)' > "$LOG"
    # extract the finished tree
    WORK=$(mktemp -d)
    python3 - "$LOG" "$WORK" <<'PYX'
import base64,io,json,sys,tarfile
blob=None
for line in open(sys.argv[1],errors="replace"):
    line=line.strip()
    if not line.startswith("{"): continue
    try: ev=json.loads(line)
    except ValueError: continue
    raw=ev.get("_raw","")
    if isinstance(raw,str) and raw.startswith("__WORKTAR__"): blob=raw[len("__WORKTAR__"):]
if blob:
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(blob))) as tf: tf.extractall(sys.argv[2])
PYX
    docker rm -f "$CID" >/dev/null 2>&1; rm -rf "$STAGE"
    # verify in an isolated, network-less container
    VSTAGE=$(mktemp -d); mkdir -p "$VSTAGE/work"; cp -r "$WORK/." "$VSTAGE/work/" 2>/dev/null || true
    cp "$task/verify.sh" "$VSTAGE/verify.sh"
    envs=(); [ -f "$task/seed/test_roman.c" ] && envs=(-e TB_TEST_SHA="$(sha256sum "$task/seed/test_roman.c"|cut -d' ' -f1)")
    tar czf - -C "$VSTAGE" . | docker run --rm -i --network none --user 0 "${envs[@]}" "$IMG" \
      'mkdir -p /v && tar xzf - -C /v && bash /v/verify.sh' >"$OUT/$ID.verify" 2>&1
    VRC=$?; rm -rf "$VSTAGE" "$WORK"
    VERDICT=SOLVED; [ $VRC -eq 0 ] || VERDICT=FAIL
    # egress self-check
    EG=$(docker run --rm --network "$NET" "$IMG" \
      'i=$(curl -s -m4 -o /dev/null -w "%{http_code}" http://1.1.1.1 2>/dev/null||echo blk); echo "net=$i"' 2>/dev/null||echo "net=?")
    A=$(python3 "$ROOT/cc-analyse.py" "$LOG" --tsv 2>/dev/null)
    IFS=$'\t' read -r CALLS TURNS INTOK OUTTOK THINKC APIS TTFT MAXGAP TOOLS SUBF ISERR <<< "$A"
    WALL=$(python3 -c "import json;ts=[json.loads(l).get('_t') for l in open('$LOG',errors='replace') if l.strip().startswith('{')];ts=[t for t in ts if t];print(round(max(ts)-min(ts)) if len(ts)>1 else 0)" 2>/dev/null||echo 0)
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date +%F)" "$VER" "$M" "$THINKING" "$RUN" "$name" "$VERDICT" "$WALL" "${CALLS:-?}" "${OUTTOK:-?}" "${THINKC:-?}" "$EG" >> "$TSV"
    printf '   %-8s %-20s wall=%ss calls=%s [%s]\n' "$VERDICT" "$name" "$WALL" "${CALLS:-?}" "$EG"
  done
  "$ROOT/idle.sh" --host "$HOST" --port "$PORT" --mine "$M" || true
 done
done
printf '\nwrote %s\n' "$TSV"
