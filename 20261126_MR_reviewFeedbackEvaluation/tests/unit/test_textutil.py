# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for text handling and the routine-approval check (REQ-UNIT-1)."""

import pytest

from mrreview import textutil


def test_grapheme_len_counts_visible_characters() -> None:
    assert textutil.grapheme_len("e\u0301") == 1
    assert textutil.grapheme_len("👍🏽") == 1
    assert textutil.grapheme_len("👨‍👩‍👧") == 1
    assert textutil.grapheme_len("Grüße") == 5


def test_truncate_never_cuts_inside_a_grapheme() -> None:
    text = "ab👨‍👩‍👧cd"
    assert textutil.truncate(text, 3) == "ab…"
    assert textutil.truncate(text, 4) == "ab👨‍👩‍👧…"
    assert textutil.truncate(text, 5) == text
    assert textutil.truncate("", 3) == ""


def test_truncate_rejects_bad_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        textutil.truncate("abc", 0)


def test_normalize_makes_composed_and_decomposed_equal() -> None:
    assert textutil.normalize("e\u0301") == textutil.normalize("é")
    assert textutil.fold("Straße") == textutil.fold("STRASSE")


@pytest.mark.parametrize(
    "body",
    [
        "LGTM",
        "lgtm!",
        "Looks good to me 👍",
        "+1",
        "👍",
        "👍🏽🎉",
        ":thumbsup:",
        "Thanks!",
        "Approved.",
        "Sieht gut aus!",
        "Passt, danke",
        "   ",
        "LGTM, thanks!",
        "> quoted suggestion\nlgtm",
    ],
)
def test_routine_bodies(body: str) -> None:
    assert textutil.is_routine(body)


@pytest.mark.parametrize(
    "body",
    [
        "Looks good, but rename `foo` to `bar`.",
        "This leaks the file handle when parse() throws.",
        "Warum nicht std::optional?",
        "Done",
        "なぜここでロックが必要ですか?",
        "+1 but please add a test",
        "Is this thread-safe?",
    ],
)
def test_substantive_bodies(body: str) -> None:
    assert not textutil.is_routine(body)


def test_strip_quotes_removes_quoted_lines() -> None:
    assert textutil.strip_quotes("> old\nnew\n>also old") == "new"


def test_reply_words_skips_quotes_and_code() -> None:
    """REQ-UI-7: reply depth counts the person's own words, not quoted text or code."""
    from mrreview.textutil import reply_words

    text = "> quoted reviewer text here\nGood point, I changed the loop.\n```\nfor x in y: pass\n```\nDone 👍"
    assert reply_words(text) == 7
    assert reply_words("") == 0
    assert reply_words("Grüße, naïve café") == 3


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Thanks, fixed.", True),
        ("thank you for the review", True),
        ("Danke, erledigt", True),
        ("Good catch! Changed.", True),
        ("Guter Punkt, passe ich an", True),
        ("> thanks\nNo, this stays.", False),
        ("Won't do, not needed.", False),
        ("thankless task", False),
    ],
)
def test_is_thanks(text: str, expected: bool) -> None:
    """REQ-UI-7: appreciation in the recipient's own words (English and German)."""
    from mrreview.textutil import is_thanks

    assert is_thanks(text) is expected
