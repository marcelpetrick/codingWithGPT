# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the executable-line coverage ratio without rounding."""

import json
import sys

totals = json.load(sys.stdin)["totals"]
covered = totals["covered_lines"]
total = totals["num_statements"]
print(f"Executable lines covered: {covered}/{total}")
if not total or covered * 100 < total * 99:
    sys.exit("Executable-line coverage is below 99%")
