#!/usr/bin/env bash
# setup.sh -- install the upstream terminal-bench harness and pre-pull the dataset.
# Idempotent; safe to re-run. Nothing here touches the shared box.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"; cd "$HERE"

VENV="${TB_VENV:-$HERE/tb-venv}"
DATASET="terminal-bench-core==0.1.1"

command -v uv >/dev/null || { echo "uv not found"; exit 1; }
docker compose version >/dev/null 2>&1 || {
  echo "docker compose plugin missing. On Manjaro:  sudo pacman -S docker-compose docker-buildx"; exit 1; }

echo "=== venv + harness ==="
[ -d "$VENV" ] || uv venv "$VENV" --python 3.12
uv pip install --python "$VENV/bin/python" --quiet terminal-bench
"$VENV/bin/tb" --help >/dev/null

echo "=== dataset ==="
"$VENV/bin/tb" datasets download -d "$DATASET"

echo "=== self-check: the ORACLE must score 100% on hello-world ==="
# The oracle runs each task's reference solution. If it does not pass, the
# harness/docker/compose plumbing is broken and no model number would mean
# anything (harness §0: a measurement that cannot fail loudly is not a
# measurement). This costs no model time.
"$VENV/bin/tb" run -d "$DATASET" -t hello-world -a oracle \
  --output-path "$HERE/runs" --run-id "selfcheck-oracle" 2>&1 | tail -5

acc=$(python3 -c "import json;print(json.load(open('$HERE/runs/selfcheck-oracle/results.json'))['accuracy'])")
[ "$acc" = "1.0" ] || { echo "ORACLE SELF-CHECK FAILED (accuracy=$acc) -- fix the harness before running models"; exit 3; }
echo "oracle self-check OK"
echo "SETUP-DONE -- now: ./GO_official_tb.sh"
