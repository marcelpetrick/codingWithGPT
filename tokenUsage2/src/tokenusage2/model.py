# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Plain data types shared by discovery, ingestion, aggregation and rendering."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Tool(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


@dataclass(frozen=True, slots=True)
class Account:
    """One local installation with its own history, e.g. one ``CODEX_HOME``."""

    id: str
    tool: Tool
    home: Path
    label: str
    identity: str | None = None
    plan: str | None = None
    origin: str = "default"


@dataclass(frozen=True, slots=True)
class Usage:
    """Token counts of one request, normalised across tools.

    ``input`` is fresh (uncached) input; ``reasoning`` is a subset of
    ``output``; ``unsplit`` holds retained totals whose split is unknown.
    """

    input: int = 0
    cache_read: int = 0
    cache_write: int = 0
    output: int = 0
    reasoning: int = 0
    unsplit: int = 0

    @property
    def fresh(self) -> int:
        return self.input + self.output

    @property
    def total(self) -> int:
        return self.input + self.cache_read + self.cache_write + self.output + self.unsplit


@dataclass(frozen=True, slots=True)
class Event:
    """One billed request (or one retained daily total when ``usage.unsplit``)."""

    key: str
    ts: float
    tool: Tool
    account: str
    model: str
    backend: str
    project: str
    session: str
    usage: Usage


@dataclass(frozen=True, slots=True)
class QuotaWindow:
    """A provider rate-limit window as last observed on disk."""

    account: str
    window: str
    used_percent: float
    resets_at: float | None
    observed_at: float
    source: str
    plan: str | None = None
