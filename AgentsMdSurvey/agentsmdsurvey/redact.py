"""Redaction for outputs that leave the machine.

Some repository names identify a customer or a product that is nobody else's
business. The survey still has to count them — dropping them would falsify
coverage — so they are masked at the point of output instead: the first
character survives, the rest becomes a block, and the length stays honest.

    easyanalyzer  ->  e███████████

Applied to the finished report, the canonical file and the JSON, so a name is
masked wherever it turns up: a scope, a path, a table cell, a quoted rule.
"""

from __future__ import annotations

import re

BLOCK = "█"

# Name stems to mask. A stem matches a whole name token — never a fragment of
# an unrelated word — so "mpt" masks mpt and mpt_automatedqualitytest while
# leaving "prompt" and "attempt" alone.
DEFAULT_STEMS: tuple[str, ...] = ("easyanalyzer", "mpt", "lvgl_app", "p118", "epulse")

# Characters that belong to a name token. The path separator does not, so each
# segment of a/b/c is masked on its own merits.
_TOKEN = r"[\w.-]"


def _pattern(stem: str) -> re.Pattern[str]:
    """A token that *starts with* the stem, or contains it after a separator.

    The second case exists for stems that trail a compound name, such as the
    p118 in meta-imx8mm-data-modul-p118.
    """
    escaped = re.escape(stem)
    return re.compile(rf"\b(?:{_TOKEN}*[-_.])?{escaped}{_TOKEN}*", re.IGNORECASE)


def mask(token: str) -> str:
    """First character, then one block per remaining character."""
    return token[0] + BLOCK * (len(token) - 1) if token else token


def redact(text: str, stems: tuple[str, ...] = DEFAULT_STEMS) -> str:
    """Mask every occurrence of every stem in ``text``."""
    for stem in stems:
        text = _pattern(stem).sub(lambda m: mask(m.group(0)), text)
    return text
