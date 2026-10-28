# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Values the app writes itself (ROI, portal restore token, accepted hotkey). No message content.

Stored as YAML next to the configuration: ~/.config/linkedin-reply-assistant/state.yaml.
A broken file is ignored (the user selects the window and region again), never fatal.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.config.loader import user_config_dir


@dataclass
class Settings:
    roi: Roi | None = None
    restore_token: str | None = None
    hotkey_trigger: str = ""
    always_on_top: bool = False


def settings_path(config_dir: Path | None = None) -> Path:
    return (user_config_dir() if config_dir is None else config_dir) / "state.yaml"


def load_settings(path: Path) -> Settings:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError, yaml.YAMLError:
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    token = data.get("restore_token")
    return Settings(
        roi=Roi.from_dict(data.get("roi")),
        restore_token=token if isinstance(token, str) and token else None,
        hotkey_trigger=str(data.get("hotkey_trigger") or ""),
        always_on_top=bool(data.get("always_on_top", False)),
    )


def save_settings(path: Path, settings: Settings) -> None:
    data = {
        "roi": settings.roi.to_dict() if settings.roi else None,
        "restore_token": settings.restore_token,
        "hotkey_trigger": settings.hotkey_trigger,
        "always_on_top": settings.always_on_top,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        "# Written by the app. Safe to delete.\n" + yaml.safe_dump(data), encoding="utf-8"
    )
    os.chmod(tmp, 0o600)  # the restore token grants screen access
    tmp.replace(path)
