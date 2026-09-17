#!/usr/bin/env bash
# provenance.sh — the reproducibility block: exactly what was measured, on what.
# Regenerate with ./provenance.sh > results/provenance.txt
set -uo pipefail
H="${1:-http://192.168.100.67:11434}"
echo "# v4 provenance — generated $(date -Is)"
echo
echo "## Inference server"
printf 'host            %s\n' "$H"
printf 'ollama          %s\n' "$(curl -s -m10 $H/api/version | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])')"
printf 'usable VRAM     35.56 GB (measured in v3 §19c; no API exposes it, no SSH to the box)\n'
printf 'reachable via   USB ethernet enp0s13f0u1u4 (192.168.100.0/24); wifi 10.x cannot see it\n'
echo
echo "## Models under test (digest = ollama manifest digest)"
curl -s -m20 $H/api/tags | python3 -c '
import sys,json
want=("Tiel","tiel","yber","ornith","north-mini","gemma4:26b","nemotron","qwen3.6:35b-a3b-q4_K_M-agentic","qwen3.8:27b-q4_K_M-ctx")
for m in sorted(json.load(sys.stdin)["models"],key=lambda m:m["name"]):
    if any(w in m["name"] for w in want):
        d=m.get("details",{})
        print("  %-62s %-18s %7.2f GB  %-8s %s"%(m["name"],m["digest"][:16],m["size"]/1e9,
              d.get("quantization_level"),d.get("parameter_size")))'
echo
echo "## Baked parameters of the two Tiel tags"
for M in "Tiel-Coder-35B-A3B-GGUF-Q5_K_XL-ctx262k:latest" "tiel-coder:35b-q5-ctx256k-agentic"; do
  echo "  $M"
  curl -s -m20 $H/api/show -d "{\"model\":\"$M\"}" | python3 -c '
import sys,json;d=json.load(sys.stdin)
for line in (d.get("parameters") or "").splitlines(): print("     ",line)
print("      capabilities:",d.get("capabilities"))'
done
echo
echo "## Client / harness"
printf 'claude code     %s\n' "$(claude --version 2>/dev/null)"
printf 'host python     %s, pytest %s\n' "$(python3 --version 2>&1 | cut -d' ' -f2)" "$(pytest --version 2>&1 | head -1 | awk '{print $2}')"
printf 'sandbox image   %s (python 3.11.2, pytest 7.2.1, claude 2.1.274)\n' "$(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' v4-cc-sandbox:latest 2>/dev/null | head -1)"
printf 'docker          %s\n' "$(docker version --format '{{.Server.Version}}' 2>/dev/null)"
printf 'repo commit     %s\n' "$(git rev-parse --short HEAD 2>/dev/null)"
echo
echo "## Laptop (the client; it does no inference)"
printf 'os              %s\n' "$(uname -sr)"
printf 'cpu             %s\n' "$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ //')"
printf 'ram             %s\n' "$(free -h | awk '/^Mem:/{print $2}')"
echo
echo "## Sampling / request settings used by the harness"
cat <<'NOTE'
  tokrate.sh      temperature 0, seed 42, think:false, num_predict 256, /api/chat
  agentic-test.sh /v1/messages, thinking disabled, max_tokens 4000, tag's own temperature (0.6)
  needle-v2.sh    temperature 0, think:false, num_predict 2048, num_ctx = min(words*2.4+8192, baked)
  vision-bench.py temperature 0, seed 42, think:false, num_predict 2048, AT the baked window
  cache-probe.py  /v1/messages, thinking disabled, 24k-word unique prompts
  cc-session*.sh  real Claude Code, CLAUDE_CODE_MAX_CONTEXT_TOKENS=200000, all four model
                  slots pinned to the tag, --permission-mode bypassPermissions
NOTE
