#!/usr/bin/env bash
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
# While any chain driver runs, regenerate the README comparison and commit it every INTERVAL seconds.
set -uo pipefail
cd "$(dirname "$0")" || exit 1
interval=${INTERVAL:-1200}
say() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*"; }
refresh() {
  ./updateComparison.sh > /dev/null || { say "update failed"; return; }
  git add -- README.md comparison
  if git diff --cached --quiet -- README.md comparison; then say "no change"; return; fi
  for _ in 1 2 3 4 5; do
    if git commit -q -m "docs: refresh the step-by-step comparison from the run data" -- README.md comparison; then say "committed"; return; fi
    sleep 3
  done
  say "commit failed"
}
# shellcheck disable=SC2009 # pgrep returned nothing inside a tool shell once; ps is reliable here.
while ps -eo args | grep -qE '^bash (recreate-101/scripts/codex-chain.sh|.*comfy-seq)|^node recreate-101/scripts/comfy-chain.mjs'; do
  refresh
  sleep "$interval"
done
refresh
say "all chains ended"
