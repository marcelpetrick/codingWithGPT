# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Controller and main window with the demo backend, an image source and scripted fakes."""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from linkedin_reply_assistant.app import make_manager
from linkedin_reply_assistant.backends.base import BackendError, Health
from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.browser_bridge.inserter import Inserter
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.capture.source import CaptureError, CaptureSource, ImageFileSource
from linkedin_reply_assistant.config.loader import Config, load_config
from linkedin_reply_assistant.diagnostics.preflight import Check
from linkedin_reply_assistant.events import EventLog
from linkedin_reply_assistant.extraction.ocr import TesseractExtractor
from linkedin_reply_assistant.pipeline import Pipeline
from linkedin_reply_assistant.portal.bus import PortalError
from linkedin_reply_assistant.reply_engine.generator import ReplyGenerator
from linkedin_reply_assistant.shortcuts.base import Binding, ShortcutStatus
from linkedin_reply_assistant.state.settings import Settings, load_settings
from linkedin_reply_assistant.state.workflow import State
from linkedin_reply_assistant.ui.controller import (
    ALL_BACKENDS_DOWN,
    EXTENSION_DOWN,
    Controller,
    Services,
    SourceSelector,
    friendly_error,
)
from linkedin_reply_assistant.ui.main_window import AUTO, MainWindow
from linkedin_reply_assistant.ui.roi_editor import RoiDialog, to_pixmap
from tests.conftest import FIXTURES
from tests.fakes import FakeBackend, make_config

SHOT = FIXTURES / "screenshots" / "dark_normal.png"
ROI = Roi(0.27, 0.0, 0.73, 0.84)
IDENT = {"ok": True, "title": "Kevin Doyle", "url": "https://www.linkedin.com/messaging/thread/9/"}


class FakeShortcuts:
    def __init__(self) -> None:
        self.on_activated: Callable[[str], None] | None = None
        self.bound: list[str] = []
        self.closed = False
        self.configure_result = True

    def start(self, on_activated: Callable[[str], None]) -> ShortcutStatus:
        self.on_activated = on_activated
        return ShortcutStatus(True, None, "Global hotkey not configured")

    def bind(self, shortcut_id: str, description: str, preferred: str) -> ShortcutStatus:
        self.bound.append(preferred)
        return ShortcutStatus(
            True, Binding(shortcut_id, description, "Ctrl+Alt+L"), "Global hotkey: Ctrl+Alt+L"
        )

    def configure(self) -> bool:
        return self.configure_result

    def close(self) -> None:
        self.closed = True


class Transport:
    def __init__(self) -> None:
        self.answers: list[dict[str, object]] = []
        self.sent: list[dict[str, object]] = []

    def request(self, message: dict[str, object], timeout: float = 5.0) -> dict[str, object]:
        self.sent.append(message)
        return self.answers.pop(0)


@dataclass
class Rig:
    controller: Controller
    shortcuts: FakeShortcuts
    transport: Transport
    bridge: dict[str, bool]
    selected: list[str | None]
    tmp: Path


def build(
    tmp: Path,
    config: Config,
    manager: BackendManager | None = None,
    selector: SourceSelector | None = None,
    settings: Settings | None = None,
) -> Rig:
    manager = manager or make_manager(config, demo=True)
    shortcuts, transport, bridge = FakeShortcuts(), Transport(), {"up": True}
    selected: list[str | None] = []

    def select(restore_token: str | None) -> tuple[CaptureSource, str | None]:
        selected.append(restore_token)
        return ImageFileSource(SHOT), f"token-{len(selected)}"

    pipeline = Pipeline(
        config, TesseractExtractor(), ReplyGenerator(config, manager), EventLog(), tmp / "debug"
    )
    services = Services(
        config=config,
        manager=manager,
        pipeline=pipeline,
        select_source=selector or select,
        shortcuts=shortcuts,
        inserter=Inserter(transport),
        bridge_connected=lambda: bridge["up"],
        preflight=lambda: [Check("session", "ok", "wayland"), Check("ai", "warn", "slow")],
        settings_path=tmp / "state.yaml",
        debug_dir=tmp / "debug",
        events=EventLog(),
    )
    controller = Controller(services, settings or Settings(roi=ROI))
    return Rig(controller, shortcuts, transport, bridge, selected, tmp)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    loaded = load_config(tmp_path / "cfg")
    return replace(
        loaded, app=replace(loaded.app, extraction=replace(loaded.app.extraction, mode="ocr"))
    )


@pytest.fixture
def rig(qtbot: QtBot, tmp_path: Path, config: Config) -> Iterator[Rig]:
    made = build(tmp_path, config)
    yield made
    made.controller.shutdown()


def ready(qtbot: QtBot, rig: Rig) -> Controller:
    controller = rig.controller
    controller.select_source()
    qtbot.waitUntil(lambda: controller.source is not None, timeout=5000)
    return controller


def drafted(qtbot: QtBot, rig: Rig) -> Controller:
    controller = ready(qtbot, rig)
    controller.capture_and_draft()
    qtbot.waitUntil(lambda: controller.workflow.state == State.DRAFT_READY, timeout=10000)
    return controller


# --- controller ---------------------------------------------------------------------------------


def test_capture_and_draft_flow(qtbot: QtBot, rig: Rig) -> None:
    controller = drafted(qtbot, rig)
    flow = controller.workflow
    assert flow.extraction is not None and flow.extraction.participant == "Kevin Doyle"
    assert flow.draft is not None and flow.draft.classification.category == "sales_outreach"
    assert controller.timings is not None and controller.timings.total_ms > 0
    assert load_settings(rig.tmp / "state.yaml").restore_token == "token-1"


def test_start_restores_source_and_reports(qtbot: QtBot, tmp_path: Path, config: Config) -> None:
    made = build(tmp_path, config, settings=Settings(restore_token="old"))
    health: list[list[Check]] = []
    made.controller.health.connect(health.append)
    made.controller.start()
    qtbot.waitUntil(lambda: made.controller.source is not None and bool(health), timeout=5000)
    assert made.selected == ["old"]
    assert made.controller.settings.restore_token == "token-1"  # single-use token replaced
    qtbot.waitUntil(lambda: made.shortcuts.on_activated is not None)
    made.controller.shutdown()
    assert made.shortcuts.closed


def test_failed_restore_clears_token(qtbot: QtBot, tmp_path: Path, config: Config) -> None:
    def broken(restore_token: str | None) -> tuple[CaptureSource, str | None]:
        raise PortalError("ScreenCast: cancelled by the user")

    made = build(tmp_path, config, selector=broken, settings=Settings(restore_token="old"))
    made.controller.select_source(restore=True)
    qtbot.waitUntil(lambda: made.controller.workflow.error != "", timeout=5000)
    assert made.controller.settings.restore_token is None
    assert made.controller.workflow.state == State.NO_SOURCE
    made.controller.shutdown()


def test_hotkey_runs_same_command(qtbot: QtBot, rig: Rig) -> None:
    controller = ready(qtbot, rig)
    controller.start()
    qtbot.waitUntil(lambda: rig.shortcuts.on_activated is not None)
    assert rig.shortcuts.on_activated is not None
    rig.shortcuts.on_activated("other-shortcut")
    rig.shortcuts.on_activated("capture-and-draft")
    qtbot.waitUntil(lambda: controller.workflow.state == State.DRAFT_READY, timeout=10000)
    assert controller.workflow.sequence == 1


def test_configure_hotkey_and_desktop_settings(qtbot: QtBot, rig: Rig) -> None:
    controller = rig.controller
    controller.configure_hotkey("CTRL+ALT+L")
    qtbot.waitUntil(lambda: controller.shortcut_status.active, timeout=5000)
    assert controller.settings.hotkey_trigger == "Ctrl+Alt+L"
    assert controller.open_desktop_shortcut_settings()


def test_capture_without_source_and_lost_source(qtbot: QtBot, rig: Rig, tmp_path: Path) -> None:
    controller = rig.controller
    messages: list[str] = []
    controller.message.connect(messages.append)
    controller.capture_and_draft()
    assert "Select the browser window" in messages[-1]
    ready(qtbot, rig)
    controller.source = ImageFileSource(tmp_path / "gone.png")
    controller.capture_and_draft()
    qtbot.waitUntil(lambda: controller.workflow.state == State.NO_SOURCE, timeout=5000)
    assert "Select the browser window again" in controller.workflow.error


def test_all_backends_down_keeps_capture(qtbot: QtBot, tmp_path: Path, config: Config) -> None:
    down = FakeBackend(make_config(), Health(False, error="timeout after 700 ms"))
    made = build(tmp_path, config, manager=BackendManager([down], 30))
    controller = ready(qtbot, made)
    controller.capture_and_draft()
    qtbot.waitUntil(lambda: controller.workflow.state == State.ERROR, timeout=10000)
    assert controller.workflow.error.startswith(ALL_BACKENDS_DOWN)
    assert "net: timeout after 700 ms" in controller.workflow.error  # §13.5: the reason is visible
    assert controller.workflow.capture is not None and controller.workflow.extracted_text
    made.controller.shutdown()


def test_unusable_extraction(qtbot: QtBot, rig: Rig, tmp_path: Path) -> None:
    blank = tmp_path / "blank.png"
    Image.new("RGB", (300, 200), "white").save(blank)
    controller = ready(qtbot, rig)
    controller.source = ImageFileSource(blank)
    messages: list[str] = []
    controller.message.connect(messages.append)
    controller.capture_and_draft()
    qtbot.waitUntil(lambda: controller.workflow.state == State.EXTRACTION_REVIEW, timeout=10000)
    qtbot.waitUntil(lambda: any("needs review" in m for m in messages))


def test_regenerate_with_override_and_errors(qtbot: QtBot, rig: Rig) -> None:
    controller = drafted(qtbot, rig)
    controller.edit_extracted_text(
        "Hello Marcel, we are hiring for a senior role, is this position interesting?"
    )
    assert controller.workflow.state == State.DRAFT_STALE
    controller.regenerate("recruiting")
    qtbot.waitUntil(lambda: controller.workflow.state == State.DRAFT_READY, timeout=5000)
    assert controller.workflow.draft is not None
    assert controller.workflow.draft.classification.source == "override"
    controller.edit_draft("My own words")
    assert controller.workflow.state == State.DRAFT_EDITED
    controller.edit_draft("My own words")
    empty = build(rig.tmp / "x", controller.services.config).controller
    messages: list[str] = []
    empty.message.connect(messages.append)
    empty.regenerate()
    assert "no extracted text" in messages[-1]
    empty.shutdown()


def test_regenerate_failure_and_cancel(qtbot: QtBot, tmp_path: Path, config: Config) -> None:
    calls = {"n": 0}

    def answer(request: Any) -> str:
        calls["n"] += 1
        if calls["n"] > 1:
            raise BackendError("model crashed")
        return json.dumps({"reply": "Hi Kevin, no thanks."})

    backend = FakeBackend(make_config(), Health(True, "1", ("big:1",)), answer)
    made = build(tmp_path, config, manager=BackendManager([backend], 30))
    controller = drafted(qtbot, made)
    controller.regenerate()
    qtbot.waitUntil(lambda: controller.workflow.state == State.ERROR, timeout=5000)
    assert "model crashed" in controller.workflow.error
    controller.capture_and_draft()
    controller.cancel()
    assert controller.workflow.state == State.SOURCE_READY
    controller.cancel()  # idle: nothing happens
    made.controller.shutdown()


def test_insert_paths(qtbot: QtBot, rig: Rig) -> None:
    controller = drafted(qtbot, rig)
    rig.transport.answers = [IDENT, {"ok": True, "readback": controller.workflow.draft_text}]
    controller.insert()
    qtbot.waitUntil(lambda: controller.workflow.state == State.INSERTED, timeout=5000)
    assert rig.transport.sent[1]["type"] == "insert"

    rig.transport.answers = [dict(IDENT, title="Tom Brandt")]
    controller.insert()
    qtbot.waitUntil(lambda: controller.workflow.state == State.DRAFT_STALE, timeout=5000)
    assert not controller.workflow.can_insert


def test_insert_confirmation_and_bridge_down(qtbot: QtBot, rig: Rig) -> None:
    controller = drafted(qtbot, rig)
    questions: list[str] = []
    controller.confirm_insert.connect(questions.append)
    rig.transport.answers = [dict(IDENT, title="")]
    controller.insert()
    qtbot.waitUntil(lambda: bool(questions), timeout=5000)
    rig.transport.answers = [
        dict(IDENT, title=""),
        {"ok": True, "readback": controller.workflow.draft_text},
    ]
    controller.insert(confirmed=True)
    qtbot.waitUntil(lambda: controller.workflow.state == State.INSERTED, timeout=5000)
    rig.bridge["up"] = False
    messages: list[str] = []
    controller.message.connect(messages.append)
    controller.insert()
    assert messages[-1] == EXTENSION_DOWN


def test_insert_errors(qtbot: QtBot, rig: Rig) -> None:
    controller = drafted(qtbot, rig)
    rig.transport.answers = []  # the transport raises IndexError: an unexpected failure
    controller.insert()
    qtbot.waitUntil(lambda: controller.workflow.state == State.ERROR, timeout=5000)
    assert "Unexpected error" in controller.workflow.error
    controller.edit_extracted_text("changed")
    messages: list[str] = []
    controller.message.connect(messages.append)
    controller.insert()
    assert "non-stale" in messages[-1]


def test_roi_and_debug_data(qtbot: QtBot, rig: Rig) -> None:
    controller = rig.controller
    controller.set_roi(None)
    assert load_settings(rig.tmp / "state.yaml").roi is None
    controller.set_roi(ROI)
    assert load_settings(rig.tmp / "state.yaml").roi == ROI
    (rig.tmp / "debug").mkdir()
    (rig.tmp / "debug" / "a.png").write_bytes(b"x")
    assert controller.delete_debug_data() == 1 and not (rig.tmp / "debug").exists()
    assert controller.delete_debug_data() == 0


def test_friendly_errors() -> None:
    assert friendly_error(BackendError("x", reachable=False)) == ALL_BACKENDS_DOWN
    assert friendly_error(BackendError("bad json")) == "AI backend error: bad json"
    assert friendly_error(CaptureError("gone")) == "gone"
    assert friendly_error(KeyError("k")).startswith("Unexpected error: KeyError")


# --- main window --------------------------------------------------------------------------------


@pytest.fixture
def window(qtbot: QtBot, rig: Rig) -> MainWindow:
    win = MainWindow(rig.controller)
    qtbot.addWidget(win)
    win.show()
    return win


def test_window_full_flow(qtbot: QtBot, rig: Rig, window: MainWindow) -> None:
    assert not window.capture_button.isEnabled()
    qtbot.mouseClick(window.select_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.capture_button.isEnabled(), timeout=5000)
    qtbot.mouseClick(window.capture_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "Hi, thank you" in window.draft.toPlainText(), timeout=10000)
    assert window.sender_label.text() == "Kevin Doyle"
    assert "sales_outreach" in window.classification.text()
    assert (
        "AI: demo / demo" in window.backend_info.text()
        and "Fallback: none" in window.backend_info.text()
    )
    assert window.insert_button.isEnabled() and window.copy_button.isEnabled()
    window.copy_draft()
    assert "Greetings from Munich" in QGuiApplication.clipboard().text()
    window.draft.setPlainText("Edited reply")
    assert rig.controller.workflow.state == State.DRAFT_EDITED
    window.extracted.setPlainText("Changed text from Kevin about a demo and pricing call")
    assert "Draft stale" in window.draft_chip.text() and not window.insert_button.isEnabled()
    window.category.setCurrentText("sales_outreach")
    window.regenerate()
    qtbot.waitUntil(lambda: rig.controller.workflow.state == State.DRAFT_READY, timeout=5000)
    window.category.setCurrentText(AUTO)
    rig.bridge["up"] = False
    window.refresh_bridge()
    assert not window.insert_button.isEnabled() and "not connected" in window.extension_chip.text()


def test_window_states_and_chips(qtbot: QtBot, rig: Rig, window: MainWindow) -> None:
    rig.controller.health.emit(
        [Check("a", "ok", "x"), Check("b", "fail", "y"), Check("c", "warn", "z")]
    )
    assert window.health_chip.text() == "● Problem"
    rig.controller.health.emit([Check("a", "warn", "x"), Check("b", "ok", "y")])
    assert window.health_chip.text() == "● Check status"
    rig.controller.shortcut_status = ShortcutStatus(True, Binding("a", "b", "Ctrl+Alt+L"), "ok")
    rig.controller.shortcut.emit(rig.controller.shortcut_status)
    assert window.hotkey_chip.text() == "Hotkey: Ctrl+Alt+L"
    window.copy_draft()  # nothing to copy: no change
    controller = drafted(qtbot, rig)
    flow = controller.workflow
    assert flow.extraction is not None and flow.draft is not None
    flow.extraction = replace(flow.extraction, warnings=("low confidence",))
    flow.draft = replace(
        flow.draft,
        needs_manual_review=True,
        warnings=("draft is long",),
        result=replace(flow.draft.result, fallback_reasons=("net: timeout",)),
    )
    window.refresh()
    assert (
        "needs review" in window.extraction_chip.text()
        and "low confidence" in window.extraction_warnings.text()
    )
    assert "Review carefully: draft is long" in window.draft_chip.text()
    assert "Fallback: net: timeout" in window.backend_info.text()
    flow.draft = replace(flow.draft, needs_manual_review=False, warnings=())
    flow.state = State.INSERTED
    window.refresh()
    assert "not sent" in window.draft_chip.text()
    flow.state, flow.error = State.ERROR, "boom"
    window.refresh()
    assert window.draft_chip.text() == "boom"
    flow.state = State.GENERATING
    window.refresh()
    assert window.draft_chip.text() == "Generating…" and window.cancel_button.isEnabled()


def test_window_dialogs(
    qtbot: QtBot, rig: Rig, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    status = window.show_status()
    rig.controller.health.emit([Check("x", "ok", "fine")])
    item = status.table.item(0, 2)
    assert status.table.rowCount() == 1 and item is not None and item.text() == "fine"
    status.close()
    shortcuts = window.show_shortcuts()
    rig.controller.shortcut_status = ShortcutStatus(True, None, "Global hotkey not configured")
    shortcuts.requested.setText("ALT+F4")
    assert "reserved" in shortcuts.hint.text() and not shortcuts.request.isEnabled()
    shortcuts.requested.setText("CTRL+ALT+L")
    assert shortcuts.request.isEnabled()
    shortcuts._request()
    qtbot.waitUntil(lambda: shortcuts.accepted_label.text() == "Ctrl+Alt+L", timeout=5000)
    rig.shortcuts.configure_result = False
    shortcuts._open_desktop()
    assert "cannot open" in shortcuts.status.text()
    shortcuts.close()
    window.edit_region()  # no capture yet
    assert "Capture once first" in window.status.text()
    drafted(qtbot, rig)
    monkeypatch.setattr(RoiDialog, "exec", lambda self: 1)
    window.edit_region()
    assert rig.controller.settings.roi == ROI
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.Yes)
    rig.transport.answers = [
        dict(IDENT, title=""),
        {"ok": True, "readback": rig.controller.workflow.draft_text},
    ]
    window._confirm_insert("Insert?")
    qtbot.waitUntil(lambda: rig.controller.workflow.state == State.INSERTED, timeout=5000)
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.No)
    window._confirm_insert("Insert?")


def test_window_on_top_alert_and_close(qtbot: QtBot, rig: Rig, window: MainWindow) -> None:
    window.on_top.setChecked(True)
    assert rig.controller.settings.always_on_top
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    window.on_top.setChecked(False)
    window._on_draft_finished()
    window.close()
    assert rig.shortcuts.closed


def test_roi_dialog_drag(qtbot: QtBot) -> None:
    image = Image.new("RGB", (400, 200), "white")
    dialog = RoiDialog(image, None)
    qtbot.addWidget(dialog)
    dialog.show()
    canvas = dialog.canvas
    rect = canvas.image_rect()
    start = QPoint(rect.left() + rect.width() // 4, rect.top() + rect.height() // 4)
    end = QPoint(rect.left() + 3 * rect.width() // 4, rect.top() + 3 * rect.height() // 4)
    qtbot.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(canvas, end)
    qtbot.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=end)
    roi = dialog.roi
    assert roi is not None and abs(roi.x - 0.25) < 0.03 and abs(roi.width - 0.5) < 0.03
    qtbot.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=start)  # too small: keep the last
    assert dialog.roi == roi
    qtbot.mouseMove(canvas, end)  # no press: moves are ignored
    assert to_pixmap(image).width() == 400
    canvas.set_image(None)
    canvas.repaint()
    assert canvas.image_rect().isNull()


def test_remembered_hotkey_is_bound_again_on_start(
    qtbot: QtBot, tmp_path: Path, config: Config
) -> None:
    made = build(tmp_path, config, settings=Settings(hotkey_trigger="Ctrl+Alt+L"))
    made.controller.start()
    qtbot.waitUntil(lambda: made.controller.shortcut_status.active, timeout=5000)
    assert made.shortcuts.bound == ["Ctrl+Alt+L"]
    made.controller.shutdown()


def test_first_start_binds_nothing(qtbot: QtBot, rig: Rig) -> None:
    rig.controller.start()
    qtbot.waitUntil(lambda: rig.shortcuts.on_activated is not None, timeout=5000)
    qtbot.wait(100)
    assert rig.shortcuts.bound == []
