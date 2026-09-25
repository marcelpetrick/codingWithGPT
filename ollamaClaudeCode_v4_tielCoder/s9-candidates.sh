#!/usr/bin/env bash
# s9-candidates.sh -- the 2026-09-21 candidate screen (plan.md §8.3).
#
# Six plausible new tags exist, the box holds one model at a time, and a
# Terminal-Bench pass costs ~1.5 h per model. So candidates are SCREENED before
# they are benchmarked, with the cheapest test first, and the screen is
# pre-registered in plan.md §8.3 so it cannot be argued with afterwards:
#
#   G1 fit          100% GPU (size_vram == size) at the largest window that fits
#   G2 tools        >=9/10 on agentic-test.sh, no reproducible failure
#   G3 turn economy ledger fixture n=3 at thinking ON:
#                   median wall <= 150 s AND median hidden >= 16/18
#
# G3 is turn economy and NOT tok/s, on this box's own evidence: qwen3.8:27b
# scored 18/18 hidden three times and still took 787 s (capable, wrong shape),
# while nemotron-cascade-2 was the fastest model on the box on both axes and
# finished nothing. What you wait for is turns x latency. tok/s, prefill and
# residency are measured and reported for every candidate -- they are simply
# not the gate.
#
# Every candidate gets a row whether it passes or not. Anything cut at G1 is
# deleted the same session: a rejected 20 GB candidate must not sit on a shared
# disk (plan.md §8.5 rule 5).
#
# Usage: ./s9-candidates.sh [--host H] [--only NAME]... [--stage fit|gates|session|all]
#                           [--dry-run]
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"

HOST="192.168.100.67"; PORT="11434"; STAGE="all"; DRY=0; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --only) ONLY="${ONLY}${ONLY:+ }$2"; shift 2 ;;
    --stage) STAGE="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
BASE="http://${HOST}:${PORT}"
TSV="$HERE/results/candidates-2026-09-21.tsv"
LOG="$HERE/results/s9.log"
mkdir -p "$HERE/results"

# name | source tag to pull | expected GiB (HF tree API / registry manifest) | class | baked tag
# Expected size is a GATE, not a note: Ollama resolves an hf.co tag to a file by
# its quant label, and byteshape ships TWO files labelled Q4_K_S (3.80 and 4.22
# bpw). Pulling the wrong one would silently put us below the 4-bit floor, and
# nothing in /api/show says "this is the 3.8 bpw rung". The size does.
# RANKED 2026-09-24 after a web sweep of every candidate (cards, community tabs,
# independent measurements, Ollama issues) -- ROUND_2026-09-24.md has the
# evidence. Best first; s10-one.sh runs them one at a time in this order.
# Expected GiB now INCLUDES the vision projector where the repo ships one:
# Ollama pulls it as a layer and /api/tags counts it (Tiel: 25.13 file, 25.61
# listed), so without it the +-3% gate would cut a correct pull as a wrong rung.
#
# Not run -- ruled out on the evidence, nothing pulled:
#   ornith15-27b-coder  expert prune of Ornith-1.5, whose own tab reports broken
#                       basic tool calls and looping; author's evals weakest at planning
#   qwen36-27b-coder    community prune, NOT an official Qwen release; lowest
#                       tool-eval score in its own author's table
#   kat-ornith-35b      quant-only, source repo deleted, no card, no numbers
#   signoffour-35b      unevaluated 4-way merge with a custom chat template
#   omnimerge-v4/-v6    dense 27B merges; v4 leaks unclosed think tags by its
#                       author's account; dense 27B is already 4x too slow here
#   glm-4.7-flash       January model, behind qwen3.6 on every independent
#                       comparison, long history of Ollama tool-call bugs
#   qwen3-coder-30b     July 2025, superseded by qwen3.6 on every 2026 comparison
# The 6th field is the VENDOR sampler, baked into the tag. Claude Code sends no
# temperature, so the baked value is what every trial runs at (ROUND_2026-09-21
# defect 4). Empty = the vendor gives none; the library/GGUF default stands.
CANDIDATES=(
  "occamy|hf.co/Accio-Lab/occamy-1.0-GGUF:Q5_K_M|23.87|M|occamy-1.0:q5km-ctx256k-agentic|\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20"
  "kat-coder|hf.co/bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF:Q5_K_M|23.30|M|kat-coder-v2.5:q5km-ctx256k-agentic|\"temperature\":1.0,\"top_p\":0.95"
  "ornith15-35b|hf.co/ornith-ai/Ornith-1.5-35B-A3B-GGUF:Q5_K_M|24.45|M|ornith-1.5-35b:q5km-ctx256k-agentic|\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20"
  "byteshape|hf.co/byteshape/Qwen3.6-35B-A3B-GGUF:Q4_K_S-4.22bpw|17.86|M|byteshape-qwen3.6-35b:q4ks-ctx256k-agentic|\"temperature\":0.6,\"top_p\":0.95,\"top_k\":20,\"min_p\":0"
  # back 2026-09-25: re-gated under the current setup at Poolside's sampler, 9/10 (T4 partial)
  "laguna-xs21|laguna-xs-2.1:q4_K_M|18.88|M|laguna-xs-2.1:q4km-ctx256k-agentic|\"temperature\":1.0,\"top_k\":20,\"top_p\":1.0"
)

say () { printf '\n\033[1m%s\033[0m\n' "$*" | tee -a "$LOG"; }
note () { printf '   %s\n' "$*" | tee -a "$LOG"; }

[ -s "$TSV" ] || printf 'date\tname\tclass\tsource\tbaked_tag\tgguf_gib\tgot_gib\tctx\tresident_gb\tvram_gb\tfit\tgates\tgen_toks\tprefill_toks\tledger_median_s\tledger_hidden\tverdict\tnote\n' > "$TSV"

row () {  # name class source tag exp got ctx res vram fit gates gen pre med hid verdict note
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date +%F)" "$@" >> "$TSV"
}

# ---------------------------------------------------------------- per candidate
for spec in "${CANDIDATES[@]}"; do
  IFS='|' read -r NAME SRC EXP CLASS TAG SAMP <<< "$spec"
  if [ -n "$ONLY" ] && ! echo " $ONLY " | grep -q " $NAME "; then continue; fi
  say "=== $NAME  ($CLASS)  $SRC"
  if [ "$DRY" = 1 ]; then note "dry run: would pull, bake as $TAG, expect ${EXP} GiB"; continue; fi

  # Idempotent: a candidate already carrying a verdict is not screened again.
  # This is what makes the whole chain re-runnable -- if the link to .67 drops
  # or the laptop sleeps, running run-all.sh again resumes instead of repeating
  # hours of pulls and sessions.
  # only a FINAL verdict skips (SCREENED-IN / CUT-*); a VOID or partial-stage row must
  # not block a re-screen forever (review_20260925 #11)
  FINAL=$(awk -F'\t' -v t="$TAG" '$5==t && $17 ~ /^(SCREENED-IN|CUT-)/ {v=$17} END {print v}' "$TSV" 2>/dev/null)
  if [ -n "$FINAL" ]; then
    note "already screened ($FINAL) -- skipping"
    continue
  fi

  # be a good neighbour before touching the box at all
  ./idle.sh --host "$HOST" --port "$PORT" --mine "$TAG" >/dev/null 2>&1

  # ---- pull ------------------------------------------------------------------
  note "pulling (this is the slow part; no GPU is touched)"
  curl -s -m 7200 "$BASE/api/pull" -d "{\"model\":\"$SRC\",\"stream\":false}" | tee -a "$LOG" | tail -1
  # An unreachable server is not a result. On 2026-09-24 the link to .67
  # dropped at 16:51; the size read came back EMPTY, the gate called it a
  # wrong rung and tried to delete both KAT and ByteShape. Stop instead.
  if ! curl -s -m 10 "$BASE/api/version" >/dev/null; then
    note "SERVER UNREACHABLE -- screen stopped, nothing recorded, nothing deleted"
    exit 3
  fi
  GOT=$(./s9-parse.py size "$BASE" "$SRC")
  if [ -z "$GOT" ]; then
    note "size read failed -- not recorded"; exit 3
  fi
  if [ "$GOT" = "0" ]; then
    note "PULL FAILED -- not on the box"; row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "-" "-" "-" "-" "CUT" "-" "-" "-" "-" "-" "CUT-pull" "pull failed"; continue
  fi
  # size gate: +-3% of the HF file, else we resolved to a different rung
  OK=$(./s9-parse.py sizematch "$GOT" "$EXP")
  note "got ${GOT} GiB (expected ${EXP})  -> size match: $OK"
  if [ "$OK" = "no" ]; then
    note "WRONG RUNG -- the hf.co tag resolved to a different file. Not measured."
    row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "$GOT" "-" "-" "-" "CUT" "-" "-" "-" "-" "-" "CUT-wrong-rung" "quant label is ambiguous upstream"
    curl -s -X DELETE "$BASE/api/delete" -d "{\"model\":\"$SRC\"}" >/dev/null; continue
  fi

  # ---- bake the deployable variant ------------------------------------------
  # num_ctx is clamped to the model's own native window: baking a window larger
  # than the architecture supports is how you get a silent half-context.
  NATIVE=$(./s9-parse.py native "$BASE" "$SRC")
  CTX=$(./s9-parse.py clamp_ctx "$NATIVE")
  note "native window ${NATIVE} -> baking num_ctx ${CTX}, presence_penalty 0"
  # A hf.co GGUF brings its own Jinja chat template, and Ollama renders with it.
  # occamy's raises "System message must be at the beginning" on the mid-
  # conversation system content Claude Code sends -- every session died on a
  # 500 before one token (2026-09-24). The qwen35moe family gets Ollama's own
  # renderer and parser instead, exactly as our qwen3.6 control runs.
  FAM=$(./s9-parse.py family "$BASE" "$SRC")
  RP=""
  [ "$FAM" = "qwen35moe" ] && RP='"renderer":"qwen3.5","parser":"qwen3.5",'
  note "family ${FAM:-?} -> ${RP:+renderer/parser qwen3.5}${RP:-GGUF template}"
  curl -s -m 600 "$BASE/api/create" -d "{\"model\":\"$TAG\",\"from\":\"$SRC\",\"parameters\":{\"num_ctx\":$CTX,\"presence_penalty\":0${SAMP:+,$SAMP}},${RP}\"stream\":false}" >/dev/null

  # ---- capabilities, before any claim about vision or tools ------------------
  CAPS=$(./s9-parse.py caps "$BASE" "$TAG")
  note "capabilities: ${CAPS:-none reported}"

  # ---- G1: does it stay on the GPU ------------------------------------------
  # A model that did not LOAD is not a model that spilled. occamy read
  # "resident 0 GB" on 2026-09-24, was booked as a spill and deleted, and the
  # load error was thrown away. Keep the response, retry once, never delete.
  for TRY in 1 2; do
    LOADR=$(curl -s -m 900 "$BASE/api/generate" -d "{\"model\":\"$TAG\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1}}")
    read -r RES VRAM <<< "$(./s9-parse.py ps "$BASE" "$TAG")"
    # an EMPTY read (ps timed out, link dropped) is neither loaded nor spilled:
    # stop, record nothing, delete nothing -- the 09-24 16:51 failure one step later
    if ! [[ "${RES:-}" =~ ^[0-9.]+$ && "${VRAM:-}" =~ ^[0-9.]+$ ]]; then
      note "residency read failed (RES='${RES:-}' VRAM='${VRAM:-}') -- screen stopped, nothing recorded or deleted"; exit 3
    fi
    [ "${RES%.*}" != "0" ] && break
    note "load attempt $TRY: not resident -- response: $(echo "$LOADR" | head -c 300)"
    sleep 15
  done
  if [ "${RES%.*}" = "0" ]; then
    note "G1 LOAD FAILURE -- not a spill; tags kept for diagnosis"
    row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "$GOT" "$CTX" "$RES" "$VRAM" "FAIL" "-" "-" "-" "-" "-" "VOID-load" "$(echo "$LOADR" | tr '\t\n' '  ' | head -c 200)"
    continue
  fi
  FIT=$(./s9-parse.py fit "$RES" "$VRAM")
  note "resident ${RES} GB, vram ${VRAM} GB  -> G1 $FIT"
  if [ "$FIT" != "PASS" ]; then
    note "SPILLED -- a 12.5% spill cost 5.3x in v1. Cut, and the tags go with it."
    row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "$GOT" "$CTX" "$RES" "$VRAM" "FAIL" "-" "-" "-" "-" "-" "CUT-G1" "spilled at ctx $CTX"
    curl -s -X DELETE "$BASE/api/delete" -d "{\"model\":\"$TAG\"}" >/dev/null
    curl -s -X DELETE "$BASE/api/delete" -d "{\"model\":\"$SRC\"}" >/dev/null
    continue
  fi
  [ "$STAGE" = "fit" ] && { row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "$GOT" "$CTX" "$RES" "$VRAM" "PASS" "-" "-" "-" "-" "-" "G1-only" "$CAPS"; continue; }

  # ---- throughput: reported, never the gate ---------------------------------
  ./tokrate.sh --host "$HOST" --port "$PORT" "$TAG" 2>&1 | tail -4 | tee -a "$LOG"
  GEN=$(./s9-parse.py gen "$TAG")
  note "generation ${GEN} tok/s (recorded, not a gate)"

  # ---- G2: tool gates --------------------------------------------------------
  GATES="-"
  if [ "$STAGE" = "all" ] || [ "$STAGE" = "gates" ]; then
    ./agentic-test.sh "$HOST" "$TAG" 2>&1 | tail -12 | tee -a "$LOG"
    # Count from the gate TSV itself: agentic-test.sh prints no "x/10" summary,
    # and grepping the shared log for one read "unknown" (occamy, 2026-09-24).
    GT="$HERE/results/agentic/$(echo "$TAG" | tr '/:' '__').tsv"
    GP=$(awk -F'\t' 'NR>1 && $2=="PASS"' "$GT" 2>/dev/null | wc -l)
    GN=$(awk -F'\t' 'NR>1' "$GT" 2>/dev/null | wc -l)
    GATES="$GP/$GN"
    note "G2 gates: $GATES"
    # G2 is a GATE (>= 9/10); the screen used to record it and carry on.
    if [ "$GN" -eq 0 ] || [ "$GP" -lt 9 ]; then
      note "G2 FAIL -- not taken to the ledger session"
      row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "$GOT" "$CTX" "$RES" "$VRAM" "PASS" "$GATES" "$GEN" "-" "-" "-" "CUT-G2" "$CAPS"
      continue
    fi
  fi
  [ "$STAGE" = "gates" ] && { row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "$GOT" "$CTX" "$RES" "$VRAM" "PASS" "$GATES" "$GEN" "-" "-" "-" "G2-only" "$CAPS"; continue; }

  # ---- G3: turn economy on the ledger fixture --------------------------------
  ./cc-session.sh --host "$HOST" --port "$PORT" --fixture hard --runs 3 --thinking on "$TAG" 2>&1 | tail -15 | tee -a "$LOG"
  read -r MED HID <<< "$(./s9-parse.py ledger "$TAG")"
  VERDICT=$(./s9-parse.py verdict "$MED" "$HID")
  SL="$(echo "$TAG" | tr '/:' '__')"
  if [ "$(./s9-parse.py apierr "$HERE"/results/cc/"$SL"-hard-thinkon-r[0-9]*.jsonl)  # r[0-9]: never an A/B arm's -remindon- files" = "yes" ]; then
    VERDICT="VOID-harness"; note "a session ended on an API error -- VOID, not a model result"
  fi
  note "G3 ledger: median ${MED} s, hidden ${HID}/18 -> $VERDICT"
  row "$NAME" "$CLASS" "$SRC" "$TAG" "$EXP" "$GOT" "$CTX" "$RES" "$VRAM" "PASS" "$GATES" "$GEN" "-" "$MED" "$HID" "$VERDICT" "$CAPS"

  # be a good neighbour: hand the box back
  curl -s "$BASE/api/generate" -d "{\"model\":\"$TAG\",\"keep_alive\":0}" >/dev/null
done

say "=== screen complete -- $TSV"
column -t -s $'\t' "$TSV" 2>/dev/null || cat "$TSV"
echo "S9-CANDIDATES-DONE"
