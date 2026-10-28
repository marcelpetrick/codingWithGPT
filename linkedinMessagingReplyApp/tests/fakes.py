# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared test doubles."""

from collections.abc import Callable

from linkedin_reply_assistant.backends.base import BackendError, ChatRequest, Health
from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.config.loader import BackendConfig

Answer = str | BackendError | Callable[[ChatRequest], str]


def make_config(name: str = "net", priority: int = 10, **kw: object) -> BackendConfig:
    values: dict[str, object] = {
        "name": name,
        "label": f"{name} label",
        "url": f"http://{name}:11434",
        "priority": priority,
        "connect_timeout_ms": 100,
        "request_timeout_s": 5.0,
        "reply_models": ("big:1", "small:1"),
        "vision_models": ("eye:1",),
    }
    values.update(kw)
    return BackendConfig(**values)  # type: ignore[arg-type]


class FakeBackend:
    def __init__(self, config: BackendConfig, health: Health, answer: Answer = "ok") -> None:
        self.config = config
        self._health = health
        self.answer = answer
        self.probes = 0
        self.calls: list[str] = []
        self.requests: list[ChatRequest] = []

    def health(self) -> Health:
        self.probes += 1
        return self._health

    def chat(self, model: str, request: ChatRequest, cancel: CancelToken) -> str:
        self.calls.append(model)
        self.requests.append(request)
        if isinstance(self.answer, BackendError):
            raise self.answer
        if callable(self.answer):
            return self.answer(request)
        return self.answer


UP = Health(True, "0.40", ("big:1", "small:1", "eye:1"))


def fake_manager(answer: Answer) -> tuple[BackendManager, FakeBackend]:
    backend = FakeBackend(make_config(), UP, answer)
    return BackendManager([backend], 30), backend
