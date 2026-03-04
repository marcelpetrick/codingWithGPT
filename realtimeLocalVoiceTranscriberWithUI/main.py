#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
/**
 * @file main.py
 * @brief Application entrypoint: sets up Qt app, controller, and GUI.
 */
"""

from __future__ import annotations

import sys
from PyQt6 import QtWidgets

from model_handler import APP_VERSION, _info, init_audio_backend
from gui import MainWindow


def main() -> int:
    """
    /**
     * @brief Application entrypoint.
     * @return Qt exit code.
     */
    """
    _info(f"Starting application (version {APP_VERSION})")

    # Defensive: ensure sounddevice / PortAudio has a chance to initialize.
    init_audio_backend()

    app = QtWidgets.QApplication(sys.argv)

    win = MainWindow(app_version=APP_VERSION)
    win.show()

    _info("GUI started")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
