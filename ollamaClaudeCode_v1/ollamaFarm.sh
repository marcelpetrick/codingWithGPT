#!/usr/bin/env bash
# ollamaFarm.sh — live view of the Ollama servers on the local network.
#
# Refreshes at 1 Hz. Shows per server: reachability, version, which models are
# resident, how much VRAM they hold, whether they spilled to CPU, the context
# they were loaded with, when they expire, and whether the server is actually
# busy right now.
#
# Usage:
#   ./ollamaFarm.sh                 # 1 Hz, default hosts
#   ./ollamaFarm.sh -n 2            # every 2 s
#   ./ollamaFarm.sh -H 192.168.100.67,192.168.100.99
#   ./ollamaFarm.sh --ssh           # also pull nvidia-smi over SSH (needs keys)
#
# On GPU temperature: the Ollama HTTP API does not expose temperature, fan,
# power or GPU utilisation — it only reports model residency. Those counters
# live in nvidia-smi on the server itself. As of 2026-08-04 SSH to both hosts
# is refused (publickey,password), so the --ssh path is present but inert until
# key access is arranged. Everything else below is real API data.

set -uo pipefail

HOSTS="192.168.100.37 192.168.100.67"
INTERVAL=1
USE_SSH=0
PORT=11434

# Measured usable VRAM ceilings (see review.md). Used only to draw the bars.
# 0 = unknown, bar falls back to showing absolute numbers.
declare -A VRAM_TOTAL=( [192.168.100.37]=12.2 [192.168.100.67]=36.1 )

while [ $# -gt 0 ]; do
  case "$1" in
    -n|--interval) INTERVAL="$2"; shift 2 ;;
    -H|--hosts)    HOSTS=$(echo "$2" | tr ',' ' '); shift 2 ;;
    -p|--port)     PORT="$2"; shift 2 ;;
    --ssh)         USE_SSH=1; shift ;;
    -h|--help)     sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

C_RST=$'\e[0m'; C_DIM=$'\e[2m'; C_B=$'\e[1m'
C_GRN=$'\e[32m'; C_YEL=$'\e[33m'; C_RED=$'\e[31m'; C_CYA=$'\e[36m'; C_MAG=$'\e[35m'

cleanup() { printf '\e[?25h\e[0m\n'; exit 0; }
trap cleanup INT TERM

# remember previous eval totals so we can tell "loaded" from "actually working"
declare -A PREV_SIG
declare -A BUSY_SINCE

bar() {  # bar <used> <total> <width>
  local used="$1" total="$2" w="$3"
  if [ "$(echo "$total <= 0" | bc)" = "1" ]; then printf '%*s' "$w" ""; return; fi
  local pct filled i out=""
  pct=$(echo "scale=4; $used/$total" | bc)
  filled=$(echo "scale=0; $pct*$w/1" | bc)
  [ "$filled" -gt "$w" ] && filled=$w
  [ "$filled" -lt 0 ] && filled=0
  local col=$C_GRN
  [ "$(echo "$pct > 0.75" | bc)" = "1" ] && col=$C_YEL
  [ "$(echo "$pct > 0.92" | bc)" = "1" ] && col=$C_RED
  for ((i=0;i<filled;i++)); do out+="█"; done
  for ((i=filled;i<w;i++)); do out+="░"; done
  printf '%s%s%s' "$col" "$out" "$C_RST"
}

render_host() {
  local host="$1" base="http://$1:$PORT"
  local ver
  ver=$(curl -s --max-time 1.5 "$base/api/version" | jq -r '.version // empty' 2>/dev/null)

  if [ -z "$ver" ]; then
    printf '  %s%-16s%s  %sUNREACHABLE%s\n' "$C_B" "$host" "$C_RST" "$C_RED" "$C_RST"
    return
  fi

  # latency probe doubles as a crude busy indicator
  local t0 t1 lat
  t0=$(date +%s%3N)
  local ps
  ps=$(curl -s --max-time 2 "$base/api/ps")
  t1=$(date +%s%3N); lat=$(( t1 - t0 ))

  local n
  n=$(echo "$ps" | jq -r '.models | length' 2>/dev/null || echo 0)

  local total="${VRAM_TOTAL[$host]:-0}"
  local used
  used=$(echo "$ps" | jq -r '[.models[]?.size_vram] | add // 0 | ./1e9' 2>/dev/null)
  used=$(printf '%.2f' "$used" 2>/dev/null || echo 0)

  printf '  %s%-16s%s %sollama %-7s%s ' "$C_B" "$host" "$C_RST" "$C_DIM" "$ver" "$C_RST"
  if [ "$(echo "$total > 0" | bc)" = "1" ]; then
    printf '%s ' "$(bar "$used" "$total" 22)"
    printf '%s%5.1f%s/%s GB VRAM ' "$C_CYA" "$used" "$C_RST" "$total"
  else
    printf '%s%5.1f GB VRAM%s ' "$C_CYA" "$used" "$C_RST"
  fi
  printf '%s%3dms%s\n' "$C_DIM" "$lat" "$C_RST"

  if [ "$n" = "0" ] || [ -z "$n" ]; then
    printf '      %sidle — no model resident%s\n' "$C_DIM" "$C_RST"
    return
  fi

  # per-model detail
  echo "$ps" | jq -r '.models[]? |
      [ .name,
        (.size_vram/1e9),
        (.size/1e9),
        (.context_length // 0),
        (.expires_at // ""),
        (.details.quantization_level // "?"),
        (.details.parameter_size // "?")
      ] | @tsv' 2>/dev/null |
  while IFS=$'\t' read -r name vram size ctx exp quant psize; do
      local split="" scol="$C_GRN"
      if [ "$(echo "$vram < $size - 0.05" | bc)" = "1" ]; then
        split=" SPLIT→CPU"; scol="$C_RED"
      fi
      # seconds until keep_alive expiry
      local left=""
      if [ -n "$exp" ]; then
        local es now
        es=$(date -d "$exp" +%s 2>/dev/null || echo 0)
        now=$(date +%s)
        if [ "$es" -gt 0 ]; then
          local d=$(( es - now ))
          if   [ "$d" -lt 0 ]     ; then left="expired"
          elif [ "$d" -lt 3600 ]  ; then left="$(( d/60 ))m$(( d%60 ))s"
          else                          left="$(( d/3600 ))h"
          fi
        fi
      fi
      printf '      %s%-26s%s %s%6s %-8s%s %s%5.2f/%-5.2f GB%s%s%s%s ctx %s%-7s%s ttl %s%s%s\n' \
        "$C_MAG" "$name" "$C_RST" \
        "$C_DIM" "$psize" "$quant" "$C_RST" \
        "$scol" "$vram" "$size" "$C_RST" "$scol" "$split" "$C_RST" \
        "$C_DIM" "$ctx" "$C_RST" "$C_DIM" "$left" "$C_RST"
  done

  if [ "$USE_SSH" = "1" ]; then
    local smi
    smi=$(timeout 2 ssh -o BatchMode=yes -o ConnectTimeout=1 "$host" \
      'nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw --format=csv,noheader,nounits' 2>/dev/null)
    if [ -n "$smi" ]; then
      echo "$smi" | while IFS=, read -r idx gname temp util mused mtotal pwr; do
        printf '      %sGPU%s %s%-22s%s %s°C  %s%% util  %s/%s MiB  %sW%s\n' \
          "$C_DIM" "$idx" "$C_YEL" "$(echo "$gname"|xargs)" "$C_RST" \
          "$(echo "$temp"|xargs)" "$(echo "$util"|xargs)" \
          "$(echo "$mused"|xargs)" "$(echo "$mtotal"|xargs)" "$(echo "$pwr"|xargs)" "$C_RST"
      done
    else
      printf '      %sssh/nvidia-smi unavailable (no key access)%s\n' "$C_DIM" "$C_RST"
    fi
  fi
}

printf '\e[?25l'   # hide cursor
while true; do
  OUT=""
  OUT+=$(printf '%s┌─ Ollama farm ─────────────────────────────────────────────────────────────┐%s\n' "$C_B" "$C_RST")
  OUT+=$'\n'
  OUT+=$(printf '  %s%s   refresh %ss   ctrl-c to quit%s\n' "$C_DIM" "$(date '+%Y-%m-%d %H:%M:%S')" "$INTERVAL" "$C_RST")
  OUT+=$'\n\n'
  for H in $HOSTS; do
    OUT+=$(render_host "$H")
    OUT+=$'\n\n'
  done
  if [ "$USE_SSH" = "0" ]; then
    OUT+=$(printf '  %sGPU temp/util/power need nvidia-smi on the host — rerun with --ssh once key access exists.%s' "$C_DIM" "$C_RST")
    OUT+=$'\n'
  fi
  printf '\e[H\e[2J%s' "$OUT"
  sleep "$INTERVAL"
done
