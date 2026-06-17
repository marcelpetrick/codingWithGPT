#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

cd "$SCRIPT_DIR"

echo "==> Creating virtual environment"
python3 -m venv "$VENV_DIR"

echo "==> Activating virtual environment"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "==> Installing dev dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r requirements-dev.txt

echo "==> mypy"
python3 -m mypy --strict boldemort.py

echo "==> flake8"
python3 -m flake8 boldemort.py tests/ --max-line-length=88

echo "==> pytest"
python3 -m pytest tests/ -v

echo ""
echo "All checks passed."
