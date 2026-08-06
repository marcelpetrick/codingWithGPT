#!/usr/bin/env bash
# ollamaFarm.sh — live view of the Ollama servers on the local network.
#
# A btop-style monitor for a small farm of Ollama hosts. Beyond "what is loaded",
# it watches for the four failure modes that this hardware actually suffers from,
# every one of which is silent through the API (measurements: review2.md):
#
#   1. EVICTION THRASH — a second model displaces the resident one. On the 36 GB
#      box the 33 GB MoE plus anything else does not fit, so any second model
#      unloads it and the next real request pays a ~70 s reload. Invisible in a
#      snapshot; only a diff between polls reveals it.
#   2. SPLIT PLACEMENT — size_vram < size means part of the model sits in system
#      RAM. Measured cost: 5.3x throughput, with no error reported anywhere.
#   3. MISSING BAKED num_ctx — a model whose Modelfile leaves num_ctx unset is
#      capped at 16384 tokens through /v1/messages (which has no num_ctx knob),
#      and tool calling stops entirely past that point without an error.
#   4. presence_penalty != 0 — the qwen vendor default of 1.5 costs ~35% of
#      generation throughput for nothing.
#
# Keys (btop-style), active while running:
#   -  /  +    faster / slower refresh      p   pause (p again to resume)
#   v          VRAM bars on/off             m   per-model detail on/off
#   w          warnings on/off              e   event log on/off
#   d          re-run host discovery        s   toggle nvidia-smi over SSH
#   h  or  ?   help overlay                 q   quit
#
# Usage:
#   ./ollamaFarm.sh                    # default hosts, 1 s refresh
#   ./ollamaFarm.sh -n 2               # every 2 s
#   ./ollamaFarm.sh -H 192.168.100.67,192.168.100.99
#   ./ollamaFarm.sh -D                 # discover hosts on the /24 at startup
#   ./ollamaFarm.sh --ssh              # also pull nvidia-smi over SSH (needs keys)
#   ./ollamaFarm.sh --no-color         # plain output (also honours NO_COLOR)
#
# Settings (interval and toggles) persist to $XDG_CONFIG_HOME/ollamafarm/config,
# so the refresh rate you picked is still there next time.
#
# On GPU temperature: the Ollama HTTP API does not expose temperature, fan, power
# or GPU utilisation — it reports model residency only. Those counters live in
# nvidia-smi on the server. As of 2026-08-06 SSH to both hosts is refused
# (publickey,password), so the --ssh path is present but inert until key access
# exists. Everything else shown is real API data.
#
# On discovery: hosts are found by probing /api/version across the /24. Usable
# VRAM is deliberately NOT probed — establishing it means pushing num_ctx until
# the model spills, which loads models and disturbs a shared server. Known
# ceilings are listed in VRAM_TOTAL below; discovered hosts show "?" and get no
# bar rather than a guessed one.

set -uo pipefail

# ---------------------------------------------------------------- defaults ----
PORT=11434
DEFAULT_HOSTS="192.168.100.37 192.168.100.67"
HOSTS="$DEFAULT_HOSTS"
USE_SSH=0
DO_DISCOVER=0
WANT_COLOR=auto
HOSTS_FROM_ARG=0

# Interval ladder, btop-style: + and - step through it rather than free-typing.
INTERVALS=(0.25 0.5 1 2 3 5 10 30)
IDX=2                      # -> 1 s
SHOW_BARS=1
SHOW_MODELS=1
SHOW_WARN=1
SHOW_EVENTS=1
PAUSED=0
SHOW_HELP=0

# Measured usable VRAM ceilings (review.md / review2.md). Used only to draw bars.
# Absent host => "?" and no bar; nothing here is inferred.
declare -A VRAM_TOTAL=( [192.168.100.37]=12.2 [192.168.100.67]=36.1 )

CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/ollamafarm"
CFG="$CFG_DIR/config"
CACHE_HOSTS="$CFG_DIR/hosts"

# ------------------------------------------------------------ config load -----
# Only ever read back keys we wrote, and validate each one: a corrupt or
# hand-edited config must not be able to break the run or inject commands.
load_config() {
  [ -r "$CFG" ] || return 0
  local k v
  while IFS='=' read -r k v; do
    case "$k" in
      idx)          [[ "$v" =~ ^[0-9]+$ ]] && [ "$v" -lt "${#INTERVALS[@]}" ] && IDX="$v" ;;
      show_bars)    [[ "$v" =~ ^[01]$ ]] && SHOW_BARS="$v" ;;
      show_models)  [[ "$v" =~ ^[01]$ ]] && SHOW_MODELS="$v" ;;
      show_warn)    [[ "$v" =~ ^[01]$ ]] && SHOW_WARN="$v" ;;
      show_events)  [[ "$v" =~ ^[01]$ ]] && SHOW_EVENTS="$v" ;;
    esac
  done < "$CFG"
}

save_config() {
  mkdir -p "$CFG_DIR" 2>/dev/null || return 0
  { printf 'idx=%s\n' "$IDX"
    printf 'show_bars=%s\n' "$SHOW_BARS"
    printf 'show_models=%s\n' "$SHOW_MODELS"
    printf 'show_warn=%s\n' "$SHOW_WARN"
    printf 'show_events=%s\n' "$SHOW_EVENTS"
  } > "$CFG.tmp" 2>/dev/null && mv -f "$CFG.tmp" "$CFG" 2>/dev/null
}

load_config

# --------------------------------------------------------------- arguments ----
usage() { sed -n '2,60p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    -n|--interval)
      # Accept a raw seconds value by snapping to the nearest ladder rung, so the
      # flag and the +/- keys can never disagree about the current interval.
      [ $# -ge 2 ] || { echo "-n needs a value" >&2; exit 2; }
      local_best=0; local_bestd=""
      for i in "${!INTERVALS[@]}"; do
        d=$(awk -v a="${INTERVALS[$i]}" -v b="$2" 'BEGIN{d=a-b; print (d<0?-d:d)}')
        if [ -z "$local_bestd" ] || awk -v x="$d" -v y="$local_bestd" 'BEGIN{exit !(x<y)}'; then
          local_bestd="$d"; local_best="$i"
        fi
      done
      IDX="$local_best"; shift 2 ;;
    -H|--hosts)   [ $# -ge 2 ] || { echo "-H needs a value" >&2; exit 2; }
                  HOSTS=$(echo "$2" | tr ',' ' '); HOSTS_FROM_ARG=1; shift 2 ;;
    -p|--port)    [ $# -ge 2 ] || { echo "-p needs a value" >&2; exit 2; }
                  PORT="$2"; shift 2 ;;
    -D|--discover) DO_DISCOVER=1; shift ;;
    --ssh)        USE_SSH=1; shift ;;
    --no-color)   WANT_COLOR=never; shift ;;
    --color)      WANT_COLOR=always; shift ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "unknown arg: $1  (try --help)" >&2; exit 2 ;;
  esac
done

[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "port must be numeric: $PORT" >&2; exit 2; }

# ------------------------------------------------------------- dependencies ---
for dep in curl jq awk; do
  command -v "$dep" >/dev/null || { echo "$dep is required" >&2; exit 1; }
done

# ------------------------------------------------------------------ colours ---
# Colour encodes STATE, never decoration: green = healthy/resident,
# red = actively costing you performance, yellow = about to change.
use_color=1
case "$WANT_COLOR" in
  never)  use_color=0 ;;
  always) use_color=1 ;;
  auto)   { [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; } || use_color=0 ;;
esac
if [ "$use_color" = "1" ]; then
  C_RST=$'\e[0m'; C_DIM=$'\e[2m'; C_B=$'\e[1m'; C_REV=$'\e[7m'
  C_GRN=$'\e[32m'; C_YEL=$'\e[33m'; C_RED=$'\e[31m'
  C_CYA=$'\e[36m'; C_MAG=$'\e[35m'
else
  C_RST=""; C_DIM=""; C_B=""; C_REV=""
  C_GRN=""; C_YEL=""; C_RED=""; C_CYA=""; C_MAG=""
fi

# --------------------------------------------------------------- terminal -----
TTY_STATE=""
cleanup() {
  # Restore unconditionally: cursor, echo, and the saved termios. Without the
  # stty restore an interrupt mid-read leaves the user's shell without echo.
  [ -n "$TTY_STATE" ] && stty "$TTY_STATE" 2>/dev/null
  printf '\e[?25h\e[0m\n'
  save_config
  exit 0
}
trap cleanup INT TERM EXIT
if [ -t 0 ]; then
  TTY_STATE=$(stty -g 2>/dev/null || echo "")
  stty -echo 2>/dev/null
fi

# ---------------------------------------------------------------- helpers -----
# Frames are assembled into $OUT in-process with printf -v. This is not a style
# choice: render_host mutates the eviction-detector state (PREV_MODELS, PREV_TTL,
# EVENTS) and the /api/show cache. Capturing it with $(...) would run it in a
# subshell and silently discard every one of those updates -- the detector would
# never fire and the cache would re-query a shared server on every poll.
emit() { local _s; printf -v _s "$@"; OUT+="$_s"; }

# All float work goes through awk; bc is not assumed to be installed.
fgt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a>b)}'; }   # a > b
flt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a<b)}'; }   # a < b

num() { awk -v v="${1:-0}" 'BEGIN{printf "%.2f", (v==""?0:v)}'; }

bar() {  # bar <used> <total> <width>
  local used="$1" total="$2" w="$3"
  if ! fgt "$total" 0; then printf '%*s' "$w" ""; return; fi
  local pct filled i out="" col="$C_GRN"
  pct=$(awk -v u="$used" -v t="$total" 'BEGIN{p=u/t; print (p>1?1:p)}')
  filled=$(awk -v p="$pct" -v w="$w" 'BEGIN{printf "%d", p*w}')
  [ "$filled" -gt "$w" ] && filled="$w"
  [ "$filled" -lt 0 ] && filled=0
  fgt "$pct" 0.75 && col=$C_YEL
  fgt "$pct" 0.92 && col=$C_RED
  for ((i=0;i<filled;i++)); do out+="█"; done
  for ((i=filled;i<w;i++)); do out+="░"; done
  printf '%s%s%s' "$col" "$out" "$C_RST"
}

# ------------------------------------------------------------- event log ------
# Ring buffer of state changes. This is where eviction thrash becomes visible:
# a snapshot cannot show it, only a diff between consecutive polls can.
EVENT_MAX=6
declare -a EVENTS=()
declare -A PREV_MODELS=()   # host -> space-separated resident model names
declare -A PREV_TTL=()      # "host|model" -> seconds of keep_alive left when last seen
declare -A SUSPECT_NAME=()  # host -> model that vanished early, awaiting confirmation
declare -A SUSPECT_AT=()    # host -> epoch seconds when that happened
# How long a suspected eviction stays open. A cold 33 GB MoE took ~70 s to become
# resident after displacing its predecessor, so the window must comfortably exceed
# that; 150 s covers a slower or busier host without being loose enough to blame an
# unrelated load minutes later.
SUSPECT_WINDOW=150

event() {  # event <colour> <text>
  EVENTS+=("$(date '+%H:%M:%S')|$1|$2")
  while [ "${#EVENTS[@]}" -gt "$EVENT_MAX" ]; do EVENTS=("${EVENTS[@]:1}"); done
}

# ------------------------------------------------- per-model config warnings ---
# /api/show is queried once per (host,model) and cached: the parameters do not
# change while a model is resident, and this must not add load to a shared box.
declare -A SHOW_CACHE=()

MW=""                      # set by model_warnings; read immediately after the call
model_warnings() {  # model_warnings <host> <model>  -> sets $MW
  local host="$1" model="$2" key="$1|$2"
  MW=""
  if [ -n "${SHOW_CACHE[$key]+x}" ]; then MW="${SHOW_CACHE[$key]}"; return; fi

  local params w=""
  params=$(curl -s --max-time 3 -X POST "http://$host:$PORT/api/show" \
             -H 'Content-Type: application/json' \
             -d "$(jq -nc --arg m "$model" '{model:$m}')" 2>/dev/null \
           | jq -r '.parameters // ""' 2>/dev/null)

  if [ -n "$params" ]; then
    local pp nc
    pp=$(printf '%s\n' "$params" | awk '$1=="presence_penalty"{print $2; exit}')
    nc=$(printf '%s\n' "$params" | awk '$1=="num_ctx"{print $2; exit}')
    if [ -n "$pp" ] && fgt "$pp" 0; then
      w+="presence_penalty=$pp (~35% slower — bake 0); "
    fi
    if [ -z "$nc" ]; then
      w+="no baked num_ctx (16k cap via /v1/messages, tool calls die past it); "
    fi
  fi
  SHOW_CACHE["$key"]="${w% }"
  MW="${SHOW_CACHE[$key]}"
}

# ------------------------------------------------------------- discovery ------
# Probe /api/version across the /24 of each already-known host. Parallel, short
# timeout, and it never writes to the servers. VRAM is not probed (see header).
discover() {
  local seeds="$1" nets="" ip net found=""
  for ip in $seeds; do
    net="${ip%.*}"
    case " $nets " in *" $net "*) ;; *) nets+=" $net" ;; esac
  done
  [ -z "$nets" ] && return 1

  local tmp; tmp=$(mktemp) || return 1
  for net in $nets; do
    for i in $(seq 1 254); do printf '%s.%s\n' "$net" "$i"; done
  done | xargs -P 64 -I{} sh -c \
      'curl -s --max-time 0.6 "http://{}:'"$PORT"'/api/version" \
         | grep -q version && echo {}' > "$tmp" 2>/dev/null

  found=$(sort -t. -k4 -n "$tmp" 2>/dev/null | tr '\n' ' ')
  rm -f "$tmp"
  if [ -n "${found// /}" ]; then
    HOSTS="${found% }"
    mkdir -p "$CFG_DIR" 2>/dev/null && printf '%s\n' "$HOSTS" > "$CACHE_HOSTS" 2>/dev/null
    event "$C_GRN" "discovery: $(echo "$HOSTS" | wc -w) host(s) — $HOSTS"
    return 0
  fi
  event "$C_YEL" "discovery found nothing; keeping previous host list"
  return 1
}

# Use a cached discovery result when the caller did not pin hosts explicitly.
if [ "$HOSTS_FROM_ARG" = "0" ] && [ -r "$CACHE_HOSTS" ]; then
  cached=$(tr -d '\n' < "$CACHE_HOSTS")
  [ -n "${cached// /}" ] && HOSTS="$cached"
fi
[ "$DO_DISCOVER" = "1" ] && discover "$HOSTS"

# --------------------------------------------------------------- rendering ----
render_host() {
  local host="$1" base="http://$1:$PORT"
  local ver
  ver=$(curl -s --max-time 1.5 "$base/api/version" 2>/dev/null | jq -r '.version // empty' 2>/dev/null)

  if [ -z "$ver" ]; then
    emit '  %s%-16s%s  %sUNREACHABLE%s %s(USB ethernet adapter up?)%s\n' \
      "$C_B" "$host" "$C_RST" "$C_RED" "$C_RST" "$C_DIM" "$C_RST"
    # A host that drops out should not look like a host whose models expired.
    if [ -n "${PREV_MODELS[$host]:-}" ]; then
      event "$C_RED" "$host went unreachable (was holding: ${PREV_MODELS[$host]})"
      PREV_MODELS[$host]=""
    fi
    return
  fi

  local t0 t1 lat ps
  t0=$(date +%s%3N)
  ps=$(curl -s --max-time 2.5 "$base/api/ps" 2>/dev/null)
  t1=$(date +%s%3N); lat=$(( t1 - t0 ))

  # Malformed or empty JSON must degrade to "0 models", never crash the loop.
  local n
  n=$(printf '%s' "$ps" | jq -r '.models | length' 2>/dev/null) || n=0
  [[ "$n" =~ ^[0-9]+$ ]] || n=0

  local total="${VRAM_TOTAL[$host]:-}"
  local used
  used=$(printf '%s' "$ps" | jq -r '[.models[]?.size_vram] | add // 0 | ./1e9' 2>/dev/null) || used=0
  used=$(num "$used")

  emit '  %s%-16s%s %sollama %-7s%s ' "$C_B" "$host" "$C_RST" "$C_DIM" "$ver" "$C_RST"
  if [ -n "$total" ] && [ "$SHOW_BARS" = "1" ]; then
    emit '%s ' "$(bar "$used" "$total" 22)"
    emit '%s%5.1f%s/%s GB ' "$C_CYA" "$used" "$C_RST" "$total"
  elif [ -n "$total" ]; then
    emit '%s%5.1f%s/%s GB ' "$C_CYA" "$used" "$C_RST" "$total"
  else
    emit '%s%5.1f GB%s/%s? ' "$C_CYA" "$used" "$C_RST" "$C_DIM$C_RST"
  fi
  local lcol=$C_DIM
  [ "$lat" -gt 400 ] && lcol=$C_YEL
  [ "$lat" -gt 1500 ] && lcol=$C_RED
  emit '%s%4dms%s\n' "$lcol" "$lat" "$C_RST"

  # ---- diff against the previous poll: eviction, expiry, arrival ----
  local now cur_names=""
  now=$(date +%s)
  if [ "$n" -gt 0 ]; then
    cur_names=$(printf '%s' "$ps" | jq -r '.models[]?.name' 2>/dev/null | tr '\n' ' ')
  fi
  local prev="${PREV_MODELS[$host]:-}"
  local appeared="" vanished="" nm
  for nm in $cur_names; do
    case " $prev " in *" $nm "*) ;; *) appeared+="$nm " ;; esac
  done
  for nm in $prev; do
    case " $cur_names " in *" $nm "*) ;; *) vanished+="$nm " ;; esac
  done

  # Eviction is NOT atomic, and that shaped this logic. Measured on .67: Ollama
  # unloaded the 9b at 14:09:40 and the replacing 33 GB MoE only became resident at
  # 14:09:55 -- 15 s later, and up to ~70 s for a cold MoE. So in the poll where a
  # model disappears there is usually nothing new to blame it on yet. A model that
  # vanishes with keep_alive still on the clock is therefore recorded as a *suspected*
  # eviction, and confirmed when a different model turns up within the window below.
  if [ -n "${vanished// /}" ]; then
    for nm in $vanished; do
      local ttl="${PREV_TTL["$host|$nm"]:-0}"
      if [ -n "${appeared// /}" ]; then
        event "$C_RED" "EVICTED $nm on $host → ${appeared% } (~70 s reload penalty)"
      elif [ "$ttl" -gt 30 ]; then
        event "$C_YEL" "$nm vanished on $host, ${ttl}s ttl left — suspected eviction, watching"
        SUSPECT_NAME[$host]="$nm"
        SUSPECT_AT[$host]="$now"
      else
        event "$C_DIM" "$nm unloaded on $host (keep_alive expired)"
      fi
    done
  elif [ -n "${appeared// /}" ] && [ -n "${prev// /}" ]; then
    event "$C_YEL" "$host now holds $n models — they cannot both fit; a reload is coming"
  elif [ -n "${appeared// /}" ]; then
    local sname="${SUSPECT_NAME[$host]:-}" sat="${SUSPECT_AT[$host]:-0}"
    if [ -n "$sname" ] && [ $(( now - sat )) -le "$SUSPECT_WINDOW" ]; then
      event "$C_RED" "EVICTED $sname on $host → ${appeared% } after $(( now - sat ))s (~70 s reload penalty)"
      SUSPECT_NAME[$host]=""
    else
      event "$C_GRN" "loaded ${appeared% } on $host"
    fi
  fi
  # A suspicion that never gets confirmed is dropped rather than left to mislabel a
  # later, unrelated load as an eviction.
  if [ -n "${SUSPECT_NAME[$host]:-}" ] && \
     [ $(( now - ${SUSPECT_AT[$host]:-0} )) -gt "$SUSPECT_WINDOW" ]; then
    SUSPECT_NAME[$host]=""
  fi
  PREV_MODELS[$host]="$cur_names"

  if [ "$n" = "0" ]; then
    emit '      %sidle — no model resident%s\n' "$C_DIM" "$C_RST"
    return
  fi

  # ---- per-model detail ----
  if [ "$SHOW_MODELS" = "1" ]; then
    local name vram size ctx exp quant psize
    while IFS=$'\t' read -r name vram size ctx exp quant psize; do
      [ -z "$name" ] && continue
      local split="" scol="$C_GRN"
      if flt "$vram" "$(awk -v s="$size" 'BEGIN{print s-0.05}')"; then
        split=" ⚠ SPLIT→CPU (5.3x slower)"; scol="$C_RED"
      fi

      local left="" lc="$C_DIM" secs=0
      if [ -n "$exp" ]; then
        local es
        es=$(date -d "$exp" +%s 2>/dev/null) || es=0
        if [ "$es" -gt 0 ]; then
          secs=$(( es - now ))
          if   [ "$secs" -lt 0 ]    ; then left="expired"
          elif [ "$secs" -lt 60 ]   ; then left="${secs}s"; lc="$C_YEL"
          elif [ "$secs" -lt 3600 ] ; then left="$(( secs/60 ))m$(( secs%60 ))s"
          else                            left="$(( secs/3600 ))h$(( (secs%3600)/60 ))m"
          fi
        fi
      fi
      [ "$secs" -lt 0 ] && secs=0
      PREV_TTL["$host|$name"]="$secs"

      emit '      %s%-30s%s %s%6s %-7s%s %s%5.2f/%-5.2f GB%s %sctx %-7s%s %sttl %-7s%s%s%s%s\n' \
        "$C_MAG" "$name" "$C_RST" \
        "$C_DIM" "$psize" "$quant" "$C_RST" \
        "$scol" "$vram" "$size" "$C_RST" \
        "$C_DIM" "$ctx" "$C_RST" \
        "$lc" "$left" "$C_RST" \
        "$scol" "$split" "$C_RST"

      if [ "$SHOW_WARN" = "1" ]; then
        model_warnings "$host" "$name"
        [ -n "$MW" ] && emit '        %s↳ %s%s\n' "$C_YEL" "$MW" "$C_RST"
      fi
    done < <(printf '%s' "$ps" | jq -r '.models[]? |
        [ .name, (.size_vram/1e9), (.size/1e9), (.context_length // 0),
          (.expires_at // ""), (.details.quantization_level // "?"),
          (.details.parameter_size // "?") ] | @tsv' 2>/dev/null)
  fi

  # ---- optional nvidia-smi over SSH ----
  if [ "$USE_SSH" = "1" ]; then
    local smi
    smi=$(timeout 2 ssh -o BatchMode=yes -o ConnectTimeout=1 "$host" \
      'nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw --format=csv,noheader,nounits' 2>/dev/null)
    if [ -n "$smi" ]; then
      while IFS=, read -r idx gname temp util mused mtotal pwr; do
        [ -z "$idx" ] && continue
        local tc=$C_GRN
        temp=$(echo "$temp" | xargs)
        [[ "$temp" =~ ^[0-9]+$ ]] && { [ "$temp" -ge 75 ] && tc=$C_YEL; [ "$temp" -ge 85 ] && tc=$C_RED; }
        emit '        %sGPU%s %s %s%s°C%s  %s%% util  %s/%s MiB  %sW\n' \
          "$C_DIM" "$(echo "$idx"|xargs)" "$(echo "$gname"|xargs)" \
          "$tc" "$temp" "$C_RST" \
          "$(echo "$util"|xargs)" "$(echo "$mused"|xargs)" \
          "$(echo "$mtotal"|xargs)" "$(echo "$pwr"|xargs)"
      done <<< "$smi"
    else
      emit '        %sssh/nvidia-smi unavailable (no key access)%s\n' "$C_DIM" "$C_RST"
    fi
  fi
}

help_overlay() {
  emit '  %s%sKEYS%s\n' "$C_B" "$C_REV" "$C_RST"
  emit '    %s- +%s  refresh faster / slower    %sp%s  pause/resume   %sq%s  quit\n' \
    "$C_B" "$C_RST" "$C_B" "$C_RST" "$C_B" "$C_RST"
  emit '    %sv%s    VRAM bars                  %sm%s  model detail   %sw%s  warnings\n' \
    "$C_B" "$C_RST" "$C_B" "$C_RST" "$C_B" "$C_RST"
  emit '    %se%s    event log                  %sd%s  re-discover    %ss%s  ssh/nvidia-smi\n' \
    "$C_B" "$C_RST" "$C_B" "$C_RST" "$C_B" "$C_RST"
  emit '    %sh ?%s  close this help\n' "$C_B" "$C_RST"
  emit '  %sWatched failure modes: eviction thrash (~70 s reload), split placement\n' "$C_DIM"
  emit '  (5.3x slower), missing baked num_ctx (16k cap, tool calls die),\n'
  emit '  presence_penalty != 0 (~35%% slower). See review2.md.%s\n' "$C_RST"
}

# ------------------------------------------------------------------- main ------
printf '\e[?25l'   # hide cursor
FIRST=1
while true; do
  INTERVAL="${INTERVALS[$IDX]}"
  OUT=""

  # Terminal geometry, refreshed every frame so a resize is picked up immediately.
  # Rows drive the clipping guard; columns size the header rule, which was
  # previously a hardcoded run of box characters and so was the wrong length at
  # every window size but one.
  if [ -t 1 ]; then
    read -r TERM_ROWS TERM_COLS < <( { stty size 2>/dev/null || echo "24 80"; } )
  else
    TERM_ROWS=24; TERM_COLS=80
  fi
  [[ "$TERM_ROWS" =~ ^[0-9]+$ ]] && [ "$TERM_ROWS" -gt 0 ] || TERM_ROWS=24
  [[ "$TERM_COLS" =~ ^[0-9]+$ ]] && [ "$TERM_COLS" -gt 20 ] || TERM_COLS=80

  # A paused view says how to resume, and any section that a persisted toggle has
  # switched off is named in the header. Without that, a toggle saved in a previous
  # session silently hides the most important data and looks like a broken tool.
  # The badge is kept as a plain twin as well: its *visible* width is needed to
  # size the rule, and the coloured version is full of escape bytes that ${#...}
  # would count as characters.
  hdr_state=""; hdr_plain=""
  if [ "$PAUSED" = "1" ]; then
    hdr_plain="   PAUSED — press p to resume "
    hdr_state="  ${C_YEL}${C_REV} PAUSED — press p to resume ${C_RST}"
  fi
  off=""
  [ "$SHOW_MODELS" = "0" ] && off+=" models:off(m)"
  [ "$SHOW_BARS"   = "0" ] && off+=" bars:off(v)"
  [ "$SHOW_WARN"   = "0" ] && off+=" warnings:off(w)"
  [ "$SHOW_EVENTS" = "0" ] && off+=" events:off(e)"
  [ -n "$off" ] && off="  ${C_YEL}hidden:${off}${C_RST}"

  # Rule stretched to the terminal width: ┌─ Ollama farm ──…──┐
  hdr_title='┌─ Ollama farm '
  rule_w=$(( TERM_COLS - ${#hdr_title} - ${#hdr_plain} - 1 ))
  [ "$rule_w" -lt 3 ] && rule_w=3
  printf -v hdr_rule '%*s' "$rule_w" ''
  hdr_rule="${hdr_rule// /─}"
  emit '%s%s%s┐%s%s\n' "$C_B" "$hdr_title" "$hdr_rule" "$C_RST" "$hdr_state"
  emit '  %s%s   every %ss%s   %s[+ slower  - faster  v m w e  d s  p pause  h help  q quit]%s%s\n\n' \
       "$C_DIM" "$(date '+%Y-%m-%d %H:%M:%S')" "$INTERVAL" "$C_RST" "$C_DIM" "$C_RST" "$off"

  if [ "$SHOW_HELP" = "1" ]; then
    help_overlay
    OUT+=$'\n'
  fi

  if [ "$PAUSED" = "0" ] || [ "$FIRST" = "1" ]; then
    # render_host appends to OUT directly and mutates the detector state, so it
    # must run in THIS shell. The body is sliced back out afterwards so a paused
    # frame can be redrawn without polling.
    mark="${#OUT}"
    for H in $HOSTS; do
      render_host "$H"
      OUT+=$'\n'
    done
    LAST_BODY="${OUT:$mark}"
    FIRST=0
  else
    OUT+="${LAST_BODY:-}"
  fi

  if [ "$SHOW_EVENTS" = "1" ] && [ "${#EVENTS[@]}" -gt 0 ]; then
    emit '  %sEVENTS%s\n' "$C_B" "$C_RST"
    for ev in "${EVENTS[@]}"; do
      ts="${ev%%|*}"; rest="${ev#*|}"; col="${rest%%|*}"; txt="${rest#*|}"
      emit '    %s%s%s %s%s%s\n' "$C_DIM" "$ts" "$C_RST" "$col" "$txt" "$C_RST"
    done
    OUT+=$'\n'
  fi

  if [ "$USE_SSH" = "0" ]; then
    emit '  %sGPU temp/util/power need nvidia-smi on the host — press s once key access exists.%s\n' \
         "$C_DIM" "$C_RST"
  fi

  # Frame painting. Two things are needed to stop the display corrupting, and the
  # first version had neither:
  #
  #   1. Every line must be terminated with \e[K (erase to end of line). Without it
  #      a short line leaves the tail of whatever longer line occupied that row in
  #      the previous frame -- which is what made the event list look overwritten,
  #      since event text varies in length frame to frame.
  #   2. The frame must not exceed the terminal height. If it does, the terminal
  #      scrolls, \e[H then no longer refers to the top of the frame, and every
  #      subsequent repaint lands one row off and smears.
  if [ -t 1 ]; then
    frame=$(printf '%s' "$OUT" | head -n $(( TERM_ROWS > 2 ? TERM_ROWS - 1 : 1 )) )
    nl_count=$(printf '%s\n' "$OUT" | wc -l)
    [ "$nl_count" -ge "$TERM_ROWS" ] && frame+=$'\n  \e[2m…frame clipped to terminal height\e[0m'
    printf '\e[H%s\e[J' "${frame//$'\n'/$'\e[K'$'\n'}"
  else
    printf '%s' "$OUT"
  fi

  # read doubles as the sleep, so keys stay responsive at any refresh rate.
  # A timeout returns non-zero; that is the normal path and must not abort.
  key=""
  if [ -t 0 ]; then
    read -rsn1 -t "$INTERVAL" key || true
  else
    sleep "$INTERVAL"
  fi

  case "$key" in
    # + and - act on the INTERVAL, matching btop: "+" makes the number bigger, so
    # the refresh gets slower. (The first version had these inverted.)
    +|=)  [ "$IDX" -lt $(( ${#INTERVALS[@]} - 1 )) ] && IDX=$((IDX+1)); save_config ;;
    -|_)  [ "$IDX" -gt 0 ] && IDX=$((IDX-1)); save_config ;;
    v|V)  SHOW_BARS=$((1-SHOW_BARS)); save_config ;;
    m|M)  SHOW_MODELS=$((1-SHOW_MODELS)); save_config ;;
    w|W)  SHOW_WARN=$((1-SHOW_WARN)); save_config ;;
    e|E)  SHOW_EVENTS=$((1-SHOW_EVENTS)); save_config ;;
    p|P)  PAUSED=$((1-PAUSED)) ;;
    h|H|\?) SHOW_HELP=$((1-SHOW_HELP)) ;;
    s|S)  USE_SSH=$((1-USE_SSH)) ;;
    d|D)  discover "$HOSTS" ;;
    q|Q)  cleanup ;;
  esac
done
