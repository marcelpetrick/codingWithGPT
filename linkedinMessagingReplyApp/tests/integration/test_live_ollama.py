# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Live reply quality on the real Ollama backends (§23.5). Off by default: LIVE_OLLAMA=1.

Checks the categories and the forbidden patterns of every message fixture with the configured models.
"""

import os
import re
from pathlib import Path

import pytest

from linkedin_reply_assistant.backends.factory import build_manager
from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.config.loader import load_config
from linkedin_reply_assistant.model import load_conversation
from linkedin_reply_assistant.reply_engine.generator import ReplyGenerator
from tests.conftest import FIXTURES

pytestmark = [
    pytest.mark.live_ollama,
    pytest.mark.skipif(os.environ.get("LIVE_OLLAMA") != "1", reason="set LIVE_OLLAMA=1"),
]
FILES = sorted((FIXTURES / "messages").glob("*.yaml"))


@pytest.fixture(scope="module")
def generator(tmp_path_factory: pytest.TempPathFactory) -> ReplyGenerator:
    config = load_config(Path(os.environ.get("LRA_CONFIG_DIR", tmp_path_factory.mktemp("c"))))
    return ReplyGenerator(config, build_manager(config.backends))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_live_reply(generator: ReplyGenerator, path: Path) -> None:
    conversation = load_conversation(path)
    draft = generator.generate(
        conversation.incoming_text(),
        conversation.transcript(),
        conversation.language,
        CancelToken(),
    )
    print(
        f"\n[{path.stem}] {draft.classification.category} via {draft.result.backend}/"
        f"{draft.result.model} {draft.result.duration_s:.1f}s\n{draft.reply}"
    )
    for pattern in conversation.forbidden_reply_patterns:
        assert not re.search(pattern, draft.reply, re.IGNORECASE), pattern
    assert draft.classification.category == conversation.expected_category
