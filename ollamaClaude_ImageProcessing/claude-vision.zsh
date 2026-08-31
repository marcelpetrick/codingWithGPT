# Qwen3-VL 32B OCR shell for a 40 GB-class Ollama server.
typeset -g CLAUDE_VISION_DIR="${${(%):-%N}:A:h}"

claude-vision() {
  local H=${OLLAMA_VISION_HOST:-}
  local P=http://127.0.0.1:4748
  local M=qwen3-vl:32b-ctx49k
  local PROXY="$CLAUDE_VISION_DIR/anthropic_no_think_proxy.py"
  if [[ -z "$H" ]]; then
    echo 'claude-vision: set OLLAMA_VISION_HOST to the Ollama server URL.' >&2
    return 2
  fi
  if ! curl -fsS --max-time 2 "$P/health" 2>/dev/null | grep -q 'claude-vision-no-think'; then
    printf 'claude-vision: starting no-think proxy on 127.0.0.1:4748 ...' >&2
    nohup python3 "$PROXY" --listen 127.0.0.1 --port 4748 --upstream "$H" \
      </dev/null >>/tmp/claude-vision-proxy.log 2>&1 &!
    local i
    for i in {1..50}; do
      curl -fsS --max-time 1 "$P/health" 2>/dev/null | grep -q 'claude-vision-no-think' && break
      sleep 0.1
    done
    if ! curl -fsS --max-time 2 "$P/health" 2>/dev/null | grep -q 'claude-vision-no-think'; then
      printf ' FAILED\n' >&2
      echo "claude-vision: proxy did not start; see /tmp/claude-vision-proxy.log" >&2
      return 1
    fi
    printf ' ready\n' >&2
  fi
  printf 'claude-vision: warming %s on %s ...' "$M" "${H#http://}" >&2
  if curl -sf --max-time 600 "$H/api/generate" \
       -H 'Content-Type: application/json' \
       -d "{\"model\":\"$M\",\"prompt\":\"/no_think\\nready\",\"options\":{\"num_predict\":1},\"keep_alive\":\"2h\",\"stream\":false}" \
       >/dev/null 2>&1; then
    printf ' resident (2h)\n' >&2
  else
    printf ' FAILED\n' >&2
    echo "claude-vision: cannot reach $H or load $M." >&2
    return 1
  fi
  ANTHROPIC_AUTH_TOKEN=ollama \
  ANTHROPIC_BASE_URL="$P" \
  ANTHROPIC_API_KEY="" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="$M" \
  ANTHROPIC_DEFAULT_SONNET_MODEL="$M" \
  ANTHROPIC_DEFAULT_OPUS_MODEL="$M" \
  CLAUDE_CODE_MAX_CONTEXT_TOKENS=45000 \
  CLAUDE_CODE_MAX_OUTPUT_TOKENS=4096 \
  MAX_THINKING_TOKENS=0 \
    claude --model "$M" \
      --system-prompt $'/no_think\nYou are a precise vision and OCR assistant. Transcribe requested text exactly and describe only what is visible.' \
      --tools "" \
      "$@"
}
