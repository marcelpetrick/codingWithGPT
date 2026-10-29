# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fixed decision rule of PLAN.md, as code.

"Clearly faster" = median at least 25% higher and min-max ranges that do not overlap.
Everything else is a tie. Quality: a pass-count difference of 2 or fewer is a tie.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

MIN_GAIN = 0.25
MIN_N = 5
QUALITY_TIE = 2


@dataclass(frozen=True)
class Summary:
    """Median and range of one metric for one arm in one cell."""

    n: int
    median: float
    low: float
    high: float


def summarize(values: list[float]) -> Summary:
    """Return n, median, min and max. An empty list gives n = 0 and zeros."""
    if not values:
        return Summary(0, 0.0, 0.0, 0.0)
    return Summary(len(values), statistics.median(values), min(values), max(values))


def speed_verdict(a: Summary, b: Summary) -> str:
    """Compare arm a with arm b on a higher-is-better metric.

    Return "a faster", "b faster", "tie", or "too few runs" when an arm has n < MIN_N.
    """
    if a.n < MIN_N or b.n < MIN_N:
        return "too few runs"
    if a.median >= b.median * (1 + MIN_GAIN) and a.low > b.high:
        return "a faster"
    if b.median >= a.median * (1 + MIN_GAIN) and b.low > a.high:
        return "b faster"
    return "tie"


def ratio(a: Summary, b: Summary) -> float:
    """Return median(a) / median(b), or 0 when b has no data."""
    return a.median / b.median if b.median else 0.0


def quality_verdict(passed_a: int, passed_b: int) -> str:
    """Compare pass counts of workload C. A difference of QUALITY_TIE or less is a tie."""
    if passed_a - passed_b > QUALITY_TIE:
        return "a better"
    if passed_b - passed_a > QUALITY_TIE:
        return "b better"
    return "tie"
