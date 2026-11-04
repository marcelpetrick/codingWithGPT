#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# Check the experiment record without contacting the shared server.
set -euo pipefail
cd "$(dirname "$0")"
bash -n localPipeline.sh pull-model.sh after-pull.sh after-residency.sh agentic-smoke.sh gate-reliability.sh needle-probe.sh speed-probe.sh near-limit.sh agentic-battery.sh coding-bench.sh deep-probe.sh fidelity-retry.sh thinking-retry.sh bilingual-probe.sh reasoning-arm.sh raw-diagnostic.sh native-tool-probe.sh parser-arm.sh
python3 -m ruff check --select F .
python3 -m ruff format --check .
python3 -m py_compile residency.py refine.py bilingual.py test_bilingual.py make_dashboard.py dashboard_watch.py test_dashboard.py test_dashboard_watch.py test_residency.py test_refine.py test_pull.py test_fixture_baseline.py test_coding_patch.py test_gate_safety.py test_needle_guard.py
python3 -m coverage run --source=residency,refine,bilingual,make_dashboard,dashboard_watch -m unittest -v test_residency test_refine test_pull test_fixture_baseline test_coding_patch test_gate_safety test_needle_guard test_dashboard test_dashboard_watch test_bilingual
python3 -m coverage report --fail-under=95
shellcheck localPipeline.sh pull-model.sh after-pull.sh after-residency.sh agentic-smoke.sh gate-reliability.sh needle-probe.sh speed-probe.sh near-limit.sh agentic-battery.sh coding-bench.sh deep-probe.sh fidelity-retry.sh thinking-retry.sh bilingual-probe.sh reasoning-arm.sh raw-diagnostic.sh native-tool-probe.sh parser-arm.sh
test -s KOLIBRI_Q3_RUN.md
grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' VERSION
git diff --check -- KOLIBRI_Q3_RUN.md VERSION localPipeline.sh
