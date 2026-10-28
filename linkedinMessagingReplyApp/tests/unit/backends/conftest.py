# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from linkedin_reply_assistant.config.loader import BackendConfig
from tests.fakes import make_config


@pytest.fixture
def config() -> BackendConfig:
    return make_config()
