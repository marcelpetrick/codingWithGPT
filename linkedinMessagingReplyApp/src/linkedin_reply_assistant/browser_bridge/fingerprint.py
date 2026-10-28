# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Conversation identity check before insertion (§14.3).

The capture gives a participant name from OCR. The extension reports the active thread title and
URL. OCR may differ in a letter or two, so names are compared with a similarity threshold.
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

MATCH_THRESHOLD = 0.8
Verdict = Literal["match", "mismatch", "unknown"]


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", text.lower()).strip()


@dataclass(frozen=True)
class Identity:
    title: str
    url: str

    @property
    def thread_id(self) -> str | None:
        match = re.search(r"/messaging/thread/([^/?#]+)", self.url)
        return match.group(1) if match else None


def compare(captured_participant: str | None, active: Identity | None) -> Verdict:
    """match: same conversation; mismatch: clearly another one; unknown: cannot tell."""
    if not captured_participant or active is None or not active.title.strip():
        return "unknown"
    captured = normalize_name(captured_participant)
    title = normalize_name(active.title)
    if not captured or not title:
        return "unknown"
    shorter, longer = sorted((captured.split(), title.split()), key=len)
    if set(shorter) <= set(longer):  # whole names only: "Ann" must not match "Joanna"
        return "match"
    ratio = difflib.SequenceMatcher(None, captured, title).ratio()
    return "match" if ratio >= MATCH_THRESHOLD else "mismatch"
