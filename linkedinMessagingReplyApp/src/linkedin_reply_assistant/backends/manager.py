# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Backend manager: priority order, cached health, model selection, visible fallback (§13)."""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from linkedin_reply_assistant.backends.base import (
    Backend,
    BackendError,
    ChatRequest,
    ChatResult,
    Health,
    Purpose,
)
from linkedin_reply_assistant.cancel import CancelToken


class NoBackendError(BackendError):
    """No backend could serve the request. `reasons` names the failure per backend."""

    def __init__(self, reasons: Sequence[str]) -> None:
        super().__init__("all AI backends unavailable: " + "; ".join(reasons), reachable=False)
        self.reasons = tuple(reasons)


@dataclass(frozen=True)
class Selection:
    backend: Backend
    model: str


class BackendManager:
    def __init__(
        self,
        backends: Sequence[Backend],
        health_cache_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.backends = sorted(backends, key=lambda b: b.config.priority)
        self._ttl = health_cache_seconds
        self._clock = clock
        self._cache: dict[str, tuple[float, Health]] = {}

    def health(self, backend: Backend, *, refresh: bool = False) -> Health:
        """Return cached health. A dead endpoint is probed again after the cache period."""
        now = self._clock()
        cached = self._cache.get(backend.config.name)
        if not refresh and cached and now - cached[0] < self._ttl:
            return cached[1]
        health = backend.health()
        self._cache[backend.config.name] = (now, health)
        return health

    def mark_down(self, backend: Backend, reason: str) -> None:
        self._cache[backend.config.name] = (self._clock(), Health(False, error=reason))

    def health_report(self, *, refresh: bool = False) -> list[tuple[Backend, Health]]:
        return [(b, self.health(b, refresh=refresh)) for b in self.backends]

    @staticmethod
    def preferred_models(backend: Backend, purpose: Purpose) -> tuple[str, ...]:
        config = backend.config
        return config.reply_models if purpose == "reply" else config.vision_models

    def candidates(self, purpose: Purpose) -> tuple[list[Selection], list[str]]:
        """Usable backends with an installed preferred model, by priority, plus skip reasons."""
        selections: list[Selection] = []
        reasons: list[str] = []
        for backend in self.backends:
            preferred = self.preferred_models(backend, purpose)
            if not preferred:
                reasons.append(f"{backend.config.name}: no {purpose} model configured")
                continue
            health = self.health(backend)
            if not health.reachable:
                reasons.append(f"{backend.config.name}: {health.error}")
                continue
            model = next((m for m in preferred if m in health.models), None)
            if model is None:
                reasons.append(f"{backend.config.name}: none of {list(preferred)} installed")
                continue
            selections.append(Selection(backend, model))
        return selections, reasons

    def chat(self, purpose: Purpose, request: ChatRequest, cancel: CancelToken) -> ChatResult:
        """Run the request on the first usable backend. Fall back on failure and say why."""
        selections, reasons = self.candidates(purpose)
        skipped = list(reasons)
        for selection in selections:
            cancel.raise_if_cancelled()
            backend = selection.backend
            start = self._clock()
            try:
                text = backend.chat(selection.model, request, cancel)
            except BackendError as exc:
                if not exc.reachable:
                    self.mark_down(backend, str(exc))
                skipped.append(f"{backend.config.name}: {exc}")
                continue
            # Only reasons from higher-priority backends count as fallback.
            fallback = tuple(r for r in skipped if self._priority_of(r) < backend.config.priority)
            return ChatResult(
                text=text,
                backend=backend.config.name,
                label=backend.config.label,
                endpoint=backend.config.url,
                model=selection.model,
                duration_s=self._clock() - start,
                fallback_reasons=fallback,
            )
        raise NoBackendError(skipped or ["no backend configured"])

    def _priority_of(self, reason: str) -> int:
        name = reason.split(":", 1)[0]
        return next(b.config.priority for b in self.backends if b.config.name == name)
