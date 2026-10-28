# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Conversation data shared by extraction, classification, generation and the test harness."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

Direction = Literal["incoming", "outgoing", "unknown"]


@dataclass(frozen=True)
class Message:
    sender: str
    text: str
    time: str = ""
    direction: Direction = "unknown"


@dataclass(frozen=True)
class Conversation:
    participant: str
    messages: tuple[Message, ...]
    language: str = "en"
    expected_category: str | None = None
    rule: str | None = None
    forbidden_reply_patterns: tuple[str, ...] = field(default=())
    injection: bool = False

    def incoming_text(self) -> str:
        """The text the reply must answer: the incoming messages after the last outgoing one."""
        tail: list[str] = []
        for message in reversed(self.messages):
            if message.direction == "outgoing":
                break
            tail.append(message.text)
        return "\n".join(reversed(tail)) or "\n".join(m.text for m in self.messages)

    def transcript(self) -> str:
        return "\n".join(f"{m.sender}: {m.text}" for m in self.messages)


def load_conversation(path: Path) -> Conversation:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    messages = tuple(
        Message(
            sender=str(m["sender"]),
            text=str(m["text"]),
            time=str(m.get("time", "")),
            direction=m.get("direction", "unknown"),
        )
        for m in data["messages"]
    )
    return Conversation(
        participant=str(data["participant"]),
        messages=messages,
        language=str(data.get("language", "en")),
        expected_category=data.get("expected_category"),
        rule=data.get("rule"),
        forbidden_reply_patterns=tuple(data.get("forbidden_reply_patterns") or ()),
        injection=bool(data.get("injection", False)),
    )
