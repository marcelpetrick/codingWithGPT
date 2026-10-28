# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from linkedin_reply_assistant.config.loader import BackendConfig


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


@pytest.fixture
def config() -> BackendConfig:
    return make_config()
