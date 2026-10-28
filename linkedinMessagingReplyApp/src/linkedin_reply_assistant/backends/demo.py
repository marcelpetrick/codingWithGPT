# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic offline backend for `--demo`, `lra selftest`, the Docker smoke test and UI tests.

It is not an AI. It answers the classifier and reply prompts with fixed, well-formed JSON, so
the whole pipeline can run without Ollama. The UI shows it as backend "demo".
"""

import json
import re

from linkedin_reply_assistant.backends.base import ChatRequest, Health
from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.config.loader import BackendConfig

DEMO_CONFIG = BackendConfig(
    name="demo",
    label="offline demo, no AI",
    url="http://demo.invalid",
    priority=0,
    connect_timeout_ms=1,
    request_timeout_s=1.0,
    reply_models=("demo",),
    vision_models=(),
)
KEYWORDS = [
    ("meeting_request", r"\b(meeting|meet|call)\b"),
    ("event_invitation", r"\b(event|meetup|webinar|conference|invited?)\b"),
    ("partnership_request", r"\b(partnership|cooperation|collaborate)\b"),
    ("recruiting", r"\b(position|role|stelle|job)\b"),
    ("substantive_professional", r"\?"),
]
REPLIES = {
    "en": {
        "sales_decline": "Hi, thank you for reaching out and for explaining your offer. "
        "I have no need for it at the moment, so I will pass.",
        "manual_review": "Hi, thank you for your message.",
    },
    "de": {
        "sales_decline": "Hallo, danke für Ihre Nachricht und die Vorstellung Ihres Angebots. "
        "Aktuell habe ich keinen Bedarf.",
        "manual_review": "Hallo, danke für Ihre Nachricht.",
    },
}
DEFAULT = {
    "en": "Hi, thank you for your message. Great to be in touch!",
    "de": "Hallo, danke für Ihre Nachricht!",
}
POLICY = {
    "sales_outreach": "sales_decline",
    "lead_generation": "sales_decline",
    "partnership_request": "sales_decline",
    "unknown_manual_review": "manual_review",
}


class DemoBackend:
    config = DEMO_CONFIG

    def health(self) -> Health:
        return Health(True, "demo", ("demo",))

    def chat(self, model: str, request: ChatRequest, cancel: CancelToken) -> str:
        cancel.raise_if_cancelled()
        if request.system.startswith("Classify"):
            category = next(
                (c for c, pattern in KEYWORDS if re.search(pattern, request.user, re.IGNORECASE)),
                "friendly_connection",
            )
            return json.dumps({"category": category, "confidence": 0.6, "reason_short": "demo"})
        category = _field(request.system, "category") or "unknown_manual_review"
        language = "de" if 'Reply in the language "German"' in request.system else "en"
        reply = REPLIES[language].get(POLICY.get(category, ""), DEFAULT[language])
        sign_off = re.search(r'add the sign-off exactly: "([^"]*)"', request.system)
        if sign_off:
            reply = f"{reply}\n\n{sign_off.group(1)}"
        manual = category == "unknown_manual_review"
        answer = {"reply": reply, "category": category, "language": language}
        return json.dumps(answer | {"needs_manual_review": manual})


def _field(system: str, name: str) -> str | None:
    match = re.search(rf'"{name}": "([a-z_]+)"', system)
    return match.group(1) if match else None
