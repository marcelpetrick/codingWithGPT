# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Parse the one JSON object a model was asked to return (tolerates code fences and chatter)."""

import json
from typing import Any


class JsonOutputError(ValueError):
    """The model answer contains no valid JSON object."""


def parse_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise JsonOutputError("no JSON object in the model answer")
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise JsonOutputError(f"invalid JSON in the model answer: {exc.msg}") from exc
    if not isinstance(value, dict):  # pragma: no cover - braces guarantee an object
        raise JsonOutputError("the model answer is not a JSON object")
    return value
