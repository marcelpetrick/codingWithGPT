#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASKS_FILE="$SCRIPT_DIR/tasks.md"
LOG_FILE="$SCRIPT_DIR/watcher.log"
MODEL="qwen3.5:9b-ctx80k"
POLL_INTERVAL="${POLL_INTERVAL:-10}"

# Ollama backend settings (mirrors the claude-ol alias)
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://192.168.100.37:11434
export ANTHROPIC_API_KEY=""
# Force all claude instances (including any subagents) to use the Ollama model
export ANTHROPIC_MODEL="$MODEL"

# ANSI colors — empty when stdout is not a terminal
if [[ -t 1 ]]; then
    R='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'
    RED='\033[31m'; GRN='\033[32m'; YEL='\033[33m'; BLU='\033[34m'
else
    R=''; BOLD=''; DIM=''
    RED=''; GRN=''; YEL=''; BLU=''
fi

log() {
    local ts msg plain colored
    ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    msg="$*"
    plain="[$ts] $msg"
    case "$msg" in
        START*)     colored="${DIM}[$ts]${R} ${BOLD}${BLU}${msg}${R}" ;;
        DONE*)      colored="${DIM}[$ts]${R} ${BOLD}${GRN}${msg}${R}" ;;
        ERROR*)     colored="${DIM}[$ts]${R} ${BOLD}${RED}${msg}${R}" ;;
        *wall=*)    colored="${DIM}[$ts]${R} ${YEL}${msg}${R}"        ;;
        Watcher*)   colored="${DIM}[$ts]${R} ${BOLD}${msg}${R}"       ;;
        Cleaned*)   colored="${DIM}[$ts] ${msg}${R}"                  ;;
        *)          colored="${DIM}[$ts]${R} ${msg}"                  ;;
    esac
    echo "$plain" >> "$LOG_FILE"
    echo -e "$colored"
}

# Pretty-print stream-json from claude to the terminal.
# Raw JSON is handled upstream via tee — this only renders to stdout.
pretty_stream() {
    python3 -c '
import sys, json, os

R    = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
CYN  = "\033[36m"
YEL  = "\033[33m"
GRN  = "\033[32m"
RED  = "\033[31m"
BLU  = "\033[34m"

is_tty = os.isatty(sys.stdout.fileno())
def c(code, text):
    return code + text + R if is_tty else text

for raw in sys.stdin:
    raw = raw.strip()
    if not raw:
        continue
    try:
        obj = json.loads(raw)
        t   = obj.get("type", "")

        if t == "assistant":
            for block in obj.get("message", {}).get("content", []):
                bt = block.get("type", "")
                if bt == "text":
                    text = block.get("text", "").rstrip()
                    if text:
                        print(c(CYN, text), flush=True)
                elif bt == "tool_use":
                    name      = block.get("name", "?")
                    inp       = block.get("input", {})
                    first_key = next(iter(inp), "")
                    first_val = inp.get(first_key, "")
                    if isinstance(first_val, str) and len(first_val) > 100:
                        first_val = first_val[:97] + "..."
                    label = (first_key + "=" + repr(first_val)) if first_key else ""
                    print(c(YEL, "  -> " + name + "(" + label + ")"), flush=True)

        elif t == "user":
            for block in obj.get("message", {}).get("content", []):
                if block.get("type") == "tool_result":
                    is_error = block.get("is_error", False)
                    content  = block.get("content", "")
                    if isinstance(content, list):
                        text = " ".join(
                            b["text"] for b in content if b.get("type") == "text"
                        )
                    else:
                        text = str(content)
                    text = text.strip()[:300]
                    col  = RED if is_error else DIM
                    print(c(col, "  <- " + text), flush=True)

        elif t == "result":
            sub   = obj.get("subtype", "unknown")
            turns = obj.get("num_turns", "?")
            cost  = obj.get("total_cost_usd", 0)
            usage = obj.get("usage", {})
            in_t  = usage.get("input_tokens", "?")
            out_t = usage.get("output_tokens", "?")
            sep   = c(DIM, "-" * 60)
            st    = c(GRN, "success") if sub == "success" else c(RED, sub)
            print("")
            print(sep)
            print("  " + c(BOLD, "result:") + " " + st
                  + "  turns=" + c(BOLD, str(turns))
                  + "  tokens " + c(BOLD, "in=" + str(in_t) + " out=" + str(out_t))
                  + "  cost=" + c(BOLD, "$" + format(cost, ".4f")))
            print(sep + "\n", flush=True)

    except json.JSONDecodeError:
        print(raw, flush=True)
'
}

cleanup_workdir() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        log "Cleaned up: $dir"
    fi
}

process_repo() {
    local repo_url="$1"

    local repo_name
    repo_name=$(basename "$repo_url" .git)
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)

    local work_dir="$SCRIPT_DIR/workdir/${timestamp}_${repo_name}"
    local output_file="$SCRIPT_DIR/review_${repo_name}.md"
    local tmp_stream
    tmp_stream=$(mktemp)

    mkdir -p "$work_dir"

    log "START review: $repo_url"
    log "  workdir : $work_dir"
    log "  output  : $output_file"

    local t_start
    t_start=$(date +%s)

    # Run claude; tee raw stream-json to log and tmp_stream; pretty-print to terminal.
    # set +o errexit so a non-zero claude exit doesn't abort the script.
    local exit_code=0
    set +o errexit
    claude \
        --model "$MODEL" \
        --dangerously-skip-permissions \
        --max-turns 40 \
        --output-format stream-json \
        --verbose \
        --disallowed-tools "Agent" \
        -p "
You are an automated code reviewer. Execute all steps immediately without asking questions.

STRICT OUTPUT RULES — violating these ruins the report:
- Every field marked [MAX N words] must not exceed that limit. Stop. Move on.
- Do not pad, repeat, or elaborate beyond the word limit.
- Write the report file in one Write tool call, then stop.

## Task
Review: $repo_url

## Steps

1. Run: git clone --depth 1 $repo_url $work_dir/repo

2. Explore: list files, read key source files to understand the codebase.

3. Identify the 10 worst findings (security, bugs, architecture). Rank by severity.

4. Write the report to: $output_file

   Exact format — no deviations:

   # Code Review: $repo_name
   **Repository**: $repo_url
   **Reviewed**: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
   **Model**: $MODEL (Ollama)

   ## Summary
   [MAX 40 words: what the project does, overall risk level, biggest concern]

   ## Top 10 Findings

   ### 1. [title max 8 words] — CRITICAL|HIGH|MEDIUM|LOW
   **File**: path/to/file.ext:line
   **Description**: [MAX 25 words: what is wrong]
   **Impact**: [MAX 20 words: consequence]
   **Fix**: [MAX 20 words: recommendation]

   [repeat pattern exactly for findings 2 through 10]

   ## Quick Wins
   [3-5 bullet points, each MAX 15 words]

5. Print exactly: REVIEW COMPLETE: $output_file

Do not interact. Do not add extra text. Execute steps and terminate.
" 2>&1 | tee -a "$LOG_FILE" | tee "$tmp_stream" | pretty_stream
    exit_code=${PIPESTATUS[0]}
    set -o errexit

    local t_end
    t_end=$(date +%s)
    local wall_secs
    wall_secs=$(( t_end - t_start ))

    # Extract token/cost stats from the stream-json result event
    local stats_line in_tok out_tok cost_usd turns stats_summary
    stats_line=$(grep -m1 '"type":"result"' "$tmp_stream" 2>/dev/null || true)
    rm -f "$tmp_stream"

    if [[ -n "$stats_line" ]] && command -v jq &>/dev/null; then
        in_tok=$(  printf '%s' "$stats_line" | jq -r '.usage.input_tokens  // "?"')
        out_tok=$( printf '%s' "$stats_line" | jq -r '.usage.output_tokens // "?"')
        cost_usd=$(printf '%s' "$stats_line" | jq -r '.total_cost_usd      // "?"')
        turns=$(   printf '%s' "$stats_line" | jq -r '.num_turns           // "?"')
        stats_summary="wall=${wall_secs}s | turns=${turns} | tokens in=${in_tok} out=${out_tok} | cost=\$${cost_usd}"
    else
        in_tok="?"; out_tok="?"; cost_usd="?"; turns="?"
        stats_summary="wall=${wall_secs}s | tokens unavailable (Ollama did not report usage)"
    fi
    log "  $stats_summary"

    # Always clean up workdir — don't rely on the model doing it
    cleanup_workdir "$work_dir"

    if [[ $exit_code -ne 0 ]]; then
        log "ERROR: claude exited $exit_code for $repo_url"
        return
    fi

    # Verify the report was actually written (model may have narrated without acting)
    if [[ -f "$output_file" ]]; then
        # Inject stats as line 2 — python handles special chars that break sed
        python3 -c "
import sys
lines = open(sys.argv[1]).readlines()
lines.insert(1, '**Stats**: ' + sys.argv[2] + '\n')
open(sys.argv[1], 'w').writelines(lines)
" "$output_file" "$stats_summary"
        log "DONE: $output_file"
    else
        log "ERROR: claude exited 0 but no report was written for $repo_url — model likely narrated without calling tools"
    fi
}

main() {
    log "Watcher started (model=$MODEL, poll=${POLL_INTERVAL}s, tasks=$TASKS_FILE)"

    trap 'log "Watcher stopped."; exit 0' INT TERM

    while true; do
        if [[ -f "$TASKS_FILE" ]]; then
            local repo_url
            repo_url=$(grep -m1 '^[^#[:space:]]' "$TASKS_FILE" 2>/dev/null || true)

            if [[ -n "$repo_url" ]]; then
                # Remove that line atomically (grep -F = fixed string, not regex)
                local tmp
                tmp=$(mktemp)
                grep -Fv "$repo_url" "$TASKS_FILE" > "$tmp" || true
                mv "$tmp" "$TASKS_FILE"

                process_repo "$repo_url"
            fi
        fi

        sleep "$POLL_INTERVAL"
    done
}

main "$@"
