# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The ruleset: an ordered list of rules, first match wins (vision.md §2.3).

A rule says *when* it applies and *what* the draft should do. The last rule must be a catch-all, so
every item gets a draft. Loading fails loudly on any unknown key: a typo must never silently turn a
rule into a catch-all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from typing import Any, Literal, cast

import yaml

Kind = Literal["message", "invitation"]
Action = Literal["decline", "reply", "draft_only", "ignore"]

ACTIONS: frozenset[str] = frozenset({"decline", "reply", "draft_only", "ignore"})
KINDS: frozenset[str] = frozenset({"message", "invitation"})
RULE_KEYS: frozenset[str] = frozenset({"id", "when", "action", "prompt", "tone", "examples"})
WHEN_KEYS: frozenset[str] = frozenset(
    {"kind", "category", "keywords", "sender_title", "language", "has_profile"}
)


class RulesError(ValueError):
    """The ruleset file is invalid. The message names the rule and the problem."""


@dataclass(frozen=True)
class Item:
    """One pending thing to answer: a message thread or a connect request."""

    kind: Kind
    text: str
    sender_name: str = ""
    sender_title: str = ""
    category: str | None = None
    language: str | None = None
    has_profile: bool = False


@dataclass(frozen=True)
class Example:
    """A few-shot example: an incoming text and the reply the owner really sent."""

    incoming: str
    reply: str


@dataclass(frozen=True)
class Condition:
    """All set fields must match. An empty condition matches everything."""

    kind: Kind | None = None
    category: str | None = None
    keywords: tuple[str, ...] = ()
    sender_title: tuple[str, ...] = ()
    language: str | None = None
    has_profile: bool | None = None

    @property
    def is_catch_all(self) -> bool:
        return self == Condition()

    def matches(self, item: Item) -> bool:
        if self.kind is not None and item.kind != self.kind:
            return False
        if self.category is not None and item.category != self.category:
            return False
        if self.language is not None and item.language != self.language:
            return False
        if self.has_profile is not None and item.has_profile != self.has_profile:
            return False
        if self.keywords and not _contains_any(item.text, self.keywords):
            return False
        return not (self.sender_title and not _contains_any(item.sender_title, self.sender_title))


@dataclass(frozen=True)
class Rule:
    id: str
    when: Condition
    action: Action
    prompt: str
    tone: str = ""
    examples: tuple[Example, ...] = field(default=())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(needle.casefold() in lowered for needle in needles)


def first_match(rules: list[Rule], item: Item) -> Rule:
    """Return the first rule whose condition matches. A valid ruleset always has one."""
    for rule in rules:
        if rule.when.matches(item):
            return rule
    raise RulesError("no rule matched; the ruleset has no catch-all")


def load_rules(text: str) -> list[Rule]:
    """Parse and validate a YAML ruleset."""
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RulesError(f"not valid YAML: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise RulesError("the ruleset must be a non-empty list of rules")
    rules = [_parse_rule(entry, index) for index, entry in enumerate(raw, start=1)]
    ids = [rule.id for rule in rules]
    duplicates = sorted({rule_id for rule_id in ids if ids.count(rule_id) > 1})
    if duplicates:
        raise RulesError(f"duplicate rule ids: {', '.join(duplicates)}")
    if not rules[-1].when.is_catch_all:
        raise RulesError(f"the last rule '{rules[-1].id}' must be a catch-all (when: {{}})")
    for rule in rules[:-1]:
        if rule.when.is_catch_all:
            raise RulesError(f"rule '{rule.id}' is a catch-all, so the rules after it never run")
    return rules


def load_default_rules() -> list[Rule]:
    """The ruleset shipped with the package (reply_desk/data/rules.yaml)."""
    text = resources.files("reply_desk").joinpath("data/rules.yaml").read_text(encoding="utf-8")
    return load_rules(text)


def _parse_rule(entry: object, index: int) -> Rule:
    if not isinstance(entry, dict):
        raise RulesError(f"rule #{index} is not a mapping")
    data = cast(dict[str, Any], entry)
    name = str(data.get("id") or f"#{index}")
    _reject_unknown(data, RULE_KEYS, f"rule '{name}'")
    for key in ("id", "action", "prompt"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise RulesError(f"rule '{name}': '{key}' is required and must be a text")
    if data["action"] not in ACTIONS:
        raise RulesError(
            f"rule '{name}': action '{data['action']}' is not one of {sorted(ACTIONS)}"
        )
    return Rule(
        id=data["id"],
        when=_parse_condition(data.get("when") or {}, name),
        action=cast(Action, data["action"]),
        prompt=data["prompt"],
        tone=str(data.get("tone") or ""),
        examples=_parse_examples(data.get("examples") or [], name),
    )


def _parse_condition(when: object, name: str) -> Condition:
    if not isinstance(when, dict):
        raise RulesError(f"rule '{name}': 'when' must be a mapping")
    data = cast(dict[str, Any], when)
    _reject_unknown(data, WHEN_KEYS, f"rule '{name}' when")
    kind = data.get("kind")
    if kind is not None and kind not in KINDS:
        raise RulesError(f"rule '{name}': kind '{kind}' is not one of {sorted(KINDS)}")
    has_profile = data.get("has_profile")
    if has_profile is not None and not isinstance(has_profile, bool):
        raise RulesError(f"rule '{name}': has_profile must be true or false")
    return Condition(
        kind=cast(Kind | None, kind),
        category=_optional_text(data, "category", name),
        keywords=_text_list(data, "keywords", name),
        sender_title=_text_list(data, "sender_title", name),
        language=_optional_text(data, "language", name),
        has_profile=has_profile,
    )


def _parse_examples(examples: object, name: str) -> tuple[Example, ...]:
    if not isinstance(examples, list):
        raise RulesError(f"rule '{name}': 'examples' must be a list")
    parsed = []
    for example in examples:
        if (
            not isinstance(example, dict)
            or set(example) != {"incoming", "reply"}
            or not all(isinstance(value, str) for value in example.values())
        ):
            raise RulesError(f"rule '{name}': each example needs exactly 'incoming' and 'reply'")
        parsed.append(Example(incoming=example["incoming"], reply=example["reply"]))
    return tuple(parsed)


def _optional_text(data: dict[str, Any], key: str, name: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise RulesError(f"rule '{name}': '{key}' must be a text")
    return value


def _text_list(data: dict[str, Any], key: str, name: str) -> tuple[str, ...]:
    value = data.get(key) or []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise RulesError(f"rule '{name}': '{key}' must be a text or a list of texts")
    return tuple(value)


def _reject_unknown(data: dict[str, Any], allowed: frozenset[str], where: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise RulesError(f"{where}: unknown keys {unknown}; allowed: {sorted(allowed)}")
