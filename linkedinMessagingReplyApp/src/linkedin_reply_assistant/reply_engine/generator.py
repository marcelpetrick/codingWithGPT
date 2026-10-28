# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Draft generation with the structured output contract of §11.4. Only `reply` reaches LinkedIn."""

import re
from dataclasses import dataclass

from linkedin_reply_assistant.backends.base import ChatRequest, ChatResult
from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.config.loader import Config
from linkedin_reply_assistant.jsonout import JsonOutputError, parse_object
from linkedin_reply_assistant.reply_engine.classifier import Classification, Classifier
from linkedin_reply_assistant.reply_engine.prompts import CLOSE, OPEN, reply_prompt


class GenerationError(Exception):
    """The model gave no usable draft."""


@dataclass(frozen=True)
class Draft:
    reply: str
    classification: Classification
    language: str
    needs_manual_review: bool
    warnings: tuple[str, ...]
    result: ChatResult


def choose_language(config: Config, detected: str) -> tuple[str, list[str]]:
    """Mirror the sender language if supported (§19); otherwise use the fixed language and warn."""
    policy = config.app.language
    if policy.policy == "fixed":
        return policy.fixed, []
    if detected in policy.supported:
        return detected, []
    if detected == "und":
        return policy.fixed, []
    return policy.fixed, [f"language '{detected}' is not supported: manual review"]


def leak_warnings(reply: str, config: Config) -> list[str]:
    """Output guard: the draft must not echo policy, markers or endpoints (§12)."""
    found = []
    lowered = reply.lower()
    if OPEN.lower() in lowered or CLOSE.lower() in lowered or "message_data" in lowered:
        found.append("draft contains data markers")
    for backend in config.backends.backends:
        host = re.sub(r"^https?://", "", backend.url).split(":")[0]
        if host and host in reply:
            found.append("draft contains a backend address")
    if "system prompt" in lowered or "allowed facts" in lowered:
        found.append("draft talks about its instructions")
    return found


class ReplyGenerator:
    def __init__(self, config: Config, manager: BackendManager) -> None:
        self.config = config
        self.manager = manager
        self.classifier = Classifier(config, manager)

    def generate(
        self,
        incoming_text: str,
        transcript: str,
        detected_language: str,
        cancel: CancelToken,
        category_override: str | None = None,
    ) -> Draft:
        if category_override:
            classification = self.classifier.override(category_override)
        else:
            classification = self.classifier.classify(incoming_text, cancel)
        cancel.raise_if_cancelled()
        language, warnings = choose_language(self.config, detected_language)
        system, user = reply_prompt(self.config, classification.category, language, transcript)
        result = self.manager.chat("reply", ChatRequest(system, user), cancel)
        try:
            data = parse_object(result.text)
        except JsonOutputError as exc:
            raise GenerationError(f"the model answer has no reply: {exc}") from exc
        reply = str(data.get("reply", "")).strip()
        if not reply:
            raise GenerationError("the model returned an empty reply")
        warnings += leak_warnings(reply, self.config)
        limit = self.config.reply_rules.categories[classification.category].max_words
        if len(reply.split()) > limit * 1.5:
            warnings.append(f"draft is long ({len(reply.split())} words, limit {limit})")
        manual = (
            bool(data.get("needs_manual_review"))
            or classification.reply_policy == "manual_review"
            or bool(warnings)
        )
        return Draft(reply, classification, language, manual, tuple(warnings), result)
