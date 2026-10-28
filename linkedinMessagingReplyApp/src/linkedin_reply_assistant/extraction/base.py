# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Common extractor interface (§9.1)."""

from dataclasses import dataclass, field
from typing import Protocol

from PIL import Image

from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.model import Message


class ExtractionError(Exception):
    """The extractor could not run (missing engine, backend down)."""


@dataclass(frozen=True)
class ExtractionContext:
    owner_name: str
    min_confidence: float
    min_characters: int
    cancel: CancelToken = field(default_factory=CancelToken)


@dataclass(frozen=True)
class ExtractionResult:
    raw_text: str
    messages: tuple[Message, ...]
    participant: str | None
    confidence: float  # 0..1
    language: str
    warnings: tuple[str, ...]
    extractor: str
    detail: str = ""  # for example "network-ollama / qwen3.6" for the vision extractor

    @property
    def needs_review(self) -> bool:
        return bool(self.warnings)


class Extractor(Protocol):
    name: str

    def extract(self, image: Image.Image, context: ExtractionContext) -> ExtractionResult: ...
