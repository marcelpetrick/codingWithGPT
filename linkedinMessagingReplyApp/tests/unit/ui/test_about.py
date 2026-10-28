# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import builtins
import shutil
import subprocess
from importlib import metadata
from pathlib import Path

import pytest
from PIL import Image
from pytestqt.qtbot import QtBot

from linkedin_reply_assistant.cli import main
from linkedin_reply_assistant.ui import about
from linkedin_reply_assistant.ui.about import AboutDialog, all_dependencies, python_dependencies


def test_about_dialog_content(qtbot: QtBot) -> None:
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    for text in (
        "Marcel Petrick",
        "mail@marcelpetrick.it",
        "GPLv3",
        "own risk",
        "thought prototype",
    ):
        assert text in about.ABOUT_HTML
    names = [dialog.table.item(row, 0).text() for row in range(dialog.table.rowCount())]  # type: ignore[union-attr]
    for name in (
        "Python",
        "Qt",
        "GStreamer",
        "Tesseract OCR",
        "PySide6-Essentials",
        "httpx",
        "pytest",
    ):
        assert name in names


def test_dependencies_have_versions() -> None:
    rows = python_dependencies()
    runtime = [r for r in rows if r[2] == "runtime"]
    assert rows[: len(runtime)] == runtime  # runtime first
    assert dict((n, v) for n, v, _ in rows)["httpx"] == metadata.version("httpx")
    assert all(v for _, v, _ in all_dependencies())


def test_missing_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(metadata, "requires", lambda dist: ["nonexistent-pkg==1.0"])
    assert python_dependencies() == [("nonexistent-pkg", "not installed", "runtime")]
    monkeypatch.setattr(metadata, "requires", lambda dist: None)
    assert python_dependencies() == []
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert about.tesseract_version() == "not installed"
    real = builtins.__import__

    def no_gi(name: str, *args: object, **kw: object) -> object:
        if name == "gi":
            raise ImportError(name)
        return real(name, *args, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", no_gi)
    assert about.gstreamer_version() == "not installed"


def test_tesseract_version_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        stdout = ""
        stderr = ""

    monkeypatch.setattr(shutil, "which", lambda name: "/bin/tesseract")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Result())
    assert about.tesseract_version() == "unknown"


def test_screenshot_with_about(qtbot: QtBot, tmp_path: Path) -> None:
    out, dialog = tmp_path / "ui.png", tmp_path / "about.png"
    assert (
        main(["--config-dir", str(tmp_path), "screenshot", str(out), "--about", str(dialog)]) == 0
    )
    with Image.open(dialog) as image:
        assert image.width >= 400
