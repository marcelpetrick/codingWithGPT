#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
/**
 * @file main.py
 * @brief PyQt6 offline, streaming speech-to-text using Vosk + sounddevice.
 *
 * Features:
 *  - Uses default microphone by default; optional device picker.
 *  - Start/Stop recording on demand.
 *  - Streaming (partial + final) transcription while recording (offline).
 *  - Robust threading: audio/transcription runs off the GUI thread.
 *  - Defensive error handling: never crash; prints warnings/errors to stdout.
 *
 * Requirements:
 *  - A Vosk model directory available locally (e.g. ./model or env VOSK_MODEL_PATH).
 *
 * Notes:
 *  - Audio format: 16 kHz, mono, 16-bit PCM (typical for Vosk).
 *  - This app does not upload audio anywhere; recognition is local.
 */
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
import sounddevice as sd
from PyQt6 import QtCore, QtGui, QtWidgets

try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
except Exception as exc:  # pragma: no cover
    print(f"[ERROR] Failed to import vosk. Is it installed? Details: {exc}")
    raise


# --------------------------- Version ---------------------------

APP_VERSION = "0.1.0"  # SemVer, update manually as needed


# --------------------------- Utilities ---------------------------

def _warn(msg: str) -> None:
    print(f"[WARN] {msg}", flush=True)


def _err(msg: str) -> None:
    print(f"[ERROR] {msg}", flush=True)


def _info(msg: str) -> None:
    print(f"[INFO] {msg}", flush=True)


def _default_model_path() -> Optional[Path]:
    env = os.environ.get("VOSK_MODEL_PATH", "").strip()
    candidates: List[Path] = []
    if env:
        candidates.append(Path(env))
    candidates.append(Path.cwd() / "model")

    for p in candidates:
        if p.is_dir():
            return p
    return None


def list_input_devices() -> List[Tuple[int, str]]:
    _info("Querying audio input devices")
    out: List[Tuple[int, str]] = []
    try:
        devices = sd.query_devices()
        for idx, d in enumerate(devices):
            if int(d.get("max_input_channels", 0)) > 0:
                name = d.get("name", f"Device {idx}")
                hostapi = d.get("hostapi", None)
                api_name = ""
                try:
                    if hostapi is not None:
                        api_name = sd.query_hostapis()[hostapi].get("name", "")
                except Exception:
                    api_name = ""
                label = f"{idx}: {name}" + (f" [{api_name}]" if api_name else "")
                out.append((idx, label))
    except Exception as exc:
        _warn(f"Could not query input devices: {exc}")
    _info(f"Found {len(out)} input devices")
    return out


# --------------------------- Worker ---------------------------

@dataclass(frozen=True)
class AudioConfig:
    samplerate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    blocksize: int = 8000


class TranscriberWorker(QtCore.QObject):

    partial_text = QtCore.pyqtSignal(str)
    final_text = QtCore.pyqtSignal(str)
    status = QtCore.pyqtSignal(str)
    fatal_error = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._stop_event = threading.Event()
        self._audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=50)
        self._stream: Optional[sd.RawInputStream] = None
        self._recognizer: Optional[KaldiRecognizer] = None
        self._model: Optional[Model] = None
        self._cfg = AudioConfig()

    @QtCore.pyqtSlot(str, int)
    def start(self, model_dir: str, device_index: int) -> None:

        _info(f"Worker start requested (device_index={device_index})")

        if self._stream is not None:
            self.status.emit("Already running.")
            _warn("Worker already running")
            return

        self._stop_event.clear()
        SetLogLevel(-1)

        try:
            model_path = Path(model_dir).expanduser().resolve()
            if not model_path.is_dir():
                raise FileNotFoundError(f"Model dir not found: {model_path}")

            _info(f"Loading Vosk model from: {model_path}")
            self.status.emit(f"Loading model: {model_path}")

            self._model = Model(str(model_path))
            _info("Model successfully loaded")

            self._recognizer = KaldiRecognizer(self._model, self._cfg.samplerate)

            try:
                self._recognizer.SetWords(True)
            except Exception:
                pass

        except Exception as exc:
            msg = f"Failed to initialize recognizer/model: {exc}"
            _err(msg)
            self.fatal_error.emit(msg)
            self._cleanup()
            return

        def _audio_callback(indata, frames: int, time_info, status) -> None:
            if status:
                _warn(f"Audio callback status: {status}")
            if self._stop_event.is_set():
                return

            try:
                data = bytes(indata)
                self._audio_q.put_nowait(data)
            except queue.Full:
                _warn("Audio queue full; dropping audio chunk.")
            except Exception as exc:
                _warn(f"Audio callback error: {exc}")

        try:
            device = None if device_index < 0 else device_index

            _info(f"Opening microphone stream (device={device})")

            self._stream = sd.RawInputStream(
                samplerate=self._cfg.samplerate,
                blocksize=self._cfg.blocksize,
                device=device,
                dtype=self._cfg.dtype,
                channels=self._cfg.channels,
                callback=_audio_callback,
            )

            self._stream.start()

            _info("Audio stream started")

            self.status.emit("Recording… (offline transcription running)")

        except Exception as exc:
            msg = f"Failed to start audio stream: {exc}"
            _err(msg)
            self.fatal_error.emit(msg)
            self._cleanup()
            return

        try:
            self._run_loop()
        finally:
            _info("Worker stopping")
            self._cleanup()
            self.status.emit("Stopped.")

    @QtCore.pyqtSlot()
    def stop(self) -> None:
        _info("Worker stop requested")
        self._stop_event.set()

    def _run_loop(self) -> None:

        if self._recognizer is None:
            raise RuntimeError("Recognizer not initialized.")

        last_partial_emit = 0.0

        while not self._stop_event.is_set():
            try:
                chunk = self._audio_q.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                if not isinstance(chunk, (bytes, bytearray)):
                    chunk = bytes(chunk)

                accepted = self._recognizer.AcceptWaveform(chunk)

                if accepted:
                    res = json.loads(self._recognizer.Result() or "{}")
                    text = (res.get("text") or "").strip()

                    if text:
                        _info(f"Final transcription: {text}")
                        self.final_text.emit(text)

                else:
                    now = time.time()

                    if now - last_partial_emit >= 0.10:
                        pres = json.loads(self._recognizer.PartialResult() or "{}")
                        ptxt = (pres.get("partial") or "").strip()

                        if ptxt:
                            _info(f"Partial transcription: {ptxt}")

                        self.partial_text.emit(ptxt)
                        last_partial_emit = now

            except Exception as exc:
                _warn(f"Transcription error (continuing): {exc}")

        try:
            res = json.loads(self._recognizer.FinalResult() or "{}")
            text = (res.get("text") or "").strip()

            if text:
                _info(f"Final transcription after stop: {text}")
                self.final_text.emit(text)

        except Exception as exc:
            _warn(f"Finalization error: {exc}")

    def _cleanup(self) -> None:

        _info("Cleaning up audio/transcription resources")

        try:
            if self._stream is not None:
                try:
                    self._stream.stop()
                except Exception:
                    pass

                try:
                    self._stream.close()
                except Exception:
                    pass
        finally:
            self._stream = None
            self._recognizer = None
            self._model = None

            try:
                while True:
                    self._audio_q.get_nowait()
            except queue.Empty:
                pass


# --------------------------- GUI ---------------------------

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        _info("Initializing main window")

        self.setWindowTitle(f"Offline Transcription (Vosk + PyQt6) v{APP_VERSION}")
        self.resize(900, 600)

        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[TranscriberWorker] = None

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

        self.model_browse_btn.clicked.connect(self._browse_model_dir)
        self.refresh_devices_btn.clicked.connect(self._populate_devices)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)

        self._populate_devices()

        mp = _default_model_path()
        if mp:
            _info(f"Using default model path: {mp}")
            self.model_path_edit.setText(str(mp))
        else:
            _warn("No default Vosk model found.")

        if self.device_combo.count() == 0:
            self.device_combo.addItem("Default input device", -1)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:

        _info("Application window closing")

        try:
            self._stop()
        except Exception as exc:
            _warn(f"Error during shutdown: {exc}")

        super().closeEvent(event)

    def _browse_model_dir(self) -> None:
        _info("User opened model directory dialog")

        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Vosk model directory"
        )

        if d:
            _info(f"User selected model directory: {d}")
            self.model_path_edit.setText(d)
            self.start_btn.setEnabled(True)

    def _populate_devices(self) -> None:
        _info("Refreshing microphone device list")

        current_data = self.device_combo.currentData()

        self.device_combo.clear()
        self.device_combo.addItem("Default input device", -1)

        devices = list_input_devices()

        for idx, label in devices:
            self.device_combo.addItem(label, idx)

        if current_data is not None:
            i = self.device_combo.findData(current_data)
            if i >= 0:
                self.device_combo.setCurrentIndex(i)

    def _append_final(self, text: str) -> None:
        if not text:
            return
        self.text_out.appendPlainText(text)

    def _set_partial(self, text: str) -> None:
        self.partial_label.setText(text or "")

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _on_fatal(self, msg: str) -> None:
        _err(f"Fatal worker error: {msg}")
        self._set_status(msg)
        self._stop_ui_only()

    def _start(self) -> None:

        _info("User pressed START recording")

        model_dir = self.model_path_edit.text().strip()

        if not model_dir:
            self._set_status("Please select a Vosk model directory.")
            self.start_btn.setEnabled(False)
            return

        model_path = Path(model_dir).expanduser()

        if not model_path.is_dir():
            self._set_status(f"Model dir does not exist: {model_path}")
            _err(f"Model dir does not exist: {model_path}")
            return

        if self._thread is not None:
            _warn("Thread already exists; ignoring start.")
            return

        device_index = int(self.device_combo.currentData() or -1)

        _info(f"Starting worker thread (device_index={device_index})")

        self._thread = QtCore.QThread(self)
        self._worker = TranscriberWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(
            lambda: self._worker.start(model_dir, device_index)
        )

        self._worker.partial_text.connect(self._set_partial)
        self._worker.final_text.connect(self._append_final)
        self._worker.status.connect(self._set_status)
        self._worker.fatal_error.connect(self._on_fatal)

        self._thread.finished.connect(self._thread.deleteLater)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.device_combo.setEnabled(False)
        self.refresh_devices_btn.setEnabled(False)
        self.model_path_edit.setEnabled(False)
        self.model_browse_btn.setEnabled(False)

        self._thread.start()

    def _stop(self) -> None:

        _info("User pressed STOP recording")

        if self._worker is not None:
            try:
                self._worker.stop()
            except Exception as exc:
                _warn(f"Failed to request stop: {exc}")

        if self._thread is not None:
            self._thread.quit()

            if not self._thread.wait(2500):
                _warn("Worker thread did not exit in time; terminating.")
                self._thread.terminate()
                self._thread.wait(1000)

        self._stop_ui_only()

    def _stop_ui_only(self) -> None:

        _info("Resetting UI after stop")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.refresh_devices_btn.setEnabled(True)
        self.model_path_edit.setEnabled(True)
        self.model_browse_btn.setEnabled(True)

        self._set_partial("")

        self._worker = None
        self._thread = None


# --------------------------- Entrypoint ---------------------------

def main() -> int:

    _info(f"Starting application (version {APP_VERSION})")

    try:
        sd.default.reset()
    except Exception as exc:
        _warn(f"Audio backend init warning: {exc}")

    app = QtWidgets.QApplication(sys.argv)

    w = MainWindow()
    w.show()

    _info("GUI started")

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
