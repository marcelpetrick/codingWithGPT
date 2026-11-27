# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unicode-safe text helpers and the routine-approval check.

Text is cut and counted by grapheme cluster, so an emoji or an accented letter is never split.
Text is NFC-normalised before comparison.
"""

from __future__ import annotations

import unicodedata

import regex

_GRAPHEME = regex.compile(r"\X")
_SHORTCODE = regex.compile(r":[a-z0-9_+\-]+:")
_ROUTINE_WORDS = frozenset(
    [
        "lgtm",
        "looks",
        "look",
        "good",
        "to",
        "me",
        "approved",
        "approve",
        "ship",
        "it",
        "thanks",
        "thank",
        "you",
        "thx",
        "ty",
        "ok",
        "okay",
        "nice",
        "great",
        "cool",
        "job",
        "well",
        "+1",
        "sieht",
        "gut",
        "aus",
        "passt",
        "danke",
        "super",
        "top",
        "merci",
        "parfait",
        "perfect",
        "lgtm.",
    ]
)
_MAX_ROUTINE_WORDS = 8


def normalize(text: str) -> str:
    """Return the NFC form of text."""
    return unicodedata.normalize("NFC", text)


def fold(text: str) -> str:
    """Return a form of text for caseless comparison (NFKC plus casefold)."""
    return unicodedata.normalize("NFKC", text).casefold()


def graphemes(text: str) -> list[str]:
    """Split text into user-visible characters (extended grapheme clusters)."""
    return list(_GRAPHEME.findall(normalize(text)))


def grapheme_len(text: str) -> int:
    """Count user-visible characters."""
    return len(graphemes(text))


def truncate(text: str, limit: int, ellipsis: str = "…") -> str:
    """Cut text to at most limit graphemes, the ellipsis included."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    parts = graphemes(text)
    if len(parts) <= limit:
        return "".join(parts)
    return "".join(parts[: limit - 1]) + ellipsis


def strip_quotes(text: str) -> str:
    """Remove Markdown quote lines (they repeat another note)."""
    kept = [line for line in text.splitlines() if not line.lstrip().startswith(">")]
    return "\n".join(kept).strip()


def _is_decoration(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return cat in {"So", "Sk", "Cf", "Zs", "Cc"} or cat.startswith("P") or ch in "\ufe0f\u20e3"


def is_routine(body: str) -> bool:
    """True when a note says no more than a routine approval, thanks or an emoji.

    The check is deliberately narrow: any extra word makes the note non-routine.
    """
    text = fold(strip_quotes(body))
    text = text.replace("+1", " plusone ")
    text = _SHORTCODE.sub(" ", text)
    cleaned = "".join(" " if _is_decoration(ch) else ch for ch in text)
    words = [w for w in cleaned.split() if w]
    if not words:
        return True
    if len(words) > _MAX_ROUTINE_WORDS:
        return False
    return all(w in _ROUTINE_WORDS or w == "plusone" for w in words)


_FENCE = regex.compile(r"```.*?(?:```|$)", flags=regex.DOTALL)
_WORD = regex.compile(r"\w+")
_THANKS = regex.compile(
    r"\b(?:thanks?|thx|ty|danke|merci|good (?:catch|point|idea|hint)|nice (?:catch|idea)|"
    r"great (?:catch|point|idea)|guter (?:punkt|hinweis|catch|einwand)|gute idee)\b",
    flags=regex.IGNORECASE,
)


def own_text(text: str) -> str:
    """The author's own words: without quoted lines and fenced code."""
    return _FENCE.sub(" ", strip_quotes(normalize(text)))


def reply_words(text: str) -> int:
    """Words a person wrote in a note (REQ-UI-7). Quotes, code and emoji do not count."""
    return len(_WORD.findall(own_text(text)))


def is_thanks(text: str) -> bool:
    """True when the note thanks or credits the feedback in its own words (REQ-UI-7)."""
    return _THANKS.search(own_text(text)) is not None
