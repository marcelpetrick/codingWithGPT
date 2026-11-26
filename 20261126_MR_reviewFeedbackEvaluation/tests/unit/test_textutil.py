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
