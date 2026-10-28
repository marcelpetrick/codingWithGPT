# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""About dialog: author, license, disclaimer and every dependency with its installed version."""

import platform
import re
import shutil
import subprocess
from importlib import metadata

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linkedin_reply_assistant.version import __version__

DIST = "linkedin-reply-assistant"
ABOUT_HTML = f"""
<h2>LinkedIn Reply Assistant {__version__}</h2>
<p>Built by <b>Marcel Petrick</b>
(<a href="mailto:mail@marcelpetrick.it">mail@marcelpetrick.it</a>).</p>
<p>License: <b>GNU GPLv3 or later</b>.
<a href="https://www.gnu.org/licenses/gpl-3.0.html">gnu.org/licenses/gpl-3.0</a></p>
<p><b>Use at your own risk.</b> This is a thought prototype, not a product. It comes with no
warranty. It never sends a message: you review every draft and press Send in LinkedIn yourself.</p>
"""


def _requirement_name(requirement: str) -> str:
    return re.split(r"[\s;=<>!~\[]", requirement, maxsplit=1)[0]


def python_dependencies(dist: str = DIST) -> list[tuple[str, str, str]]:
    """(name, installed version, kind) for each declared requirement of the package."""
    rows = []
    for requirement in metadata.requires(dist) or []:
        kind = "development" if "extra ==" in requirement else "runtime"
        name = _requirement_name(requirement)
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            version = "not installed"
        rows.append((name, version, kind))
    return sorted(rows, key=lambda row: (row[2] != "runtime", row[0].lower()))


def tesseract_version() -> str:
    if shutil.which("tesseract") is None:
        return "not installed"
    result = subprocess.run(
        ["tesseract", "--version"], capture_output=True, text=True, timeout=10, check=False
    )
    first = (result.stdout or result.stderr).splitlines()
    return first[0].removeprefix("tesseract ").strip() if first else "unknown"


def gstreamer_version() -> str:
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        Gst.init(None)
        return str(Gst.version_string()).removeprefix("GStreamer ")
    except ImportError, ValueError:
        return "not installed"


def all_dependencies() -> list[tuple[str, str, str]]:
    system = [
        ("Python", platform.python_version(), "platform"),
        ("Qt", qVersion(), "platform"),
        ("PySide6 (bindings)", pyside_version, "platform"),
        ("GStreamer", gstreamer_version(), "system"),
        ("Tesseract OCR", tesseract_version(), "system"),
    ]
    return system + python_dependencies()


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About LinkedIn Reply Assistant")
        self.resize(560, 620)
        layout = QVBoxLayout(self)
        text = QLabel(ABOUT_HTML)
        text.setWordWrap(True)
        text.setOpenExternalLinks(True)
        layout.addWidget(text)
        layout.addWidget(QLabel("<b>Dependencies</b> (installed versions):"))
        rows = all_dependencies()
        self.table = QTableWidget(len(rows), 3)
        self.table.setHorizontalHeaderLabels(["Component", "Version", "Kind"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
