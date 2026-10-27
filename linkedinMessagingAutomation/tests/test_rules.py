# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from reply_desk.rules import (
    Condition,
    Item,
    Rule,
    RulesError,
    first_match,
    load_default_rules,
    load_rules,
)

FALLBACK = "- id: fallback\n  when: {}\n  action: draft_only\n  prompt: p.md\n"


def rules_with(head: str) -> list[Rule]:
    return load_rules(head + FALLBACK)


# --- conditions ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("condition", "item", "expected"),
    [
        (Condition(), Item(kind="message", text="x"), True),
        (Condition(kind="invitation"), Item(kind="message", text="x"), False),
        (
            Condition(category="recruiter"),
            Item(kind="message", text="", category="recruiter"),
            True,
        ),
        (Condition(category="recruiter"), Item(kind="message", text=""), False),
        (Condition(language="de"), Item(kind="message", text="", language="en"), False),
        (Condition(has_profile=True), Item(kind="invitation", text=""), False),
        (Condition(keywords=("WEBINAR",)), Item(kind="message", text="Join our webinar"), True),
        (Condition(keywords=("webinar", "demo")), Item(kind="message", text="Hello"), False),
        (
            Condition(sender_title=("recruit",)),
            Item(kind="message", text="", sender_title="Recruiter"),
            True,
        ),
        (
            Condition(sender_title=("recruit",)),
            Item(kind="message", text="", sender_title="CTO"),
            False,
        ),
    ],
)
def test_condition_matches(condition: Condition, item: Item, expected: bool) -> None:
    assert condition.matches(item) is expected


def test_all_fields_must_match() -> None:
    condition = Condition(kind="message", keywords=("offer",), language="de")
    assert condition.matches(Item(kind="message", text="Ein Offer", language="de"))
    assert not condition.matches(Item(kind="message", text="Ein Offer", language="en"))


# --- loading ------------------------------------------------------------------------------------


def test_first_match_wins_in_file_order() -> None:
    rules = rules_with(
        "- id: a\n  when: {keywords: [offer]}\n  action: decline\n  prompt: a.md\n"
        "- id: b\n  when: {keywords: [offer, hello]}\n  action: reply\n  prompt: b.md\n"
    )
    assert first_match(rules, Item(kind="message", text="special offer")).id == "a"
    assert first_match(rules, Item(kind="message", text="hello")).id == "b"
    assert first_match(rules, Item(kind="message", text="other")).id == "fallback"


def test_full_rule_is_parsed() -> None:
    rule = rules_with(
        "- id: r\n  when: {kind: invitation, sender_title: CEO, has_profile: false}\n"
        "  action: reply\n  prompt: r.md\n  tone: warm\n"
        "  examples:\n    - {incoming: Hi, reply: Hello}\n"
    )[0]
    assert rule.when == Condition(kind="invitation", sender_title=("CEO",), has_profile=False)
    assert rule.tone == "warm"
    assert rule.examples[0].reply == "Hello"


def test_first_match_without_catch_all_raises() -> None:
    rule = Rule(id="x", when=Condition(kind="invitation"), action="reply", prompt="p")
    with pytest.raises(RulesError, match="no rule matched"):
        first_match([rule], Item(kind="message", text=""))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("a: [", "not valid YAML"),
        ("{}", "non-empty list"),
        ("[]", "non-empty list"),
        ("- just text\n", "not a mapping"),
        ("- id: x\n  action: reply\n  prompt: p\n  colour: red\n", "unknown keys"),
        ("- id: x\n  action: reply\n", "'prompt' is required"),
        ("- id: x\n  action: send\n  prompt: p\n", "is not one of"),
        ("- id: x\n  when: [a]\n  action: reply\n  prompt: p\n", "'when' must be a mapping"),
        ("- id: x\n  when: {kategory: a}\n  action: reply\n  prompt: p\n", "unknown keys"),
        ("- id: x\n  when: {kind: post}\n  action: reply\n  prompt: p\n", "kind 'post'"),
        (
            "- id: x\n  when: {has_profile: yes please}\n  action: reply\n  prompt: p\n",
            "true or false",
        ),
        ("- id: x\n  when: {category: 3}\n  action: reply\n  prompt: p\n", "must be a text"),
        ("- id: x\n  when: {keywords: [1]}\n  action: reply\n  prompt: p\n", "list of texts"),
        ("- id: x\n  action: reply\n  prompt: p\n  examples: {a: b}\n", "must be a list"),
        ("- id: x\n  action: reply\n  prompt: p\n  examples: [{incoming: a}]\n", "exactly"),
        ("- id: x\n  when: {kind: message}\n  action: reply\n  prompt: p\n", "must be a catch-all"),
    ],
)
def test_invalid_rulesets_are_rejected(text: str, message: str) -> None:
    with pytest.raises(RulesError, match=message):
        load_rules(text)


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(RulesError, match="duplicate rule ids: fallback"):
        rules_with(FALLBACK)


def test_catch_all_before_the_end_is_rejected() -> None:
    with pytest.raises(RulesError, match="'early' is a catch-all"):
        rules_with("- id: early\n  action: reply\n  prompt: p\n")


# --- the shipped ruleset: one golden case per rule -----------------------------------------------

GOLDEN = {
    "decline_commercial": Item(kind="message", text="Buy leads", category="commercial_offer"),
    "friendly_connect": Item(kind="invitation", text="Hi Marcel", has_profile=True),
    "connect_without_profile": Item(kind="invitation", text="Hi Marcel"),
    "recruiter_senior_only": Item(kind="message", text="New role", category="recruiter"),
    "fallback": Item(kind="message", text="Long time no see!", category="personal"),
}


def test_default_rules_have_a_golden_case_each() -> None:
    assert [rule.id for rule in load_default_rules()] == list(GOLDEN)


@pytest.mark.parametrize("rule_id", sorted(GOLDEN))
def test_default_rules_golden_cases(rule_id: str) -> None:
    assert first_match(load_default_rules(), GOLDEN[rule_id]).id == rule_id
