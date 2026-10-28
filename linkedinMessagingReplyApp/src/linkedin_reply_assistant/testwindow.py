# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic LinkedIn-like "Capture Test Window" (VISION §23.2).

It shows a conversation in a layout like LinkedIn messaging: a noisy sidebar, a thread title,
messages with sender and time, and a composer. It serves live portal capture tests and renders
the OCR fixtures (light/dark theme, zoom, high-DPI) without LinkedIn.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linkedin_reply_assistant.model import Conversation

TITLE = "LRA Capture Test Window"
THEMES = {
    "light": {
        "bg": "#f4f2ee",
        "panel": "#ffffff",
        "text": "#191919",
        "muted": "#666666",
        "line": "#e0dfdc",
        "accent": "#0a66c2",
    },
    "dark": {
        "bg": "#000000",
        "panel": "#1b1f23",
        "text": "#e9e9e9",
        "muted": "#a0a0a0",
        "line": "#38434f",
        "accent": "#71b7fb",
    },
}
SIDEBAR = [
    "Ad: Upgrade to Premium",
    "Jobs you may be interested in",
    "Messaging",
    "Search messages",
]


def named[W: QWidget](widget: W, name: str) -> W:
    widget.setObjectName(name)
    return widget


class CaptureTestWindow(QWidget):
    def __init__(self, conversation: Conversation, theme: str = "light", zoom: float = 1.0):
        super().__init__()
        self.setWindowTitle(TITLE)
        colors = THEMES[theme]
        base = QFont("DejaVu Sans")
        base.setPixelSize(round(14 * zoom))
        self.setFont(base)
        self.setStyleSheet(
            f"QWidget {{ background: {colors['bg']}; color: {colors['text']}; }}"
            f"QFrame#panel {{ background: {colors['panel']}; border: 1px solid {colors['line']}; }}"
            f"QLabel {{ background: transparent; }}"
            f"QLabel#muted {{ color: {colors['muted']}; }}"
            f"QLabel#title {{ font-weight: bold; }}"
            f"QTextEdit {{ background: {colors['panel']}; border: 1px solid {colors['line']}; }}"
        )
        layout = QHBoxLayout(self)
        sidebar = named(QFrame(), "panel")
        side = QVBoxLayout(sidebar)
        for entry in SIDEBAR:
            side.addWidget(named(QLabel(entry), "muted"))
        side.addStretch(1)
        layout.addWidget(sidebar, 1)

        thread = named(QFrame(), "panel")
        body = QVBoxLayout(thread)
        title = named(QLabel(conversation.participant), "title")
        title_font = QFont(base)
        title_font.setPixelSize(round(18 * zoom))
        title.setFont(title_font)
        body.addWidget(title)
        for message in conversation.messages:
            header = named(QLabel(f"{message.sender}  {message.time}".strip()), "title")
            text = QLabel(message.text)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            body.addWidget(header)
            body.addWidget(text)
        body.addStretch(1)
        composer = QTextEdit()
        composer.setPlaceholderText("Write a message…")
        composer.setFixedHeight(round(60 * zoom))
        body.addWidget(composer)
        layout.addWidget(thread, 3)
        self.resize(round(900 * zoom), round(560 * zoom))


def render(
    conversation: Conversation,
    path: Path,
    theme: str = "light",
    zoom: float = 1.0,
    dpr: float = 1.0,
) -> None:
    """Render the window offscreen to a PNG (fixtures, docs). Needs a QApplication."""
    window = CaptureTestWindow(conversation, theme, zoom)
    window.show()
    pixmap = window.grab()
    if dpr != 1.0:
        pixmap = pixmap.scaled(
            round(pixmap.width() * dpr),
            round(pixmap.height() * dpr),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    window.close()
    if not pixmap.save(str(path), "PNG"):
        raise OSError(f"cannot write {path}")
