#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Check the experiment record without contacting the shared server.
set -euo pipefail
cd "$(dirname "$0")"
bash -n localPipeline.sh pull-model.sh after-pull.sh
python3 -m py_compile residency.py test_residency.py
python3 -m coverage run --source=residency -m unittest -v test_residency
python3 -m coverage report --fail-under=95
shellcheck localPipeline.sh pull-model.sh after-pull.sh
test -s KOLIBRI_Q3_RUN.md
grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' VERSION
git diff --check -- KOLIBRI_Q3_RUN.md VERSION localPipeline.sh
