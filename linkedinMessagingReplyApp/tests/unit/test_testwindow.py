# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

import pytest
from PIL import Image
from pytestqt.qtbot import QtBot

from linkedin_reply_assistant.model import load_conversation
from linkedin_reply_assistant.testwindow import TITLE, CaptureTestWindow, render
from tests.conftest import FIXTURES

CONVERSATION = load_conversation(FIXTURES / "messages" / "substantive_01.yaml")


def test_window_shows_conversation(qtbot: QtBot) -> None:
    window = CaptureTestWindow(CONVERSATION, "dark", 1.5)
    qtbot.addWidget(window)
    assert window.windowTitle() == TITLE
    assert window.width() == 1350


@pytest.mark.parametrize("dpr", [1.0, 2.0])
def test_render_png(qtbot: QtBot, tmp_path: Path, dpr: float) -> None:
    path = tmp_path / "shot.png"
    render(CONVERSATION, path, "light", 1.0, dpr)
    with Image.open(path) as image:
        assert image.size == (round(900 * dpr), round(560 * dpr))


def test_render_fails_on_bad_path(qtbot: QtBot, tmp_path: Path) -> None:
    with pytest.raises(OSError, match="cannot write"):
        render(CONVERSATION, tmp_path / "missing" / "x.png")
