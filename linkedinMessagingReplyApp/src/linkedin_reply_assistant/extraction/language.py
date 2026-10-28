# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tiny stop-word language guess for the dominant language of a message (§19). No dependencies."""

import re

STOPWORDS = {
    "en": {
        *("the", "and", "you", "for", "with", "this", "your", "are", "have", "would", "is"),
        *("to", "of", "in", "on", "we", "our", "i", "it", "be", "thanks", "hi", "hello", "that"),
    },
    "de": {
        *("der", "die", "das", "und", "sie", "ich", "für", "mit", "nicht", "ist", "ein", "eine"),
        *("zu", "auf", "wir", "ihr", "ihnen", "hallo", "danke", "bei", "als", "hätten", "suche"),
    },
    "fr": {"le", "la", "les", "et", "vous", "pour", "avec", "est", "une", "des", "bonjour"},
    "es": {"el", "los", "las", "y", "usted", "para", "con", "una", "hola", "gracias", "que"},
}


def guess_language(text: str) -> str:
    """Return an ISO 639-1 code, or "und" when the text gives no signal."""
    words = re.findall(r"[a-zA-ZäöüÄÖÜßéèàáñ]+", text.lower())
    scores = {lang: sum(w in stop for w in words) for lang, stop in STOPWORDS.items()}
    best = max(scores, key=lambda lang: scores[lang])
    return best if scores[best] > 0 else "und"
