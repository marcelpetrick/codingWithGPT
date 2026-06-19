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
    local output_file="$SCRIPT_DIR/review_${timestamp}_${repo_name}.md"
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
        -p "
You are an automated code reviewer running in headless mode. Complete ALL steps without asking for confirmation. Do not ask clarifying questions — proceed immediately.

## Task
Review the repository: $repo_url

## Steps

1. Clone the repository into: $work_dir
   Use: git clone --depth 1 $repo_url $work_dir/repo

2. Explore the codebase:
   - Identify languages, frameworks, and dependencies
   - Note overall structure and entry points

3. Perform a thorough review focused on:
   - Security vulnerabilities (injection, auth flaws, secrets in code, insecure deps)
   - Architectural anti-patterns and design flaws
   - Critical bugs and data integrity issues
   - Dangerous or deprecated API usage

4. Select the 10 worst findings, ranked by severity.

5. Write the report to: $output_file

   Use this exact format:

   \`\`\`
   # Code Review: $repo_name
   **Repository**: $repo_url
   **Reviewed**: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
   **Model**: $MODEL (Ollama)

   ## Summary
   [2-3 sentences: what the project does, overall risk level, key concern]

   ## Top 10 Findings

   ### 1. [Short title] — CRITICAL|HIGH|MEDIUM|LOW
   **File**: path/to/file.ext:line
   **Description**: What is wrong and why it matters.
   **Impact**: What an attacker or bug could cause.
   **Fix**: Concrete recommendation.

   [repeat for findings 2-10]

   ## Quick Wins
   [Bullet list of easy, low-risk improvements worth mentioning]
   \`\`\`

6. After writing the report, delete $work_dir entirely to free disk space.

7. Print exactly: REVIEW COMPLETE: $output_file

Do not interact. Execute all steps in order and terminate.
" 2>&1 | tee -a "$LOG_FILE" | tee "$tmp_stream" | pretty_stream
    exit_code=${PIPESTATUS[0]}
    set -o errexit

    local t_end
    t_end=$(date +%s)
    local wall_secs
    wall_secs=$(( t_end - t_start ))

    # Extract token/cost stats from the stream-json result event
    local stats_line
    stats_line=$(grep -m1 '"type":"result"' "$tmp_stream" 2>/dev/null || true)
    rm -f "$tmp_stream"

    if [[ -n "$stats_line" ]] && command -v jq &>/dev/null; then
        local in_tok out_tok cost_usd turns
        in_tok=$(  printf '%s' "$stats_line" | jq -r '.usage.input_tokens  // "?"')
        out_tok=$( printf '%s' "$stats_line" | jq -r '.usage.output_tokens // "?"')
        cost_usd=$(printf '%s' "$stats_line" | jq -r '.total_cost_usd      // "?"')
        turns=$(   printf '%s' "$stats_line" | jq -r '.num_turns           // "?"')
        log "  wall=${wall_secs}s | turns=$turns | tokens in=$in_tok out=$out_tok | cost=\$$cost_usd"
    else
        log "  wall=${wall_secs}s (no usage stats — jq missing or Ollama did not report tokens)"
    fi

    # Always clean up workdir — don't rely on the model doing it
    cleanup_workdir "$work_dir"

    if [[ $exit_code -ne 0 ]]; then
        log "ERROR: claude exited $exit_code for $repo_url"
        return
    fi

    # Verify the report was actually written (model may have narrated without acting)
    if [[ -f "$output_file" ]]; then
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
