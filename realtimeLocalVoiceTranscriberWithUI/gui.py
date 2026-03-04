#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
/**
 * @file gui.py
 * @brief PyQt6 GUI: device selection, model selection, and transcription display.
 */
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from model_handler import (
    _info,
    _warn,
    _err,
    default_model_path,
    list_input_devices,
    TranscriptionController,
)


class MainWindow(QtWidgets.QMainWindow):
    """
    /**
     * @brief Main application window.
     */
    """

    def __init__(self, app_version: str) -> None:
        super().__init__()

        _info("Initializing main window")

        self.setWindowTitle(f"Offline Transcription (Vosk + PyQt6) v{app_version}")
        self.resize(900, 600)

        self._controller = TranscriptionController(self)

        # Persistent settings (INI file via QSettings)
        config_dir = Path(
            QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.StandardLocation.AppConfigLocation
            )
        )
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If config dir creation fails, QSettings will still try to create the file later.
            pass
        self._settings_path = config_dir / "settings.ini"
        self._settings = QtCore.QSettings(
            str(self._settings_path), QtCore.QSettings.Format.IniFormat
        )

        # Cached values loaded from settings (used during UI init)
        self._saved_model_dir: str = self._settings.value("model/model_dir", "", type=str)
        try:
            self._saved_device_index: int = int(
                self._settings.value("audio/device_index", -1)
            )
        except Exception:
            self._saved_device_index = -1

        # Widgets
        self.model_path_edit = QtWidgets.QLineEdit()
        self.model_browse_btn = QtWidgets.QPushButton("Browse…")

        self.device_combo = QtWidgets.QComboBox()
        self.refresh_devices_btn = QtWidgets.QPushButton("Refresh devices")

        self.start_btn = QtWidgets.QPushButton("Start recording")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.status_label = QtWidgets.QLabel("Ready.")
        self.status_label.setWordWrap(True)

        self.partial_label = QtWidgets.QLabel("")
        self.partial_label.setStyleSheet("font-style: italic;")
        self.partial_label.setWordWrap(True)

        self.text_out = QtWidgets.QPlainTextEdit()
        self.text_out.setReadOnly(True)
        self.text_out.setPlaceholderText("Final transcription will appear here…")

        # Layout
        top = QtWidgets.QWidget()
        self.setCentralWidget(top)
        layout = QtWidgets.QVBoxLayout(top)

        model_row = QtWidgets.QHBoxLayout()
        model_row.addWidget(QtWidgets.QLabel("Vosk model dir:"))
        model_row.addWidget(self.model_path_edit, 1)
        model_row.addWidget(self.model_browse_btn)
        layout.addLayout(model_row)

        dev_row = QtWidgets.QHBoxLayout()
        dev_row.addWidget(QtWidgets.QLabel("Input device:"))
        dev_row.addWidget(self.device_combo, 1)
        dev_row.addWidget(self.refresh_devices_btn)
        layout.addLayout(dev_row)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        layout.addWidget(QtWidgets.QLabel("Partial:"))
        layout.addWidget(self.partial_label)
        layout.addWidget(QtWidgets.QLabel("Final:"))
        layout.addWidget(self.text_out, 1)
        layout.addWidget(self.status_label)

        # GUI signals
        self.model_browse_btn.clicked.connect(self._browse_model_dir)
        self.refresh_devices_btn.clicked.connect(self._populate_devices)
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)

        # Persist user choices
        self.model_path_edit.editingFinished.connect(self._save_model_dir)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

        # Controller signals
        self._controller.partial_text.connect(self._set_partial)
        self._controller.final_text.connect(self._append_final)
        self._controller.status.connect(self._set_status)
        self._controller.fatal_error.connect(self._on_fatal)
        self._controller.running_changed.connect(self._set_running_state)

        # Initialize defaults (restore persisted choices first)
        self._populate_devices()
        self._init_default_model_path()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        /**
         * @brief Ensure worker is stopped before exiting.
         */
        """
        _info("Application window closing")
        try:
            self._controller.stop()
        except Exception as exc:
            _warn(f"Error during shutdown: {exc}")
        super().closeEvent(event)

    # --------------------------- UI init ---------------------------

    def _init_default_model_path(self) -> None:
        # 1) Prefer persisted model dir (if still valid)
        saved = (self._saved_model_dir or "").strip()
        if saved:
            sp = Path(saved).expanduser()
            if sp.is_dir():
                _info(f"Restoring persisted model path: {sp}")
                self.model_path_edit.setText(str(sp))
                self.start_btn.setEnabled(True)
                return
            _warn(f"Persisted model path no longer exists: {sp}")

        # 2) Fall back to auto-detected default
        mp = default_model_path()
        if mp:
            _info(f"Using default model path: {mp}")
            self.model_path_edit.setText(str(mp))
            self.start_btn.setEnabled(True)
            # Don't overwrite a user's previous choice unless they change it.
        else:
            _warn("No default Vosk model found. Set VOSK_MODEL_PATH or put a model in ./model.")
            self.status_label.setText("No model dir found. Set VOSK_MODEL_PATH or put a model in ./model.")
            self.start_btn.setEnabled(False)

    def _populate_devices(self) -> None:
        _info("Refreshing microphone device list")

        # Prefer the currently selected device; otherwise fall back to persisted choice.
        preferred = self.device_combo.currentData()
        if preferred is None:
            preferred = self._saved_device_index

        self.device_combo.blockSignals(True)
        try:
            self.device_combo.clear()
            self.device_combo.addItem("Default input device", -1)

            for idx, label in list_input_devices():
                self.device_combo.addItem(label, idx)

            i = self.device_combo.findData(preferred)
            if i >= 0:
                self.device_combo.setCurrentIndex(i)
            else:
                # If the saved device no longer exists, fall back to default.
                self.device_combo.setCurrentIndex(0)
        finally:
            self.device_combo.blockSignals(False)

    # --------------------------- Persistence ---------------------------

    def _save_model_dir(self) -> None:
        """Persist the currently entered model directory to the INI file."""
        model_dir = self.model_path_edit.text().strip()
        if not model_dir:
            return
        self._settings.setValue("model/model_dir", model_dir)
        self._settings.sync()
        self._saved_model_dir = model_dir
        _info(f"Persisted model path to settings: {model_dir}")

    def _save_device_index(self, device_index: int) -> None:
        """Persist the selected input device index to the INI file."""
        self._settings.setValue("audio/device_index", int(device_index))
        self._settings.sync()
        self._saved_device_index = int(device_index)
        _info(f"Persisted device index to settings: {device_index}")

    @QtCore.pyqtSlot(int)
    def _on_device_changed(self, _: int) -> None:
        """Handle device selection changes (stdout + persistence)."""
        device_index = int(self.device_combo.currentData() or -1)
        device_label = self.device_combo.currentText()

        # Explicit stdout output as requested (in addition to internal logging)
        print(f"Selected input device: {device_label} (device_index={device_index})", flush=True)

        self._save_device_index(device_index)

# --------------------------- User actions ---------------------------

    def _browse_model_dir(self) -> None:
        _info("User opened model directory dialog")
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Vosk model directory")
        if d:
            _info(f"User selected model directory: {d}")
            self.model_path_edit.setText(d)
            self.start_btn.setEnabled(True)
            self._save_model_dir()

    def _on_start_clicked(self) -> None:
        _info("User pressed START recording")

        model_dir = self.model_path_edit.text().strip()
        if not model_dir:
            self._set_status("Please select a Vosk model directory.")
            self.start_btn.setEnabled(False)
            return

        model_path = Path(model_dir).expanduser()
        if not model_path.is_dir():
            msg = f"Model dir does not exist: {model_path}"
            self._set_status(msg)
            _err(msg)
            return

        device_index = int(self.device_combo.currentData() or -1)
        _info(f"Starting transcription (device_index={device_index})")

        # Persist the last used values
        self._save_model_dir()
        self._save_device_index(device_index)

        self._controller.start(model_dir=model_dir, device_index=device_index)

    def _on_stop_clicked(self) -> None:
        _info("User pressed STOP recording")
        self._controller.stop()

    # --------------------------- UI updates ---------------------------

    @QtCore.pyqtSlot(bool)
    def _set_running_state(self, running: bool) -> None:
        # Enable/disable controls depending on state.
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

        self.device_combo.setEnabled(not running)
        self.refresh_devices_btn.setEnabled(not running)
        self.model_path_edit.setEnabled(not running)
        self.model_browse_btn.setEnabled(not running)

        if not running:
            self._set_partial("")

    @QtCore.pyqtSlot(str)
    def _append_final(self, text: str) -> None:
        if not text:
            return
        self.text_out.appendPlainText(text)

    @QtCore.pyqtSlot(str)
    def _set_partial(self, text: str) -> None:
        self.partial_label.setText(text or "")

    @QtCore.pyqtSlot(str)
    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    @QtCore.pyqtSlot(str)
    def _on_fatal(self, msg: str) -> None:
        _err(f"Fatal worker error: {msg}")
        self._set_status(msg)
        # Ensure UI recovers even on worker failure.
        self._set_running_state(False)
