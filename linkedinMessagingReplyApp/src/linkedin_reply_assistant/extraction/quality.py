# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extraction quality checks (§9.5). A warning marks the draft as "Extraction needs review"."""

import re

# Characters that normal message text uses. The hyphen is escaped: "#-–" would be a range.
GARBAGE = re.compile(r"[^\w\s.,!?:;'\"()@&%€$/+#\-–—…’“”]", re.UNICODE)


def quality_warnings(
    text: str, confidence: float, min_confidence: float, min_chars: int
) -> list[str]:
    warnings = []
    stripped = text.strip()
    if len(stripped) < min_chars:
        warnings.append(f"almost no text recognized ({len(stripped)} characters)")
    if stripped:
        garbage = len(GARBAGE.findall(stripped)) / len(stripped)
        if garbage > 0.15:
            warnings.append(f"many unusual characters ({garbage:.0%})")
    if confidence * 100 < min_confidence:
        warnings.append(f"low recognition confidence ({confidence:.0%})")
    return warnings
