# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the backend manager from the configuration."""

from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.backends.ollama import OllamaBackend
from linkedin_reply_assistant.config.loader import BackendsConfig


def build_manager(config: BackendsConfig) -> BackendManager:
    backends = [OllamaBackend(entry) for entry in config.backends]
    return BackendManager(backends, config.health_cache_seconds)
