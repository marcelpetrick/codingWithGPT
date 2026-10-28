# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Message classification: rules from reply_rules.yaml first, the model second (§10)."""

import re
from dataclasses import dataclass

from linkedin_reply_assistant.backends.base import ChatRequest
from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.config.loader import (
    CATEGORIES,
    UNKNOWN_CATEGORY,
    ClassificationRule,
    Config,
)
from linkedin_reply_assistant.jsonout import JsonOutputError, parse_object
from linkedin_reply_assistant.reply_engine.prompts import classifier_prompt

MIN_WORDS = 3


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    reason_short: str
    reply_policy: str
    source: str  # "rule:<id>", "model", "override", "too short", "unparsable"


def rule_hits(rule: ClassificationRule, text: str) -> int:
    lowered = text.lower()
    return sum(
        1 for keyword in rule.keywords if re.search(rf"\b{re.escape(keyword.lower())}\b", lowered)
    )


class Classifier:
    def __init__(self, config: Config, manager: BackendManager) -> None:
        self._config = config
        self._manager = manager

    def _make(self, category: str, confidence: float, reason: str, source: str) -> Classification:
        policy = self._config.reply_rules.categories[category].policy
        return Classification(category, confidence, reason, policy, source)

    def override(self, category: str) -> Classification:
        if category not in CATEGORIES:
            raise ValueError(f"unknown category {category}")
        return self._make(category, 1.0, "chosen by the user", "override")

    def by_rules(self, text: str) -> Classification | None:
        if len(text.split()) < MIN_WORDS:
            return self._make(UNKNOWN_CATEGORY, 1.0, "not enough text", "too short")
        for rule in self._config.reply_rules.rules:
            hits = rule_hits(rule, text)
            if hits >= rule.min_hits:
                reason = f"{hits} keyword(s) of rule {rule.id}"
                return self._make(rule.category, 0.9, reason, f"rule:{rule.id}")
        return None

    def classify(self, text: str, cancel: CancelToken) -> Classification:
        """Rules first; the model only for the ambiguous rest. BackendError propagates."""
        ruled = self.by_rules(text)
        if ruled is not None:
            return ruled
        system, user = classifier_prompt(self._config, text)
        result = self._manager.chat("reply", ChatRequest(system, user, temperature=0.0), cancel)
        try:
            data = parse_object(result.text)
        except JsonOutputError:
            return self._make(UNKNOWN_CATEGORY, 0.0, "model answer unreadable", "unparsable")
        category = str(data.get("category", ""))
        if category not in CATEGORIES:
            return self._make(UNKNOWN_CATEGORY, 0.0, f"unknown category '{category}'", "unparsable")
        try:
            confidence = min(1.0, max(0.0, float(data.get("confidence", 0.5))))
        except TypeError, ValueError:
            confidence = 0.5
        reason = str(data.get("reason_short", ""))[:120]
        return self._make(category, confidence, reason, "model")
