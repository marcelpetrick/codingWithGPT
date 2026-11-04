#!/usr/bin/env bash
# Check the experiment record without contacting the shared server.
set -euo pipefail
cd "$(dirname "$0")"
bash -n localPipeline.sh pull-model.sh
test -s KOLIBRI_Q3_RUN.md
grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' VERSION
git diff --check -- KOLIBRI_Q3_RUN.md VERSION localPipeline.sh
