# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path

import pytest

from linkedin_reply_assistant import paths


def test_paths_follow_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "d"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "s"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "r"))
    assert paths.tessdata_dir() == tmp_path / "d" / "linkedin-reply-assistant" / "tessdata"
    assert paths.user_state_dir() == tmp_path / "s" / "linkedin-reply-assistant"
    assert paths.runtime_dir() == tmp_path / "r" / "linkedin-reply-assistant"


def test_paths_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR"):
        monkeypatch.delenv(name, raising=False)
    assert paths.user_data_dir() == Path.home() / ".local/share/linkedin-reply-assistant"
    assert paths.user_state_dir() == Path.home() / ".local/state/linkedin-reply-assistant"
    assert paths.runtime_dir() == Path(f"/tmp/linkedin-reply-assistant-{os.getuid()}") / (
        "linkedin-reply-assistant"
    )
