#!/usr/bin/env bash
# publish_q8.sh -- P7: upload the merged Q8_0 (the card's recommended precision) as an A/B arm.
# Q8_0 is 28.6 GB, so only a 65536 window fits the box's ~35.5 GB (the card's own llama.cpp window).
# Run only after build.sh says BUILD-DONE (the merged file must be complete). Idempotent.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; BASE=http://192.168.100.67:11434
F=/var/tmp/v6/Qwen3.8-27B-Q8_0.gguf; TAG=qwen3.8-pi:27b-q8-ctx64k-nothink; LOG="$HERE/results/build.log"
export NO_PROXY="192.168.100.67,${NO_PROXY:-}" no_proxy="192.168.100.67,${no_proxy:-}"
[ -e /var/tmp/v6/.merged ] || { echo "not merged yet" >&2; exit 1; }
say () { printf '[%s] %s\n' "$(date +%T)" "$*" | tee -a "$LOG"; }
sha="$(sha256sum "$F" | cut -d' ' -f1)"; say "$TAG: blob sha256:$sha"
[ "$(curl -s -o /dev/null -w '%{http_code}' -I "$BASE/api/blobs/sha256:$sha")" = 200 ] || { say "$TAG: upload"; curl -sf -T "$F" -X POST "$BASE/api/blobs/sha256:$sha" >/dev/null; }
curl -sf -m 1800 "$BASE/api/create" -d "{\"model\":\"$TAG\",\"files\":{\"model.gguf\":\"sha256:$sha\"},\"renderer\":\"qwen3.8\",\"parser\":\"qwen3-coder\",\"parameters\":{\"num_ctx\":65536,\"temperature\":0.8,\"top_p\":0.95,\"top_k\":20,\"min_p\":0,\"presence_penalty\":0,\"repeat_penalty\":1},\"stream\":false}" | tee -a "$LOG"; echo
say "Q8-PUBLISHED"
