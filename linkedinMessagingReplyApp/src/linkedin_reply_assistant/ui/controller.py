# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Qt controller: runs commands in worker threads and keeps the workflow on the GUI thread.

Workers never touch widgets or the workflow. They post a callable back to the GUI thread, and the
workflow drops results of superseded sequences. Button and hotkey call the same `capture_and_draft`.
"""

import contextlib
import shutil
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, Qt, Signal, Slot

from linkedin_reply_assistant.backends.base import BackendError
from linkedin_reply_assistant.backends.manager import BackendManager, NoBackendError
from linkedin_reply_assistant.browser_bridge.inserter import Inserter, InsertOutcome
from linkedin_reply_assistant.browser_bridge.server import BridgeError
from linkedin_reply_assistant.cancel import Cancelled
from linkedin_reply_assistant.capture.frame import Capture
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.capture.source import CaptureError, CaptureSource
from linkedin_reply_assistant.config.loader import Config
from linkedin_reply_assistant.diagnostics.preflight import Check
from linkedin_reply_assistant.events import EventLog
from linkedin_reply_assistant.extraction.base import ExtractionError, ExtractionResult
from linkedin_reply_assistant.pipeline import Pipeline, Timings, run_full
from linkedin_reply_assistant.portal.bus import PortalError
from linkedin_reply_assistant.reply_engine.generator import Draft, GenerationError
from linkedin_reply_assistant.shortcuts.base import ShortcutService, ShortcutStatus
from linkedin_reply_assistant.state.settings import Settings, save_settings
from linkedin_reply_assistant.state.workflow import State, Workflow, WorkflowError

ALL_BACKENDS_DOWN = (
    "All AI backends are unavailable. The capture and text are kept; press Regenerate."
)
REVIEW = "Extraction needs review: edit the text, then Regenerate."
EXTENSION_DOWN = "Browser extension not connected. Use Copy Draft and paste in LinkedIn."


class SourceSelector(Protocol):
    """Opens a capture source. `restore_token` may skip the picker; returns (source, new token)."""

    def __call__(self, restore_token: str | None) -> tuple[CaptureSource, str | None]: ...


@dataclass
class Services:
    config: Config
    manager: BackendManager
    pipeline: Pipeline
    select_source: SourceSelector
    shortcuts: ShortcutService
    inserter: Inserter | None
    bridge_connected: Callable[[], bool]
    preflight: Callable[[], list[Check]]
    settings_path: Path
    debug_dir: Path
    events: EventLog


def friendly_error(exc: BaseException) -> str:
    """Error text for the UI (§21, §29). Never a traceback."""
    if isinstance(exc, NoBackendError):
        return f"{ALL_BACKENDS_DOWN} ({'; '.join(exc.reasons)})"
    if isinstance(exc, BackendError):
        return ALL_BACKENDS_DOWN if not exc.reachable else f"AI backend error: {exc}"
    if isinstance(exc, (CaptureError, ExtractionError, GenerationError, PortalError, BridgeError)):
        return str(exc)
    return f"Unexpected error: {type(exc).__name__}: {exc}"


class Controller(QObject):
    changed = Signal()  # workflow state or data changed
    message = Signal(str)  # status line text
    health = Signal(list)  # list[Check]
    shortcut = Signal(object)  # ShortcutStatus
    confirm_insert = Signal(str)  # question; the UI calls insert(confirmed=True) on yes
    draft_finished = Signal()
    _invoke = Signal(object)

    def __init__(self, services: Services, settings: Settings) -> None:
        super().__init__()
        self.services = services
        self.settings = settings
        self.workflow = Workflow()
        self.source: CaptureSource | None = None
        self.timings: Timings | None = None
        self.shortcut_status = ShortcutStatus(False, None, "Global hotkey: checking…")
        self.last_insert: InsertOutcome | None = None
        self._pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="lra")
        self._invoke.connect(self._run_callable, Qt.ConnectionType.QueuedConnection)

    # --- thread plumbing ----------------------------------------------------------------------

    @Slot(object)
    def _run_callable(self, fn: Callable[[], None]) -> None:
        fn()

    def post(self, fn: Callable[[], None]) -> None:
        """Run `fn` on the GUI thread (safe from any thread)."""
        self._invoke.emit(fn)

    def submit(
        self,
        work: Callable[[], Any],
        done: Callable[[Any], None],
        failed: Callable[[BaseException], None],
    ) -> Future[Any]:
        def run() -> None:
            try:
                value = work()
            except BaseException as exc:  # noqa: BLE001 - every failure is reported in the UI
                error = exc  # `exc` is unbound after the except block; keep a reference
                self.post(lambda: failed(error))
                return
            self.post(lambda: done(value))

        return self._pool.submit(run)

    def shutdown(self) -> None:
        self.workflow.cancel()
        self._pool.shutdown(wait=False, cancel_futures=True)
        for close in (self.services.shortcuts.close, self._close_source):
            with contextlib.suppress(Exception):  # best effort at exit
                close()

    def _close_source(self) -> None:
        if self.source is not None:
            self.source.close()

    def _changed(self, text: str | None = None) -> None:
        if text is not None:
            self.message.emit(text)
        self.changed.emit()

    def save(self) -> None:
        save_settings(self.services.settings_path, self.settings)

    # --- startup ------------------------------------------------------------------------------

    def start(self) -> None:
        """Probe health and shortcuts, and restore the capture source if a token exists."""
        self.refresh_health()
        self.submit(
            lambda: self.services.shortcuts.start(self._on_hotkey),
            self._on_shortcut,
            lambda exc: self._on_shortcut(ShortcutStatus(False, None, friendly_error(exc))),
        )
        if self.settings.restore_token:
            self.select_source(restore=True)

    def refresh_health(self) -> None:
        self.submit(self.services.preflight, self.health.emit, lambda exc: None)

    def _on_shortcut(self, status: ShortcutStatus) -> None:
        self.shortcut_status = status
        if status.binding is not None and status.binding.trigger:
            self.settings.hotkey_trigger = status.binding.trigger
            self.save()
        self.shortcut.emit(status)

    def _on_hotkey(self, shortcut_id: str) -> None:
        """Called on the portal thread. The hotkey runs the same command as the button (§8)."""
        if shortcut_id == self.services.config.app.hotkey.shortcut_id:
            self.post(self.capture_and_draft)

    def configure_hotkey(self, trigger: str) -> None:
        hotkey = self.services.config.app.hotkey
        self.message.emit("Asking the desktop for the global hotkey…")
        self.submit(
            lambda: self.services.shortcuts.bind(hotkey.shortcut_id, hotkey.description, trigger),
            self._on_shortcut,
            lambda exc: self._on_shortcut(ShortcutStatus(False, None, friendly_error(exc))),
        )

    def open_desktop_shortcut_settings(self) -> bool:
        return self.services.shortcuts.configure()

    # --- capture source -----------------------------------------------------------------------

    def select_source(self, restore: bool = False) -> None:
        token = self.settings.restore_token if restore else None
        self.message.emit("Select the browser window in the desktop dialog…")

        def work() -> tuple[CaptureSource, str | None]:
            if self.source is not None:
                self.source.close()
            return self.services.select_source(token)

        def done(value: tuple[CaptureSource, str | None]) -> None:
            self.source, new_token = value
            # Restore tokens are single-use: always keep the newest one (§6.2).
            self.settings.restore_token = new_token
            self.save()
            self.workflow.source_selected()
            self._changed(f"Capture source: {self.source.name}")

        def failed(exc: BaseException) -> None:
            if restore:
                self.settings.restore_token = None
                self.save()
            self.source = None
            self.workflow.source_lost(friendly_error(exc))
            self._changed(f"No capture source: {friendly_error(exc)}")

        self.submit(work, done, failed)

    def set_roi(self, roi: Roi | None) -> None:
        self.settings.roi = roi
        self.save()
        self._changed("Capture region saved." if roi else "Capture region reset: full window.")

    # --- Capture & Draft ----------------------------------------------------------------------

    def capture_and_draft(self) -> None:
        try:
            seq, token = self.workflow.begin_capture()
        except WorkflowError as exc:
            self._changed(str(exc))
            return
        self._changed(f"Capture #{seq}…")
        source, roi = self.source, self.settings.roi

        def on_step(step: str, payload: object) -> None:
            def apply() -> None:
                if isinstance(payload, Capture):
                    self.workflow.captured(seq, payload)
                elif isinstance(payload, tuple):
                    result, usable = cast(tuple[ExtractionResult, bool], payload)
                    if self.workflow.extracted(seq, result, usable) and not usable:
                        self.message.emit(REVIEW)
                elif isinstance(payload, Draft) and self.workflow.drafted(seq, payload):
                    self.draft_finished.emit()
                self.changed.emit()

            self.post(apply)

        def done(timings: Timings) -> None:
            if seq == self.workflow.sequence:
                self.timings = timings
                self._changed(self._done_text(timings))

        def failed(exc: BaseException) -> None:
            if isinstance(exc, Cancelled):
                return
            if isinstance(exc, CaptureError) and seq == self.workflow.active:
                self.workflow.source_lost(str(exc))
                self.source = None
                self._changed(str(exc))
                return
            if self.workflow.failed(seq, friendly_error(exc)):
                self._changed(self.workflow.error)

        self.submit(
            lambda: run_full(self.services.pipeline, seq, source, roi, token, on_step), done, failed
        )

    def _done_text(self, timings: Timings) -> str:
        state = self.workflow.state
        if state == State.EXTRACTION_REVIEW:
            return REVIEW
        return f"{state.value} in {timings.total_ms / 1000:.1f} s."

    def regenerate(self, category: str | None = None) -> None:
        try:
            seq, token = self.workflow.begin_regenerate()
        except WorkflowError as exc:
            self._changed(str(exc))
            return
        self._changed("Generating…")
        result, text = self.workflow.extraction, self.workflow.extracted_text

        def done(draft: Any) -> None:
            if self.workflow.drafted(seq, draft):
                self.draft_finished.emit()
                self._changed("Draft ready.")

        def failed(exc: BaseException) -> None:
            if not isinstance(exc, Cancelled) and self.workflow.failed(seq, friendly_error(exc)):
                self._changed(self.workflow.error)

        self.submit(
            lambda: self.services.pipeline.draft(seq, result, text, token, Timings(), category),
            done,
            failed,
        )

    def cancel(self) -> None:
        if self.workflow.busy:
            self.workflow.cancel()
            self._changed("Cancelled.")

    # --- editing ------------------------------------------------------------------------------

    def edit_extracted_text(self, text: str) -> None:
        before = self.workflow.state
        self.workflow.edit_extracted_text(text)
        if self.workflow.state != before:
            self._changed(self.workflow.stale_reason)

    def edit_draft(self, text: str) -> None:
        before = self.workflow.state
        self.workflow.edit_draft(text)
        if self.workflow.state != before:
            self._changed()

    # --- insertion ----------------------------------------------------------------------------

    @property
    def bridge_connected(self) -> bool:
        return self.services.inserter is not None and self.services.bridge_connected()

    def insert(self, confirmed: bool = False) -> None:
        if not self.bridge_connected:
            self._changed(EXTENSION_DOWN)
            return
        try:
            text = self.workflow.begin_insert()
        except WorkflowError as exc:
            self._changed(str(exc))
            return
        participant = self.workflow.extraction.participant if self.workflow.extraction else None
        inserter = self.services.inserter
        assert inserter is not None
        self._changed("Inserting into LinkedIn…")

        def done(outcome: InsertOutcome) -> None:
            self.last_insert = outcome
            if outcome.needs_confirmation:
                self.workflow.inserted(False, outcome.message)
                self._changed(outcome.message)
                self.confirm_insert.emit(outcome.message)
                return
            self.workflow.inserted(outcome.ok, outcome.message)
            if not outcome.ok and outcome.message.startswith("Conversation changed"):
                self.workflow.mark_stale(outcome.message)
            self.services.events("insert_succeeded" if outcome.ok else "insert_failed")
            self._changed(outcome.message)

        def failed(exc: BaseException) -> None:
            self.workflow.inserted(False, friendly_error(exc))
            self._changed(self.workflow.error)

        self.submit(lambda: inserter.insert(text, participant, confirmed), done, failed)

    # --- debug data ---------------------------------------------------------------------------

    def delete_debug_data(self) -> int:
        directory = self.services.debug_dir
        count = len(list(directory.glob("*.png"))) if directory.is_dir() else 0
        shutil.rmtree(directory, ignore_errors=True)
        self.message.emit(f"Deleted {count} debug capture(s).")
        return count
