# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for metric helpers (REQ-UI-4)."""

from typing import Any

import pytest

from mrreview.metrics import overview, quantile, rate


def test_quantile() -> None:
    assert quantile([], 0.5) is None
    assert quantile([5.0], 0.9) == 5.0
    assert quantile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert quantile([4.0, 1.0, 3.0, 2.0], 0.75) == pytest.approx(3.25)


def test_rate_keeps_denominator() -> None:
    assert rate(1, 4) == {"num": 1, "den": 4, "value": 0.25}
    assert rate(0, 0) == {"num": 0, "den": 0, "value": None}


def f(**kw: Any) -> dict[str, Any]:
    base = {
        "t": "a",
        "act": "change_request",
        "outcome": "implemented",
        "ver": "direct",
        "cens": None,
        "tm": {"fr": ["o", 2.0, 1.0]},
    }
    return {**base, **kw}


def test_overview() -> None:
    ds = {
        "mrs": [{}, {}],
        "threads": [
            {"id": "a", "reason": "substantive", "resolved": True},
            {"id": "b", "reason": "routine_only", "resolved": False},
        ],
        "findings": [
            f(),
            f(ver="textual_only"),
            f(outcome="open", tm={"fr": ["p", 3.0]}),
            f(outcome="open", cens="recent", act="question", tm={"fr": ["o", 1.0, 3.0]}),
        ],
    }
    o = overview(ds)
    assert o["mrs"] == 2
    assert o["substantive_threads"] == 1
    assert o["actionable"] == 3
    assert o["verified_rate"] == {"num": 1, "den": 3, "value": 1 / 3}
    assert o["unresolved"] == 1
    assert o["resolved_without_code"] == 1
    assert o["median_first_response_biz_h"] == 1.0
    assert o["first_response_pending"] == 1
