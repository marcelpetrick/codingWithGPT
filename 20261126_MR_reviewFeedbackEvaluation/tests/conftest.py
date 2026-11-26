# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared fixtures."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from mrreview import db


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    c = db.connect(tmp_path / "test.sqlite3")
    yield c
    c.close()
