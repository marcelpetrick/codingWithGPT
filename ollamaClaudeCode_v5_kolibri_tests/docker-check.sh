#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Build and smoke-test the dashboard image on an ephemeral local port.
set -euo pipefail
cd "$(dirname "$0")"
image='kolibri-dashboard:local-check'
container=''
cleanup() { if [[ -n "$container" ]]; then docker rm -f "$container" >/dev/null 2>&1 || true; fi; }
trap cleanup EXIT
docker build --build-arg "APP_VERSION=$(cat VERSION)" -f Dockerfile -t "$image" ..
container=$(docker run -d --read-only --cap-drop ALL --security-opt no-new-privileges -p 127.0.0.1::8080 "$image")
port=$(docker port "$container" 8080/tcp | python3 -c 'import sys; print(int(sys.stdin.read().strip().rsplit(":",1)[1]))')
body=''
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if body=$(curl --noproxy '*' -fsS -m 2 "http://127.0.0.1:$port/dashboard.html"); then break; fi
  sleep 1
done
[[ "$body" == *'Kolibri Q3 benchmark'* && "$body" == *'Cold throughput'* ]] || { echo 'Dashboard HTTP check failed.' >&2; exit 1; }
curl --noproxy '*' -fsS -m 5 "http://127.0.0.1:$port/KOLIBRI_Q3_RUN.md" >/dev/null
curl --noproxy '*' -fsS -m 5 "http://127.0.0.1:$port/ollamaClaudeCode_v4_tielCoder/dashboard.html" >/dev/null
