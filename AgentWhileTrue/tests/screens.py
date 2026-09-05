"""Screen fixtures reproducing what the real CLIs display.

The Claude blocks are transcribed from a screenshot of an actual five-hour limit
event on Claude Code 2.1.261; the wording of the other blocks comes from the
strings shipped inside the Claude Code 2.1.261 and Codex CLI 0.153.2 binaries.
Keeping them here, verbatim, is what makes the recognizer tests meaningful.
"""

from __future__ import annotations

CLAUDE_SESSION_LIMIT = [
    "  ⎿  You've hit your session limit · resets 8:10pm (Europe/Berlin)",
    "     /upgrade or /usage-credits to finish what you're working on.",
    "",
    "✳ Crunched for 0s · done 7:31 PM",
    "",
    "❯ ",
]

CLAUDE_READY_TO_RESUME = [
    "  ⎿  You've hit your session limit · resets 8:10pm (Europe/Berlin)",
    "",
    "✳ Crunched for 0s · done 7:31 PM",
    "",
    "● Usage limit has reset · press enter to continue",
    "",
    "❯ ",
]

CLAUDE_SELF_HEALING = [
    "● Usage limit reached · resets 8:10pm",
    "  Continuing automatically when your limit resets",
    "",
    "❯ ",
]

CLAUDE_WEEKLY_LIMIT = [
    "  ⎿  You've hit your weekly limit · resets Mon 12:00am",
    "",
    "❯ ",
]

CLAUDE_WILL_NOT_SELF_RESUME = [
    "● Usage limit reached · resets in 30h",
    "  the usage limit now resets more than 24 hours out, so this task will not",
    "  resume on its own (/rate-limit-options to wait anyway)",
    "",
    "❯ ",
]

CLAUDE_SPEND_LIMIT = [
    "● You've hit your monthly spend limit. Run /usage-credits to manage your limit",
    "",
    "❯ ",
]

CLAUDE_MODEL_DOWNGRADE = [
    "● You've hit your Opus limit · resets 8:10pm",
    "  Switch to another model to keep going",
    "",
    "❯ ",
]

CLAUDE_ACTIVE = [
    "● Reading src/agent_watch/policy.py",
    "",
    "❯ ",
    "  Opus 5 ctx:28% 5h:19% reset:4h51m",
]

CODEX_USAGE_LIMIT = [
    "▌ You've hit your usage limit. Try again at 8:10 PM.",
    "",
    "› ",
]

CODEX_APPROACHING = [
    "▌ Approaching rate limits",
    "",
    "› ",
]

CODEX_OUT_OF_CREDITS = [
    "▌ You're out of credits. Your workspace is out of credits. Add credits to continue.",
    "",
    "› ",
]

CODEX_MODEL_DOWNGRADE = [
    "▌ You've hit your usage limit.",
    "  Uses fewer credits for upcoming turns.",
    "  Keep current model",
    "",
    "› ",
]

CODEX_RESET_CREDIT = [
    "▌ Usage limit reached",
    "  Redeem usage limit reset",
    "",
    "› ",
]

CODEX_ACTIVE = [
    "• Ran cargo test",
    "",
    "› ",
]


#: A limit banner that has scrolled far up the screen. It must not be able to
#: trigger anything (vision DANGER 3).
def scrolled_away(block: list[str], *, filler_lines: int = 60) -> list[str]:
    return [*block, *[f"  ... build output line {n}" for n in range(filler_lines)], "❯ "]
