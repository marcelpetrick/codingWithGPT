"""Claude Code prompt recognition.

Every pattern below was taken from the strings shipped inside the Claude Code
2.1.261 executable and cross-checked against a screenshot of a real five-hour
limit event, rather than being guessed from documentation.

The most important entry is not a limit pattern at all: since 2.1.234 Claude
Code resumes itself when the limit resets, and advertises that with
"Continuing automatically when your limit resets". When that is on screen the
supervisor must stand down, because two things pressing Enter at the same
prompt is worse than neither.

The gap the supervisor genuinely fills is the opposite case, which Claude Code
also states explicitly: a reset more than 24 hours out, or a session that was
moved to the background, will *not* resume on its own.
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

NAME: Final = "claude"
PATTERNS_VERSION: Final = "claude-2.1.x/2"
VERIFIED_AGAINST: Final = "Claude Code 2.1.261"


def _pattern(text: str) -> re.Pattern[str]:
    return re.compile(text, re.IGNORECASE)


#: Claude renders "·" between the headline and the reset time. It is matched
#: loosely because the separator is cosmetic and could change.
_RESETS = r"resets?\b"

PATTERNS: Final[tuple[PromptPattern, ...]] = (
    PromptPattern(
        id="claude/limit-session",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="session",
        all_of=(_pattern(r"You've hit your session limit"),),
        note="Rolling five-hour window exhausted.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/limit-weekly",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="weekly",
        all_of=(_pattern(r"You've hit your weekly limit"),),
        note="Seven-day window exhausted; a five-hour reset must not unblock it.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/limit-opus",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="opus",
        all_of=(_pattern(r"You've hit your Opus limit"),),
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/limit-sonnet",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="sonnet",
        all_of=(_pattern(r"You've hit your Sonnet limit"),),
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/limit-fast",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="fast",
        all_of=(_pattern(r"You've hit your fast limit"),),
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/limit-banner",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="session",
        all_of=(_pattern(r"Usage limit reached"),),
        note="Generic banner; carries the reset time.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/arm-automatic-wait",
        provider=NAME,
        kind=PromptKind.LIMIT_BLOCKED,
        scope="session",
        all_of=(
            _pattern(
                r"\N{HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT}"
                r"\s*1\.\s*Stop and wait for limit to reset"
            ),
            _pattern(r"2\.\s*Wait here, then continue automatically"),
            _pattern(r"Enter to confirm"),
        ),
        action=ResumeAction(
            kind=ActionKind.ARROW_DOWN_THEN_ENTER,
            requires_policy="allow_claude_auto_wait",
        ),
        note="Exact menu and cursor position required; selects only Claude's own wait mode.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/ready-press-enter",
        provider=NAME,
        kind=PromptKind.READY_TO_RESUME,
        scope="session",
        all_of=(
            _pattern(r"[Uu]sage limit (?:has reset|reset|available again)"),
            _pattern(r"press enter to continue"),
        ),
        # The provider states the expected input in so many words, so the action
        # is a bare Enter. The literal word "continue" is never typed: at this
        # prompt it would be echoed into the composer rather than accepted.
        action=ResumeAction(kind=ActionKind.ENTER),
        note="Requires both the reset headline and the explicit affordance.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/self-healing",
        provider=NAME,
        kind=PromptKind.SELF_HEALING,
        scope="session",
        all_of=(_pattern(r"[Cc]ontinuing automatically when (?:your limit|it) resets"),),
        note="Claude Code 2.1.234+ resumes itself; the supervisor must stand down.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/self-healing-timed",
        provider=NAME,
        kind=PromptKind.SELF_HEALING,
        scope="session",
        all_of=(
            _pattern(
                r"(?:Claude Code will continue|continuing) automatically at "
                r"\d{1,2}[:.]\d{2}(?:am|pm)"
            ),
        ),
        note="Timed automatic wait is already armed; the supervisor must stand down.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/will-not-self-resume",
        provider=NAME,
        kind=PromptKind.WILL_NOT_SELF_RESUME,
        scope="session",
        all_of=(_pattern(r"will not resume on its own"),),
        note="Reset more than 24h out, or the session was backgrounded.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/spend-limit",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="spend",
        all_of=(_pattern(r"You've hit your monthly spend limit"),),
        note="Money. Never automated.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/usage-credits-offer",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="credits",
        all_of=(_pattern(r"/(?:upgrade|usage-credits)\b"),),
        note="Offers paid continuation. Never automated.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/upgrade-plan-offer",
        provider=NAME,
        kind=PromptKind.PAID_ACTION_REQUIRED,
        scope="credits",
        all_of=(_pattern(r"Upgrade your plan"),),
        note="Interactive paid upgrade choice. Never selected automatically.",
        verified_against=VERIFIED_AGAINST,
    ),
    PromptPattern(
        id="claude/model-downgrade",
        provider=NAME,
        kind=PromptKind.MODEL_DOWNGRADE_OFFER,
        scope="model",
        all_of=(_pattern(r"Switch to another model"),),
        note="Silently changes output quality. Never automated.",
        verified_against=VERIFIED_AGAINST,
    ),
)


class ClaudeAdapter(ProviderAdapter):
    """Recognises Claude Code's usage-limit prompts."""

    name = NAME
    patterns_version = PATTERNS_VERSION

    @property
    def patterns(self) -> tuple[PromptPattern, ...]:
        return PATTERNS

    def executable_names(self) -> frozenset[str]:
        return frozenset({"claude"})
