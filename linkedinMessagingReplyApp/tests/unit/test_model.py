# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
from linkedin_reply_assistant.model import Conversation, Message, load_conversation
from tests.conftest import FIXTURES


def test_load_fixture() -> None:
    conversation = load_conversation(FIXTURES / "messages" / "prompt_injection_01.yaml")
    assert conversation.injection and conversation.expected_category == "sales_outreach"
    assert conversation.forbidden_reply_patterns


def test_incoming_text_after_last_outgoing() -> None:
    conversation = Conversation(
        "Ann",
        (
            Message("Ann", "old", direction="incoming"),
            Message("Me", "reply", direction="outgoing"),
            Message("Ann", "new 1", direction="incoming"),
            Message("Ann", "new 2", direction="incoming"),
        ),
    )
    assert conversation.incoming_text() == "new 1\nnew 2"
    assert conversation.transcript().startswith("Ann: old\nMe: reply")
    only_outgoing = Conversation("Ann", (Message("Me", "hi", direction="outgoing"),))
    assert only_outgoing.incoming_text() == "hi"
