# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-user directories (XDG). The repo never holds user data."""

import os
from pathlib import Path

APP = "linkedin-reply-assistant"


def user_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP


def user_state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / APP


def tessdata_dir() -> Path:
    """User-level Tesseract data from scripts/fetch_tessdata.sh (no root needed)."""
    return user_data_dir() / "tessdata"


def runtime_dir() -> Path:
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/{APP}-{os.getuid()}"
    return Path(base) / APP
