# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn OCR lines into message candidates using the LinkedIn header pattern "Name  10:32 AM"."""

import re

from linkedin_reply_assistant.model import Direction, Message

TIME = r"(?:\d{1,2}[:.]\d{2}\s*(?:[AaPp]\.?\s?[Mm]\.?)?|yesterday|today|gestern|heute)"
HEADER = re.compile(
    rf"^(?P<sender>[^\d:]{{2,60}}?)\s*[·•|-]?\s*(?P<time>{TIME})\s*$", re.IGNORECASE
)


def split_messages(lines: list[str], owner_name: str) -> tuple[str | None, tuple[Message, ...]]:
    """Return (participant, messages). The participant is the first non-owner sender, or the
    first line (thread title) when no header is found."""
    messages: list[Message] = []
    sender: str | None = None
    time = ""
    body: list[str] = []

    def flush() -> None:
        if sender is not None and body:
            direction: Direction = "outgoing" if _same_person(sender, owner_name) else "incoming"
            messages.append(Message(sender, " ".join(body), time, direction))

    for line in lines:
        match = HEADER.match(line.strip())
        if match:
            flush()
            sender, time, body = match["sender"].strip(), match["time"], []
        elif sender is not None and line.strip():
            body.append(line.strip())
    flush()
    participant = next((m.sender for m in messages if m.direction == "incoming"), None)
    if participant is None and lines:
        participant = lines[0].strip() or None
    return participant, tuple(messages)


def _same_person(sender: str, owner: str) -> bool:
    owner = owner.strip().lower()
    return bool(owner) and sender.lower().split()[0] == owner.split()[0]
