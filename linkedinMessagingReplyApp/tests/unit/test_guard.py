# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Guard for the hard limits and the fences of the bent rules in AGENTS.md.

The code never sends, clicks, types keys, fakes a paste or navigates on LinkedIn, never injects OS
input, and never calls linkedin.com.
The scan is deliberately crude. A hit is a defect, or a reason to change AGENTS.md first.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCANNED = [ROOT / "src", ROOT / "extension"]
SUFFIXES = {".py", ".js", ".json", ".html"}

FORBIDDEN = {
    "DOM click": re.compile(r"\.click\s*\("),
    "send button selector": re.compile(r"send[-_]?button|msg-form__send", re.IGNORECASE),
    "form submit": re.compile(r"\.requestSubmit\s*\(|\.submit\(\s*\)"),
    "synthetic key events": re.compile(r"KeyboardEvent|dispatchKey|Input\.dispatch"),
    "page navigation": re.compile(r"location\.(assign|replace)\s*\(|location\.href\s*=[^=]"),
    "tab navigation": re.compile(r"tabs\.(create|update)\s*\("),
    "session cookie": re.compile(r"li_at"),
    "Voyager API": re.compile(r"voyager", re.IGNORECASE),
    "HTTP call to LinkedIn": re.compile(
        r"(get|post|put|patch|delete|request|fetch|urlopen)\([^)]*linkedin\.com", re.IGNORECASE
    ),
    "OS input injection": re.compile(
        r"\b(ydotoold?|uinput|xdotool|wtype|libei|evdev|pynput|pyautogui)\b|portal\.RemoteDesktop",
        re.IGNORECASE,
    ),
    "fake paste": re.compile(r"ClipboardEvent|execCommand\(\s*[\"']paste"),
}


def scanned_files() -> list[Path]:
    return sorted(
        path
        for base in SCANNED
        if base.exists()
        for path in base.rglob("*")
        if path.suffix in SUFFIXES and "node_modules" not in path.parts
    )


def test_source_tree_is_not_empty() -> None:
    assert scanned_files()


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
def test_no_forbidden_pattern(name: str) -> None:
    pattern = FORBIDDEN[name]
    hits = [
        f"{path.relative_to(ROOT)}:{number}"
        for path in scanned_files()
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if pattern.search(line)
    ]
    assert not hits, f"{name} found: {hits}"


@pytest.mark.parametrize(
    ("name", "sample"),
    [
        ("DOM click", "button.click()"),
        ("send button selector", "querySelector('.msg-form__send-button')"),
        ("form submit", "form.requestSubmit()"),
        ("synthetic key events", "new KeyboardEvent('keydown')"),
        ("page navigation", "window.location.href = url"),
        ("tab navigation", "chrome.tabs.update(id, {url})"),
        ("HTTP call to LinkedIn", 'httpx.get("https://www.linkedin.com/x")'),
        ("OS input injection", 'subprocess.run(["ydotool", "key", "29:1"])'),
        ("OS input injection", "org.freedesktop.portal.RemoteDesktop"),
        ("OS input injection", "from pynput.keyboard import Controller"),
        ("fake paste", "el.dispatchEvent(new ClipboardEvent('paste'))"),
        ("fake paste", 'document.execCommand("paste")'),
    ],
)
def test_patterns_catch_examples(name: str, sample: str) -> None:
    assert FORBIDDEN[name].search(sample)
