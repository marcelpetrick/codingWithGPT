# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Insert into LinkedIn (§14.2): check the conversation, insert, verify. Never send."""

import re
from dataclasses import dataclass
from typing import Protocol

from linkedin_reply_assistant.browser_bridge.fingerprint import Identity, compare

CONVERSATION_CHANGED = "Conversation changed — recapture required."
INSERTED = "Inserted into LinkedIn. Review it there and press Send yourself."
NOT_VERIFIED = "The composer does not show the expected text. Nothing was sent; check LinkedIn."


class Transport(Protocol):
    def request(self, message: dict[str, object], timeout: float = 5.0) -> dict[str, object]: ...


@dataclass(frozen=True)
class InsertOutcome:
    ok: bool
    message: str
    identity: Identity | None = None
    needs_confirmation: bool = False


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class Inserter:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def identify(self) -> tuple[Identity | None, str]:
        answer = self._transport.request({"type": "identify"})
        if not answer.get("ok"):
            return None, str(answer.get("error", "the active tab is not a LinkedIn conversation"))
        return Identity(str(answer.get("title", "")), str(answer.get("url", ""))), ""

    def insert(self, text: str, participant: str | None, confirmed: bool = False) -> InsertOutcome:
        identity, error = self.identify()
        if identity is None:
            return InsertOutcome(False, error)
        verdict = compare(participant, identity)
        if verdict == "mismatch":
            return InsertOutcome(False, CONVERSATION_CHANGED, identity)
        if verdict == "unknown" and not confirmed:
            who = participant or "an unknown participant"
            return InsertOutcome(
                False,
                f"Cannot verify the conversation. Insert the draft for {who}?",
                identity,
                needs_confirmation=True,
            )
        answer = self._transport.request({"type": "insert", "text": text, "url": identity.url})
        if not answer.get("ok"):
            return InsertOutcome(False, str(answer.get("error", "insertion failed")), identity)
        if squash(text) not in squash(str(answer.get("readback", ""))):
            return InsertOutcome(False, NOT_VERIFIED, identity)
        return InsertOutcome(
            True, "Inserted into LinkedIn. Review it there and press Send yourself.", identity
        )
