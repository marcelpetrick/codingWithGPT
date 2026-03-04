#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
/**
 * @file model_handler.py
 * @brief Audio capture + offline streaming transcription (Vosk) + threading controller.
 *
 * Design:
 *  - TranscriberWorker: runs inside a QThread; owns the PortAudio stream + Vosk recognizer.
 *  - TranscriptionController: lives in GUI thread; manages worker thread lifecycle and
 *    forwards worker signals.
 */
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import sounddevice as sd
from PyQt6 import QtCore

try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
except Exception as exc:  # pragma: no cover
    print(f"[ERROR] Failed to import vosk. Is it installed? Details: {exc}", flush=True)
    raise


# --------------------------- Version ---------------------------

APP_VERSION = "0.1.4"  # SemVer; update manually as needed.


# --------------------------- Logging ---------------------------

def _warn(msg: str) -> None:
    """Print a warning to stdout."""
    print(f"[WARN] {msg}", flush=True)


def _err(msg: str) -> None:
    """Print an error to stdout."""
    print(f"[ERROR] {msg}", flush=True)


def _info(msg: str) -> None:
    """Print info to stdout."""
    print(f"[INFO] {msg}", flush=True)


def init_audio_backend() -> None:
    """
    /**
     * @brief Try to initialize / reset PortAudio defaults defensively.
     *
     * This helps surface audio backend issues early and avoids surprises later.
     */
    """
    try:
        sd.default.reset()
    except Exception as exc:
        _warn(f"Audio backend init warning: {exc}")


# --------------------------- Helpers ---------------------------

def default_model_path() -> Optional[Path]:
    """
    /**
     * @brief Determine a sensible default Vosk model directory.
     * @return Path to model directory, or None if not found.
     */
    """
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
    """
    /**
     * @brief List available audio *input* devices as (device_index, display_name).
     */
    """
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
    """
    /**
     * @brief Audio capture configuration (Vosk-friendly).
     */
    """
    samplerate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    blocksize: int = 8000  # ~0.5s at 16kHz mono int16


class TranscriberWorker(QtCore.QObject):
    """
    /**
     * @brief Runs in a QThread. Owns microphone stream + Vosk recognizer loop.
     *
     * Signals are emitted from the worker thread; the controller connects them with
     * QueuedConnection so GUI updates are safe.
     */
    """

    partial_text = QtCore.pyqtSignal(str)
    final_text = QtCore.pyqtSignal(str)
    status = QtCore.pyqtSignal(str)
    fatal_error = QtCore.pyqtSignal(str)

    def __init__(self, cfg: Optional[AudioConfig] = None) -> None:
        super().__init__()
        self._cfg = cfg or AudioConfig()

        self._stop_event = threading.Event()
        self._audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=50)

        self._stream: Optional[sd.RawInputStream] = None
        self._recognizer: Optional[KaldiRecognizer] = None
        self._model: Optional[Model] = None

    @QtCore.pyqtSlot(str, int)
    def run(self, model_dir: str, device_index: int) -> None:
        """
        /**
         * @brief Worker main entry: load model, start stream, run recognition loop.
         * @param model_dir Vosk model root directory.
         * @param device_index sounddevice device index, or -1 for default.
         */
        """
        _info(f"Worker run requested (device_index={device_index})")
        self._stop_event.clear()
        SetLogLevel(-1)  # keep Vosk quieter; we log ourselves.

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
            # PortAudio callback: keep it fast, never touch Qt here.
            if status:
                _warn(f"Audio callback status: {status}")
            if self._stop_event.is_set():
                return
            try:
                # IMPORTANT: force a real bytes object (fixes cffi buffer issues)
                self._audio_q.put_nowait(bytes(indata))
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
        """
        /**
         * @brief Request the worker to stop. Recognition loop exits shortly.
         */
        """
        _info("Worker stop requested")
        self._stop_event.set()

    def _run_loop(self) -> None:
        """
        /**
         * @brief Consume audio from queue and feed Vosk recognizer incrementally.
         */
        """
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

        # Flush final result on stop
        try:
            res = json.loads(self._recognizer.FinalResult() or "{}")
            text = (res.get("text") or "").strip()
            if text:
                _info(f"Final transcription after stop: {text}")
                self.final_text.emit(text)
        except Exception as exc:
            _warn(f"Finalization error: {exc}")

    def _cleanup(self) -> None:
        """
        /**
         * @brief Cleanup stream and internal state safely.
         */
        """
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

            # Drain queue
            try:
                while True:
                    self._audio_q.get_nowait()
            except queue.Empty:
                pass


# --------------------------- Controller ---------------------------

class TranscriptionController(QtCore.QObject):
    """
    /**
     * @brief GUI-thread controller that manages the worker thread lifecycle.
     *
     * Responsibilities:
     *  - start/stop (non-blocking) transcription
     *  - forward worker signals to GUI via queued connections
     *  - prevent UI freezes on stop by polling instead of blocking waits
     */
    """

    partial_text = QtCore.pyqtSignal(str)
    final_text = QtCore.pyqtSignal(str)
    status = QtCore.pyqtSignal(str)
    fatal_error = QtCore.pyqtSignal(str)
    running_changed = QtCore.pyqtSignal(bool)

    # used to invoke worker.run() in the worker thread (queued)
    start_requested = QtCore.pyqtSignal(str, int)

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[TranscriberWorker] = None

        self._stop_timer: Optional[QtCore.QTimer] = None
        self._stop_deadline: float = 0.0
        self._finalized_stop: bool = False

    def is_running(self) -> bool:
        t = self._thread
        if t is None:
            return False
        try:
            return t.isRunning()
        except RuntimeError:
            # Underlying C++ object already deleted
            return False

    def start(self, model_dir: str, device_index: int) -> None:
        """
        /**
         * @brief Start transcription asynchronously.
         */
        """
        if self._thread is not None:
            _warn("Controller: start requested while already running; ignoring.")
            return

        # ensure any stale stop timer state is cleared
        if self._stop_timer is not None and self._stop_timer.isActive():
            self._stop_timer.stop()

        self._finalized_stop = False

        _info(f"Controller: starting (device_index={device_index})")

        self._thread = QtCore.QThread(self)
        self._worker = TranscriberWorker()
        self._worker.moveToThread(self._thread)

        # Forward signals (queued => GUI safe)
        self._worker.partial_text.connect(
            self.partial_text, type=QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._worker.final_text.connect(
            self.final_text, type=QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._worker.status.connect(
            self.status, type=QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._worker.fatal_error.connect(
            self.fatal_error, type=QtCore.Qt.ConnectionType.QueuedConnection
        )

        # Start worker.run() via queued invocation into the worker thread
        self.start_requested.connect(
            self._worker.run,
            type=QtCore.Qt.ConnectionType.QueuedConnection,
        )

        # When the thread finishes, finalize stop (Qt-native Option C)
        self._thread.finished.connect(self._on_thread_finished)

        # It's fine to deleteLater; we guard against touching deleted objects.
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

        # Kick off worker after thread event loop is running
        self.start_requested.emit(model_dir, device_index)

        self.running_changed.emit(True)

    def stop(self) -> None:
        """
        /**
         * @brief Request stop without blocking the GUI thread.
         */
        """
        if self._thread is None:
            return

        _info("Controller: stop requested")

        if self._worker is not None:
            try:
                self._worker.stop()
            except Exception as exc:
                _warn(f"Controller: failed to request worker stop: {exc}")

        # Ask the thread event loop to exit; worker should naturally stop shortly.
        try:
            self._thread.quit()
        except Exception:
            pass

        if self._stop_timer is None:
            self._stop_timer = QtCore.QTimer(self)
            self._stop_timer.setInterval(50)
            self._stop_timer.timeout.connect(self._poll_stop)

        # watchdog deadline (fallback)
        self._stop_deadline = time.monotonic() + 2.5
        self._stop_timer.start()

    @QtCore.pyqtSlot()
    def _on_thread_finished(self) -> None:
        # Normal completion path: stop polling and finalize exactly once.
        if self._stop_timer is not None and self._stop_timer.isActive():
            self._stop_timer.stop()
        self._finalize_stop()

    def _poll_stop(self) -> None:
        # Fallback watchdog: never crash if QThread object was deleted.
        if self._finalized_stop:
            if self._stop_timer is not None and self._stop_timer.isActive():
                self._stop_timer.stop()
            return

        t = self._thread
        if t is None:
            if self._stop_timer is not None:
                self._stop_timer.stop()
            self._finalize_stop()
            return

        try:
            running = t.isRunning()
        except RuntimeError:
            # underlying C++ object deleted (this was your crash)
            running = False

        if not running:
            _info("Controller: worker thread stopped cleanly")
            if self._stop_timer is not None:
                self._stop_timer.stop()
            self._finalize_stop()
            return

        if time.monotonic() >= self._stop_deadline:
            _warn("Controller: worker thread did not exit in time; terminating.")
            try:
                t.terminate()
            except Exception as exc:
                _warn(f"Controller: terminate failed: {exc}")
            try:
                t.wait(1000)
            except Exception:
                pass
            if self._stop_timer is not None:
                self._stop_timer.stop()
            self._finalize_stop()

    def _finalize_stop(self) -> None:
        # Must be idempotent; can be called by finished-signal or watchdog.
        if self._finalized_stop:
            return
        self._finalized_stop = True

        # Disconnect start_requested from the old worker to avoid stacking connections on restart.
        if self._worker is not None:
            try:
                self.start_requested.disconnect(self._worker.run)
            except Exception:
                pass

        self._worker = None
        self._thread = None
        self.running_changed.emit(False)
