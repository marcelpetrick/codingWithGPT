# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prompt construction with a strict split of policy and message data (§11, §12).

Message text is untrusted. It is never passed through str.format, it is wrapped in data markers,
and marker look-alikes inside it are neutralized so it cannot close the data block.
"""

import re

from linkedin_reply_assistant.config.loader import Config

OPEN = "<<<MESSAGE_DATA"
CLOSE = "MESSAGE_DATA>>>"
MARKER = re.compile(r"<{0,3}\s*MESSAGE_DATA\s*>{0,3}", re.IGNORECASE)
LANGUAGE_NAMES = {"en": "English", "de": "German"}


def fence(text: str) -> str:
    """Wrap untrusted text as data. Marker look-alikes inside the text are removed."""
    cleaned = MARKER.sub("[removed marker]", text)
    return f"{OPEN}\n{cleaned}\n{CLOSE}"


def classifier_prompt(config: Config, text: str) -> tuple[str, str]:
    return config.prompts["classifier.md"], fence(text)


def reply_prompt(config: Config, category: str, language: str, transcript: str) -> tuple[str, str]:
    """Return (system, user) for a reply in `language` under the policy of `category`."""
    profile = config.user_profile
    policy = config.reply_rules.categories[category]
    facts = (
        "\n".join(f"  - {fact}" for fact in profile.allowed_facts)
        if category in profile.mention_facts_in
        else "  - (none for this kind of message)"
    )
    values = {
        "name": profile.name,
        "language": LANGUAGE_NAMES.get(language, language),
        "max_words": policy.max_words,
        "sign_off": profile.sign_off_de if language == "de" else profile.sign_off,
        "allowed_facts": facts,
        "style": "\n".join(f"  - {rule}" for rule in config.reply_rules.style),
        "category": category,
        "recruiting_preference": profile.recruiting_preference,
    }
    system = config.prompts["system.md"].format(**values)
    task = config.prompts[policy.prompt].format(**values)
    user = (
        "Conversation, oldest message first. Draft the reply to the last incoming message.\n"
        + fence(transcript)
    )
    return f"{system}\n\n{task}", user
