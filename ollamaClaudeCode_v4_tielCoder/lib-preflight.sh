# lib-preflight.sh — sourced by the shell harnesses. One job: prove the REMOTE
# Ollama server answers before any measurement starts.
#
# Why this exists (review.md R11). needle-v2.sh shipped with HOST=127.0.0.1.
# Run without --host it queried the laptop, every request came back empty, each
# rung was scored PARSE_FAIL and the baked-window probe fell back to 32768.
# Three rows of "results" that measured nothing, and they looked like a model
# that could not retrieve rather than a harness pointed at the wrong machine.
#
# A benchmark must fail loudly when its target is absent, never produce numbers.
# preflight() exits 2 with the URL and the reason instead of returning.
preflight() {
  local host="$1" port="$2" ver
  ver=$(curl -s -m 10 "http://${host}:${port}/api/version" 2>/dev/null \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])' 2>/dev/null)
  if [ -z "$ver" ]; then
    echo "PREFLIGHT FAILED: http://${host}:${port} did not answer /api/version." >&2
    echo "  - the servers are reachable only via the USB ethernet adapter (enp0s13f0u1u4)," >&2
    echo "    not wifi; check: ip -br addr show enp0s13f0u1u4" >&2
    echo "  - did you mean --host 192.168.100.67 ? (localhost has no Ollama here)" >&2
    exit 2
  fi
  printf 'preflight: %s:%s ollama %s\n' "$host" "$port" "$ver" >&2
}
