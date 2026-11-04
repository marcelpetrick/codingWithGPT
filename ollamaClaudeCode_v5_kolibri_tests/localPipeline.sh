#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Check the experiment record without contacting the shared server.
set -euo pipefail
cd "$(dirname "$0")"
bash -n localPipeline.sh pull-model.sh after-pull.sh after-residency.sh agentic-smoke.sh gate-reliability.sh needle-probe.sh speed-probe.sh near-limit.sh agentic-battery.sh coding-bench.sh deep-probe.sh fidelity-retry.sh
python3 -m py_compile residency.py refine.py test_residency.py test_refine.py test_pull.py
python3 -m coverage run --source=residency,refine -m unittest -v test_residency test_refine test_pull
python3 -m coverage report --fail-under=95
shellcheck localPipeline.sh pull-model.sh after-pull.sh after-residency.sh agentic-smoke.sh gate-reliability.sh needle-probe.sh speed-probe.sh near-limit.sh agentic-battery.sh coding-bench.sh deep-probe.sh fidelity-retry.sh
test -s KOLIBRI_Q3_RUN.md
grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' VERSION
git diff --check -- KOLIBRI_Q3_RUN.md VERSION localPipeline.sh
