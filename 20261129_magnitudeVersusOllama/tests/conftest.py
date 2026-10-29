# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures: a running fake engine."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from fake_engine import FakeEngine  # noqa: E402


@pytest.fixture
def fake() -> Iterator[FakeEngine]:
    with FakeEngine() as engine:
        yield engine
