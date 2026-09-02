"""Redaction for outputs that leave the machine.

Some repository names identify a customer or a product that is nobody else's
business. The survey still has to count them — dropping them would falsify
coverage — so they are masked at the point of output instead: the first
character survives, the rest becomes a block, and the length stays honest.

    acmeanalyzer  ->  a███████████

Applied to the finished report, the canonical file and the JSON, so a name is
masked wherever it turns up: a scope, a path, a table cell, a quoted rule.
"""

from __future__ import annotations

import re
from pathlib import Path

BLOCK = "█"

# The stems themselves are the sensitive part: a list of customer names sitting
# in a public repository would publish exactly what the masking is meant to
# hide. So the list is not in the code. It lives in an untracked file, one stem
# per line, blank lines and # comments ignored:
#
#     <project root>/redact.stems
#
# A stem matches a whole name token — never a fragment of an unrelated word —
# so a stem like "abc" masks abc and abc_tooling while leaving "abcdefg" as one
# token and ordinary prose untouched.
STEMS_FILE = Path(__file__).resolve().parent.parent / "redact.stems"

DEFAULT_STEMS: tuple[str, ...] = ()

# Characters that belong to a name token. The path separator does not, so each
# segment of a/b/c is masked on its own merits.
_TOKEN = r"[\w.-]"


def _pattern(stem: str) -> re.Pattern[str]:
    """A token that *starts with* the stem, or contains it after a separator.

    The second case exists for a stem that trails a compound name, where the
    sensitive part is the last segment of something like vendor-board-<stem>.
    """
    escaped = re.escape(stem)
    return re.compile(rf"\b(?:{_TOKEN}*[-_.])?{escaped}{_TOKEN}*", re.IGNORECASE)


def load_stems(path: Path = STEMS_FILE) -> tuple[str, ...]:
    """Read the untracked stem list. Missing file means no stems, not a crash."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    return tuple(
        line.strip().lower()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    )


def mask(token: str) -> str:
    """First character, then one block per remaining character."""
    return token[0] + BLOCK * (len(token) - 1) if token else token


def redact(text: str, stems: tuple[str, ...] = DEFAULT_STEMS) -> str:
    """Mask every occurrence of every stem in ``text``."""
    for stem in stems:
        text = _pattern(stem).sub(lambda m: mask(m.group(0)), text)
    return text
