# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Types shared by all backends."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.config.loader import BackendConfig

Purpose = Literal["reply", "vision"]


class BackendError(Exception):
    """A backend call failed. `reachable` is False when the endpoint itself is down."""

    def __init__(self, message: str, *, reachable: bool = True) -> None:
        super().__init__(message)
        self.reachable = reachable


@dataclass(frozen=True)
class Health:
    reachable: bool
    version: str | None = None
    models: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ChatRequest:
    system: str
    user: str
    images: tuple[bytes, ...] = ()
    json_output: bool = True
    temperature: float = 0.4


@dataclass(frozen=True)
class ChatResult:
    text: str
    backend: str
    label: str
    endpoint: str
    model: str
    duration_s: float
    fallback_reasons: tuple[str, ...] = field(default=())

    @property
    def fallback_used(self) -> bool:
        return bool(self.fallback_reasons)


class Backend(Protocol):
    config: BackendConfig

    def health(self) -> Health: ...

    def chat(self, model: str, request: ChatRequest, cancel: CancelToken) -> str: ...
