#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Application entrypoint: sets up Qt app, controller, and GUI.
"""

from __future__ import annotations

import sys
from PyQt6 import QtCore, QtWidgets

from model_handler import APP_VERSION, _info, init_audio_backend
from gui import MainWindow


def main() -> int:
    _info(f"Starting application (version {APP_VERSION})")

    # Initialize audio backend
    init_audio_backend()

    # Create QApplication first
    app = QtWidgets.QApplication(sys.argv)

    # IMPORTANT: define a stable application name so QStandardPaths
    # writes settings to ~/.config/realtimeLocalVoiceTranscriptionWithUI/
    QtCore.QCoreApplication.setApplicationName(
        "realtimeLocalVoiceTranscriptionWithUI"
    )

    win = MainWindow(app_version=APP_VERSION)
    win.show()

    _info("GUI started")

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
