# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unified-diff helpers: the new-side lines of a file in one MR version."""

from __future__ import annotations

import re

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def new_side_lines(diff: str) -> dict[int, str]:
    """Map new-file line numbers to text for every added or context line in the diff."""
    out: dict[int, str] = {}
    line_no = 0
    in_hunk = False
    for raw in diff.splitlines():
        m = _HUNK.match(raw)
        if m:
            line_no = int(m.group(1))
            in_hunk = True
            continue
        if not in_hunk or raw.startswith("\\"):
            continue
        if raw.startswith("-"):
            continue
        out[line_no] = raw[1:] if raw[:1] in ("+", " ") else raw
        line_no += 1
    return out


def window(lines: dict[int, str], center: int, radius: int) -> dict[int, str]:
    """The lines from center - radius to center + radius that exist in lines."""
    return {n: lines[n] for n in range(center - radius, center + radius + 1) if n in lines}
