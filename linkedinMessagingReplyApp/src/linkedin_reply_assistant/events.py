# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Event logging without private content (§20.1).

`log_event("capture_succeeded", seq=3, size="900x560")` writes one line. Fields that can hold
LinkedIn content are redacted unless debug.log_message_text is enabled.
"""

import logging

LOGGER = logging.getLogger("linkedin_reply_assistant")
PRIVATE_FIELDS = {"text", "reply", "participant", "message", "draft", "extracted"}


class EventLog:
    def __init__(self, log_message_text: bool = False, logger: logging.Logger = LOGGER) -> None:
        self.log_message_text = log_message_text
        self._logger = logger

    def __call__(self, name: str, **fields: object) -> str:
        parts = [name]
        for key, value in fields.items():
            if key in PRIVATE_FIELDS and not self.log_message_text:
                value = f"<redacted {len(str(value))} chars>"
            parts.append(f"{key}={value}")
        line = " ".join(parts)
        self._logger.info(line)
        return line


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
