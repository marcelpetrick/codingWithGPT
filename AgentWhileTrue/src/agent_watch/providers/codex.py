"""Codex CLI prompt recognition.

Patterns were taken from the strings shipped inside the Codex CLI 0.153.2
binary. Codex differs from Claude Code in one way that matters a great deal
here: it offers no "press enter to continue" affordance. When a Codex turn is
cut short by a usage limit the TUI returns to its composer, so resuming means
*typing* rather than pressing a key.

Typing is strictly more dangerous than pressing Enter, because if the foreground
process changed in the meantime the text lands in a shell. Codex resume is
therefore gated behind its own policy flag and stays off in auto mode until the
user opts in, even though the rest of the machinery is identical.
"""

from __future__ import annotations

import re
from typing import Final

from agent_watch.providers.base import (
    ActionKind,
    PromptKind,
    PromptPattern,
    ProviderAdapter,
    ResumeAction,
)

NAME: Final = "codex"
PATTERNS_VERSION: Final = "codex-0.153.x/1"
VERIFIED_AGAINST: Final = "Codex CLI 0.153.2"

#: What is typed into the composer to pick the work back up. Deliberately a
#: plain instruction with no slash command: a slash command that has been
#: renamed would silently do something else.
DEFAULT_RESUME_TEXT: Final = "continue"


def _pattern(text: str) -> re.Pattern[str]:
    return re.compile(text, re.IGNORECASE)


PATTERNS: Final[tuple[PromptPattern, ...]] = (
    PromptPattern(
        id="codex/limit-usage",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="usage",
        all_of=(_pattern(r"You've hit your usage limit"),),
        action=ResumeAction(
            kind=ActionKind.TEXT_THEN_ENTER,
            text=DEFAULT_RESUME_TEXT,
            requires_policy="allow_codex_auto_resume",
        ),
        note="Codex returns to the composer; resuming means typing.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/limit-banner",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="usage",
        all_of=(_pattern(r"Usage limit reached"),),
        action=ResumeAction(
            kind=ActionKind.TEXT_THEN_ENTER,
            text=DEFAULT_RESUME_TEXT,
            requires_policy="allow_codex_auto_resume",
        ),
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/try-again-at",
        provider=NAME,
        kind=PromptKind.WILL_NOT_SELF_RESUME,
        scope="usage",
        all_of=(_pattern(r"Try again at\b"),),
        note="Carries the reset time; Codex never resumes on its own.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/approaching-limit",
        provider=NAME,
        kind=PromptKind.LIMIT_WARNING,
        scope="usage",
        all_of=(_pattern(r"Approaching rate limits"),),
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/out-of-credits",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="credits",
        all_of=(_pattern(r"(?:You're|Your workspace is) out of credits"),),
        note="Money. Never automated.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/workspace-credit-limit",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="credits",
        all_of=(_pattern(r"reached your workspace credit limit"),),
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/purchase-offer",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="credits",
        all_of=(_pattern(r"purchase more credits|Upgrade to (?:Plus|Pro)\b"),),
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/limit-increase-request",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="credits",
        all_of=(_pattern(r"Request (?:a limit increase|an? increase)|Request increase\?"),),
        note="Sends a request to a workspace admin. Never automated.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/reset-credit-offer",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="reset-credit",
        all_of=(_pattern(r"Redeem usage limit reset|usage limit resets? available"),),
        note="Consumes a finite earned reset. Never automated.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="codex/model-downgrade",
        provider=NAME,
        kind=PromptKind.MODEL_DOWNGRADE_OFFER,
        scope="model",
        all_of=(_pattern(r"Keep current model|Uses fewer credits for upcoming turns"),),
        verified_against=VERIFIED_AGAINST,
    ),
)


class CodexAdapter(ProviderAdapter):
    """Recognises Codex CLI's usage-limit prompts."""

    name = NAME
    patterns_version = PATTERNS_VERSION

    @property
    def patterns(self) -> tuple[PromptPattern, ...]:
        return PATTERNS

    def executable_names(self) -> frozenset[str]:
        return frozenset({"codex"})
