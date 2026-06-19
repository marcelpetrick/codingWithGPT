#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASKS_FILE="$SCRIPT_DIR/tasks.md"
LOG_FILE="$SCRIPT_DIR/watcher.log"
MODEL="qwen3.5:9b-ctx80k (Ollama)"
POLL_INTERVAL="${POLL_INTERVAL:-10}"

# Ollama backend settings (mirrors the claude-ol alias)
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://192.168.100.37:11434
export ANTHROPIC_API_KEY=""

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$LOG_FILE"
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

    # Derive a safe name from the URL
    local repo_name
    repo_name=$(basename "$repo_url" .git)
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)

    local work_dir="$SCRIPT_DIR/workdir/${timestamp}_${repo_name}"
    local output_file="$SCRIPT_DIR/review_${timestamp}_${repo_name}.md"

    mkdir -p "$work_dir"

    log "START review: $repo_url"
    log "  workdir : $work_dir"
    log "  output  : $output_file"

    # Run claude in non-interactive mode; clean up workdir even if claude fails
    if claude \
        --model qwen3.5:9b-ctx80k \
        --dangerously-skip-permissions \
        --max-turns 40 \
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
   **Model**: $MODEL

   ## Summary
   [2-3 sentences: what the project does, overall risk level, key concern]

   ## Top 10 Findings

   ### 1. [Short title] — CRITICAL|HIGH|MEDIUM|LOW
   **File**: path/to/file.ext:line
   **Description**: What is wrong and why it matters.
   **Impact**: What an attacker or bug could cause.
   **Fix**: Concrete recommendation.

   [repeat for findings 2–10]

   ## Quick Wins
   [Bullet list of easy, low-risk improvements worth mentioning]
   \`\`\`

6. After writing the report, delete $work_dir entirely to free disk space.

7. Print exactly: REVIEW COMPLETE: $output_file

Do not interact. Execute all steps in order and terminate.
" 2>&1 | tee -a "$LOG_FILE"
    local exit_code=$?

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

    # Trap SIGINT/SIGTERM for clean shutdown
    trap 'log "Watcher stopped."; exit 0' INT TERM

    while true; do
        if [[ -f "$TASKS_FILE" ]]; then
            # Read first non-blank, non-comment line
            repo_url=$(grep -m1 '^[^#[:space:]]' "$TASKS_FILE" 2>/dev/null || true)

            if [[ -n "$repo_url" ]]; then
                # Remove that line from tasks.md atomically
                tmp=$(mktemp)
                grep -v "^${repo_url}$" "$TASKS_FILE" > "$tmp" || true
                mv "$tmp" "$TASKS_FILE"

                process_repo "$repo_url"
            fi
        fi

        sleep "$POLL_INTERVAL"
    done
}

main "$@"
