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


@dataclass(slots=True)
class Usage:
    """Token counts of one request, normalised across tools.

    Not frozen on purpose — a warm start builds ~90k of these and the frozen
    constructor is 3.4x slower — but treated as immutable everywhere.

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


@dataclass(slots=True)
class Event:
    """One billed request (or one retained daily total when ``usage.unsplit``).

    ``route`` is what the log itself says about the provider — ``"anthropic"``
    when Anthropic's API answered a Claude Code request, the Codex
    ``model_provider``, the OpenCode ``providerID``. The display label (an
    Ollama host, a proxy) is resolved from it when drawing, never stored.
    """

    key: str
    ts: float
    tool: Tool
    account: str
    model: str
    route: str
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
