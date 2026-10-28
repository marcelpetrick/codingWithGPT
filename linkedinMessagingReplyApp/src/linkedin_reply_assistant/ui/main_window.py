# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main window (§15): status strip, Capture | Message | Draft panes, action bar, status line."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from linkedin_reply_assistant.config.loader import CATEGORIES
from linkedin_reply_assistant.diagnostics.preflight import Check
from linkedin_reply_assistant.shortcuts.base import ShortcutStatus
from linkedin_reply_assistant.state.workflow import BUSY, State
from linkedin_reply_assistant.ui.about import AboutDialog
from linkedin_reply_assistant.ui.controller import Controller
from linkedin_reply_assistant.ui.dialogs import ShortcutsDialog, StatusDialog
from linkedin_reply_assistant.ui.roi_editor import PreviewWidget, RoiDialog

STYLE = """
QLabel#chip { border-radius: 9px; padding: 2px 8px; }
QLabel#chip[level="ok"] { background: #dff3e4; color: #135c2a; }
QLabel#chip[level="warn"] { background: #fff0c2; color: #6b4e00; }
QLabel#chip[level="fail"] { background: #fbdcdc; color: #8a1c1c; }
QLabel#chip[level="info"] { background: #e3edf9; color: #0a4a8c; }
QLabel#heading { font-weight: bold; font-size: 15px; }
QPushButton#primary { font-weight: bold; padding: 6px 14px; }
"""
AUTO = "(automatic)"


def chip(text: str = "", level: str = "info") -> QLabel:
    label = QLabel(text)
    label.setObjectName("chip")
    label.setProperty("level", level)
    return label


def set_chip(label: QLabel, text: str, level: str) -> None:
    label.setText(text)
    if label.property("level") != level:
        label.setProperty("level", level)
        label.style().unpolish(label)
        label.style().polish(label)


class MainWindow(QMainWindow):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller = controller
        self.checks: list[Check] = []
        self.setWindowTitle("LinkedIn Reply Assistant")
        self.setStyleSheet(STYLE)
        self.resize(1280, 760)
        self._build_menu()
        central = QWidget()
        root = QVBoxLayout(central)
        root.addLayout(self._build_strip())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_capture())
        splitter.addWidget(self._build_message())
        splitter.addWidget(self._build_draft())
        splitter.setSizes([400, 420, 460])
        root.addWidget(splitter, 1)
        root.addLayout(self._build_actions())
        self.setCentralWidget(central)
        self._build_shortcuts()

        controller.changed.connect(self.refresh)
        controller.message.connect(self.status.setText)
        controller.health.connect(self._on_health)
        controller.shortcut.connect(self._on_shortcut)
        controller.confirm_insert.connect(self._confirm_insert)
        controller.draft_finished.connect(self._on_draft_finished)
        self._bridge_timer = QTimer(self)
        self._bridge_timer.timeout.connect(self.refresh_bridge)
        self._bridge_timer.start(1000)
        self.apply_always_on_top(controller.settings.always_on_top)
        self.refresh()

    # --- layout -------------------------------------------------------------------------------

    def _build_menu(self) -> None:
        tools = self.menuBar().addMenu("&Tools")
        status = QAction("System Status…", self)
        status.triggered.connect(self.show_status)
        tools.addAction(status)
        shortcuts = QAction("Keyboard Shortcuts…", self)
        shortcuts.triggered.connect(self.show_shortcuts)
        tools.addAction(shortcuts)
        self.on_top = QAction("Always on top", self, checkable=True)
        self.on_top.toggled.connect(self._toggle_on_top)
        tools.addAction(self.on_top)
        tools.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        tools.addAction(quit_action)
        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("About LinkedIn Reply Assistant…", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)

    def _build_strip(self) -> QHBoxLayout:
        strip = QHBoxLayout()
        title = QLabel("LinkedIn Reply Assistant")
        title.setObjectName("heading")
        strip.addWidget(title)
        strip.addSpacing(12)
        self.capture_chip = chip()
        self.hotkey_chip = chip()
        self.ai_chip = chip()
        self.extension_chip = chip()
        self.health_chip = chip()
        for widget in (self.capture_chip, self.hotkey_chip, self.ai_chip, self.extension_chip):
            strip.addWidget(widget)
        strip.addStretch(1)
        strip.addWidget(self.health_chip)
        return strip

    def _pane(self, title: str) -> tuple[QGroupBox, QVBoxLayout]:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        return box, layout

    def _build_capture(self) -> QGroupBox:
        box, layout = self._pane("CAPTURE")
        self.preview = PreviewWidget()
        layout.addWidget(self.preview, 1)
        self.capture_meta = QLabel()
        self.capture_meta.setWordWrap(True)
        layout.addWidget(self.capture_meta)
        row = QHBoxLayout()
        self.select_button = QPushButton("Select Window")
        self.select_button.clicked.connect(lambda: self.controller.select_source())
        self.region_button = QPushButton("Edit Region")
        self.region_button.clicked.connect(self.edit_region)
        self.reset_region_button = QPushButton("Reset Region")
        self.reset_region_button.clicked.connect(lambda: self.controller.set_roi(None))
        for button in (self.select_button, self.region_button, self.reset_region_button):
            row.addWidget(button)
        layout.addLayout(row)
        return box

    def _build_message(self) -> QGroupBox:
        box, layout = self._pane("MESSAGE")
        grid = QGridLayout()
        grid.addWidget(QLabel("Sender:"), 0, 0)
        self.sender_label = QLabel("–")
        grid.addWidget(self.sender_label, 0, 1)
        grid.addWidget(QLabel("Language:"), 1, 0)
        self.language = QLabel("–")
        grid.addWidget(self.language, 1, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addWidget(QLabel("Extracted text (editable):"))
        self.extracted = QPlainTextEdit()
        self.extracted.setPlaceholderText("The recognized conversation text appears here.")
        self.extracted.textChanged.connect(
            lambda: self.controller.edit_extracted_text(self.extracted.toPlainText())
        )
        layout.addWidget(self.extracted, 1)
        row = QHBoxLayout()
        self.extraction_chip = chip()
        row.addWidget(self.extraction_chip)
        row.addStretch(1)
        layout.addLayout(row)
        self.extraction_warnings = QLabel()
        self.extraction_warnings.setWordWrap(True)
        layout.addWidget(self.extraction_warnings)
        return box

    def _build_draft(self) -> QGroupBox:
        box, layout = self._pane("DRAFT")
        self.draft = QPlainTextEdit()
        self.draft.setPlaceholderText("The generated reply appears here. Edit it freely.")
        self.draft.textChanged.connect(lambda: self.controller.edit_draft(self.draft.toPlainText()))
        layout.addWidget(self.draft, 1)
        grid = QGridLayout()
        grid.addWidget(QLabel("Category:"), 0, 0)
        self.category = QComboBox()
        self.category.addItems([AUTO, *CATEGORIES])
        grid.addWidget(self.category, 0, 1)
        self.regenerate_button = QPushButton("Regenerate")
        self.regenerate_button.clicked.connect(self.regenerate)
        grid.addWidget(self.regenerate_button, 0, 2)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        self.classification = QLabel()
        self.classification.setWordWrap(True)
        layout.addWidget(self.classification)
        self.backend_info = QLabel()
        self.backend_info.setWordWrap(True)
        self.backend_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.backend_info)
        row = QHBoxLayout()
        self.draft_chip = chip()
        row.addWidget(self.draft_chip)
        row.addStretch(1)
        layout.addLayout(row)
        return box

    def _build_actions(self) -> QVBoxLayout:
        column = QVBoxLayout()
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        column.addWidget(line)
        row = QHBoxLayout()
        self.capture_button = QPushButton("Capture && Draft")
        self.capture_button.setObjectName("primary")
        self.capture_button.clicked.connect(self.controller.capture_and_draft)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.controller.cancel)
        row.addWidget(self.capture_button)
        row.addWidget(self.cancel_button)
        row.addStretch(1)
        self.copy_button = QPushButton("Copy Draft")
        self.copy_button.clicked.connect(self.copy_draft)
        self.insert_button = QPushButton("Insert into LinkedIn")
        self.insert_button.setObjectName("primary")
        self.insert_button.clicked.connect(lambda: self.controller.insert())
        row.addWidget(self.copy_button)
        row.addWidget(self.insert_button)
        column.addLayout(row)
        self.status = QLabel("Ready.")
        self.status.setWordWrap(True)
        column.addWidget(self.status)
        return column

    def _build_shortcuts(self) -> None:
        bindings = {
            "Ctrl+R": self.regenerate,
            "Esc": self.controller.cancel,
            "Ctrl+E": self.draft.setFocus,
            "Ctrl+D": self.copy_draft,
            "Ctrl+Q": self.close,
        }
        for keys, slot in bindings.items():
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(slot)

    # --- actions ------------------------------------------------------------------------------

    def regenerate(self) -> None:
        category = self.category.currentText()
        self.controller.regenerate(None if category == AUTO else category)

    def copy_draft(self) -> None:
        text = self.draft.toPlainText()
        if text.strip():
            QGuiApplication.clipboard().setText(text)
            self.status.setText("Draft copied. Paste it in LinkedIn and press Send yourself.")

    def edit_region(self) -> None:
        capture = self.controller.workflow.capture
        if capture is None:
            self.status.setText("Capture once first, then edit the region on that image.")
            return
        dialog = RoiDialog(capture.image, self.controller.settings.roi, self)
        if dialog.exec():
            self.controller.set_roi(dialog.roi)

    def show_status(self) -> StatusDialog:
        dialog = StatusDialog(self.controller, self.checks, self)
        dialog.show()
        return dialog

    def show_about(self) -> AboutDialog:
        dialog = AboutDialog(self)
        dialog.show()
        return dialog

    def show_shortcuts(self) -> ShortcutsDialog:
        dialog = ShortcutsDialog(self.controller, self)
        dialog.show()
        return dialog

    def _toggle_on_top(self, enabled: bool) -> None:
        self.controller.settings.always_on_top = enabled
        self.controller.save()
        self.apply_always_on_top(enabled)

    def apply_always_on_top(self, enabled: bool) -> None:
        self.on_top.blockSignals(True)
        self.on_top.setChecked(enabled)
        self.on_top.blockSignals(False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        if self.isVisible():
            self.show()

    def _confirm_insert(self, question: str) -> None:
        answer = QMessageBox.question(self, "Confirm conversation", question)
        if answer == QMessageBox.StandardButton.Yes:
            self.controller.insert(confirmed=True)

    def _on_draft_finished(self) -> None:
        if not self.isActiveWindow():
            QApplication.alert(self)  # a soft hint, no focus stealing (§15.4)

    # --- state to widgets ---------------------------------------------------------------------

    def _on_health(self, checks: list[Check]) -> None:
        self.checks = checks
        worst = "ok"
        for check in checks:
            if check.status == "fail":
                worst = "fail"
            elif check.status == "warn" and worst == "ok":
                worst = "warn"
        set_chip(
            self.health_chip,
            {"ok": "● OK", "warn": "● Check status", "fail": "● Problem"}[worst],
            worst,
        )
        self.health_chip.setToolTip("\n".join(f"{c.name}: {c.detail}" for c in checks))
        self.refresh()

    def _on_shortcut(self, status: ShortcutStatus) -> None:
        self.refresh()

    def refresh_bridge(self) -> None:
        connected = self.controller.bridge_connected
        set_chip(
            self.extension_chip,
            "Extension: connected" if connected else "Extension: not connected",
            "ok" if connected else "warn",
        )
        self._refresh_buttons()

    def _set_text(self, editor: QPlainTextEdit, text: str) -> None:
        if editor.toPlainText() != text:
            editor.blockSignals(True)
            editor.setPlainText(text)
            editor.blockSignals(False)

    def refresh(self) -> None:
        controller = self.controller
        flow = controller.workflow
        source = controller.source
        set_chip(
            self.capture_chip,
            f"Capture: {flow.state.value}" + (f" · {source.name}" if source else ""),
            "warn" if flow.state == State.NO_SOURCE else "ok",
        )
        shortcut = controller.shortcut_status
        trigger = shortcut.binding.trigger if shortcut.binding else ""
        set_chip(
            self.hotkey_chip,
            f"Hotkey: {trigger}" if trigger else "Hotkey: off",
            "ok" if trigger else "info",
        )
        self.hotkey_chip.setToolTip(shortcut.message)

        capture = flow.capture
        self.preview.roi = controller.settings.roi
        self.preview.set_image(capture.image if capture else None)
        if capture is not None:
            meta = capture.metadata()
            crop = "region set" if meta["crop"] else "full window"
            self.capture_meta.setText(
                f"#{meta['sequence_id']} · {meta['size']} · {crop} · {meta['source']}"
            )
        else:
            self.capture_meta.setText(
                "Region: set" if controller.settings.roi else "Region: full window"
            )

        extraction = flow.extraction
        self.sender_label.setText(extraction.participant or "–" if extraction else "–")
        self.language.setText(extraction.language if extraction else "–")
        self._set_text(self.extracted, flow.extracted_text)
        if extraction is None:
            set_chip(self.extraction_chip, "Extraction: –", "info")
            self.extraction_warnings.setText("")
        elif extraction.needs_review:
            set_chip(
                self.extraction_chip, f"Extraction needs review ({extraction.extractor})", "warn"
            )
            self.extraction_warnings.setText("\n".join(f"• {w}" for w in extraction.warnings))
        else:
            set_chip(
                self.extraction_chip,
                f"Extraction: {extraction.extractor} · {extraction.confidence:.0%}",
                "ok",
            )
            self.extraction_warnings.setText(extraction.detail)

        draft = flow.draft
        self._set_text(self.draft, flow.draft_text)
        if draft is None:
            self.classification.setText("Category: –")
            self.backend_info.setText("")
            set_chip(self.ai_chip, "AI: –", "info")
        else:
            c = draft.classification
            self.classification.setText(
                f"Category: {c.category} ({c.confidence:.0%}, {c.source}) · {c.reason_short}"
            )
            r = draft.result
            fallback = "; ".join(r.fallback_reasons) if r.fallback_used else "none"
            timing = controller.timings
            total = f" · total {timing.total_ms / 1000:.1f} s" if timing else ""
            self.backend_info.setText(
                f"AI: {r.backend} / {r.model} ({r.endpoint})\n"
                f"Generation: {r.duration_s:.1f} s{total}\nFallback: {fallback}"
            )
            set_chip(
                self.ai_chip, f"AI: {r.backend} / {r.model}", "warn" if r.fallback_used else "ok"
            )
        if flow.stale_reason:
            set_chip(self.draft_chip, "Draft stale: " + flow.stale_reason, "warn")
        elif draft is not None and draft.needs_manual_review:
            text = "Review carefully" + (": " + "; ".join(draft.warnings) if draft.warnings else "")
            set_chip(self.draft_chip, text, "warn")
        elif flow.state == State.INSERTED:
            set_chip(self.draft_chip, "Inserted — not sent. Press Send in LinkedIn.", "ok")
        elif flow.state == State.ERROR:
            set_chip(self.draft_chip, flow.error, "fail")
        elif flow.state in BUSY:
            set_chip(self.draft_chip, f"{flow.state.value}…", "info")
        else:
            set_chip(self.draft_chip, flow.state.value, "info")
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        flow = self.controller.workflow
        busy = flow.busy
        self.capture_button.setEnabled(flow.state not in (State.NO_SOURCE, State.INSERTING))
        self.cancel_button.setEnabled(busy and flow.state != State.INSERTING)
        self.regenerate_button.setEnabled(
            bool(flow.extracted_text.strip()) and flow.state != State.INSERTING
        )
        self.region_button.setEnabled(flow.capture is not None)
        self.copy_button.setEnabled(bool(flow.draft_text.strip()))
        self.insert_button.setEnabled(flow.can_insert and self.controller.bridge_connected)
        self.insert_button.setToolTip(
            "" if self.controller.bridge_connected else "Browser extension not connected."
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self._bridge_timer.stop()
        self.controller.shutdown()
        event.accept()
