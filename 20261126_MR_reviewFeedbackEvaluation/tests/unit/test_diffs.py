# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the diff parser."""

from mrreview.diffs import new_side_lines, window

DIFF = "@@ -1,3 +1,4 @@\n a\n-b\n+B\n+C\n d\n\\ No newline at end of file\n@@ -10 +11 @@\n+z\n"


def test_new_side_lines() -> None:
    assert new_side_lines(DIFF) == {1: "a", 2: "B", 3: "C", 4: "d", 11: "z"}


def test_ignores_text_before_first_hunk() -> None:
    assert new_side_lines("diff --git a b\n+++ b/x\n@@ -0,0 +1 @@\n+x") == {1: "x"}


def test_window() -> None:
    lines = {1: "a", 2: "b", 3: "c", 9: "z"}
    assert window(lines, 2, 1) == {1: "a", 2: "b", 3: "c"}
    assert window(lines, 9, 5) == {9: "z"}
