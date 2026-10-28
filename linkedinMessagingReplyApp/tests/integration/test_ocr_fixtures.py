# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real Tesseract on the rendered screenshot fixtures (§23.3). Tolerant compare, not byte-exact."""

import difflib

import pytest
import yaml
from PIL import Image

from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.extraction.base import ExtractionContext
from linkedin_reply_assistant.extraction.ocr import TesseractExtractor
from linkedin_reply_assistant.model import load_conversation
from tests.conftest import FIXTURES

INDEX = yaml.safe_load((FIXTURES / "screenshots" / "index.yaml").read_text())
# The conversation panel of the Capture Test Window, as a user would select it.
CONVERSATION_ROI = Roi(0.27, 0.0, 0.73, 0.84)
MIN_SIMILARITY = 0.9


@pytest.mark.parametrize("name", sorted(INDEX))
def test_ocr_fixture(name: str) -> None:
    meta = INDEX[name]
    conversation = load_conversation(FIXTURES / "messages" / f"{meta['messages']}.yaml")
    image = Image.open(FIXTURES / "screenshots" / f"{name}.png").convert("RGB")
    result = TesseractExtractor().extract(
        CONVERSATION_ROI.crop(image), ExtractionContext("Marcel", 55, 20)
    )
    incoming = " ".join(m.text for m in result.messages if m.direction == "incoming")
    similarity = difflib.SequenceMatcher(None, conversation.incoming_text(), incoming).ratio()
    assert similarity >= MIN_SIMILARITY, f"{name}: {similarity:.2f}\n{result.raw_text}"
    assert result.participant == conversation.participant
    assert result.language == conversation.language
    assert not result.needs_review, result.warnings
