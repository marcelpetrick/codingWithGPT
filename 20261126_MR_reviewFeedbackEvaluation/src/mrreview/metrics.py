# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Aggregate metrics in Python, used for tests and as a cross-check of the dashboard (REQ-UI-4).

Every rate is returned with its numerator and denominator, never as a bare percentage.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

CHANGE_OUTCOMES = frozenset({"implemented", "alternative_implemented", "partially_implemented"})
MIN_SAMPLE = 8


def quantile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolated quantile (the same method as the dashboard). None when empty."""
    if not values:
        return None
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def rate(num: int, den: int) -> dict[str, Any]:
    return {"num": num, "den": den, "value": (num / den) if den else None}


def per_thread(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The first finding of each thread. Thread-level times are counted once per thread."""
    seen: set[str] = set()
    out = []
    for f in findings:
        if f["t"] not in seen:
            seen.add(f["t"])
            out.append(f)
    return out


def overview(ds: dict[str, Any]) -> dict[str, Any]:
    """The overview numbers for the whole dataset (no filter)."""
    threads = ds["threads"]
    findings = ds["findings"]
    by_id = {t["id"]: t for t in threads}
    actionable = [f for f in findings if f["act"] == "change_request"]
    verified = [f for f in actionable if f["outcome"] in CHANGE_OUTCOMES and f["ver"] == "direct"]
    unresolved = [f for f in findings if f["outcome"] == "open" and not f["cens"]]
    unknown = [f for f in findings if f["outcome"] == "unknown"]
    claimed_no_code = [
        f
        for f in findings
        if by_id[f["t"]]["resolved"]
        and f["outcome"] in CHANGE_OUTCOMES
        and f["ver"] == "textual_only"
    ]
    first = per_thread(findings)
    fr = [f["tm"]["fr"][2] for f in first if f["tm"]["fr"][0] == "o"]
    return {
        "mrs": len(ds["mrs"]),
        "substantive_threads": sum(
            1 for t in threads if t.get("sub", t["reason"] == "substantive")
        ),
        "findings": len(findings),
        "actionable": len(actionable),
        "verified_rate": rate(len(verified), len(actionable)),
        "unresolved": len(unresolved),
        "unknown": len(unknown),
        "resolved_without_code": len(claimed_no_code),
        "median_first_response_biz_h": quantile(fr, 0.5),
        "first_response_n": len(fr),
        "first_response_pending": sum(1 for f in first if f["tm"]["fr"][0] == "p"),
    }
