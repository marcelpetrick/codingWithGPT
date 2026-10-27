# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Guard for the hard limits in AGENTS.md.

The code never sends, clicks, types or navigates on LinkedIn.

The scan is deliberately crude. A hit is a defect, or a reason to change AGENTS.md first.
"""

import re
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parent.parent / "reply_desk"

FORBIDDEN = {
    "CDP input events": re.compile(r"Input\.dispatch"),
    "CDP navigation": re.compile(r"Page\.(navigate|reload)"),
    "DOM clicks": re.compile(r"\.click\s*\("),
    "session cookie": re.compile(r"li_at"),
    "Voyager API": re.compile(r"voyager", re.IGNORECASE),
    "write calls to LinkedIn": re.compile(
        r"(post|put|patch|delete)\([^)]*linkedin\.com", re.IGNORECASE
    ),
}


def source_files() -> list[Path]:
    return sorted(SOURCE.rglob("*.py"))


def test_source_tree_is_not_empty() -> None:
    assert source_files()


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
def test_no_forbidden_pattern(name: str) -> None:
    pattern = FORBIDDEN[name]
    hits = [
        f"{path.relative_to(SOURCE.parent)}:{number}"
        for path in source_files()
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if pattern.search(line)
    ]
    assert not hits, f"{name} found: {hits}"


def test_patterns_catch_examples() -> None:
    assert FORBIDDEN["CDP input events"].search('send("Input.dispatchMouseEvent")')
    assert FORBIDDEN["DOM clicks"].search("button.click()")
    assert FORBIDDEN["write calls to LinkedIn"].search('httpx.post("https://www.linkedin.com/x")')
