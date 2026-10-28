# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keyboard Shortcuts page (§17.2) and System Status page (§5, §20.2)."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linkedin_reply_assistant.diagnostics.preflight import Check
from linkedin_reply_assistant.shortcuts.guardrails import LOCAL_SHORTCUTS, check_trigger
from linkedin_reply_assistant.ui.controller import Controller

LOCAL_ACTIONS = {
    "CTRL+R": "Regenerate",
    "ESC": "Cancel",
    "CTRL+E": "Focus the draft editor",
    "CTRL+D": "Copy Draft",
    "CTRL+Q": "Quit",
}


class ShortcutsDialog(QDialog):
    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        hotkey = controller.services.config.app.hotkey
        self.requested = QLineEdit(hotkey.preferred_trigger)
        self.requested.textChanged.connect(self._validate)
        form.addRow("Requested global shortcut", self.requested)
        self.accepted_label = QLabel()
        form.addRow("Accepted by the desktop", self.accepted_label)
        self.status = QLabel()
        self.status.setWordWrap(True)
        form.addRow("Status", self.status)
        self.hint = QLabel()
        form.addRow("", self.hint)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.request = QPushButton("Request from desktop")
        self.request.clicked.connect(self._request)
        row.addWidget(self.request)
        self.desktop = QPushButton("Open desktop shortcut settings")
        self.desktop.clicked.connect(self._open_desktop)
        row.addWidget(self.desktop)
        layout.addLayout(row)
        local = QLabel(
            "In-application shortcuts: "
            + ", ".join(f"{key} = {LOCAL_ACTIONS[key]}" for key in LOCAL_SHORTCUTS)
            + ". Insert into LinkedIn has no shortcut on purpose."
        )
        local.setWordWrap(True)
        layout.addWidget(local)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        controller.shortcut.connect(self._show)
        self._show(controller.shortcut_status)
        self._validate()

    def _show(self, status: object) -> None:
        current = self.controller.shortcut_status
        trigger = current.binding.trigger if current.binding else ""
        self.accepted_label.setText(trigger or "none")
        self.status.setText(current.message)
        self.request.setEnabled(current.available and not self.hint.text())

    def _validate(self) -> None:
        reason = check_trigger(self.requested.text())
        self.hint.setText(reason or "")
        self.request.setEnabled(self.controller.shortcut_status.available and reason is None)

    def _request(self) -> None:
        self.controller.configure_hotkey(self.requested.text())

    def _open_desktop(self) -> None:
        if not self.controller.open_desktop_shortcut_settings():
            self.status.setText("This desktop cannot open its shortcut settings from here.")


class StatusDialog(QDialog):
    def __init__(self, controller: Controller, checks: list[Check], parent: QWidget | None = None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("System Status")
        self.resize(820, 420)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Check", "State", "Detail"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        self.show_checks(checks)
        controller.health.connect(self.show_checks)
        debug = controller.services.config.app.save_debug_captures
        warning = QLabel(
            "Debug capture saving is ON: screenshots are written to "
            f"{controller.services.debug_dir}."
            if debug
            else "Debug capture saving is off. No screenshot is written to disk."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(controller.refresh_health)
        row.addWidget(refresh)
        self.delete = QPushButton("Delete debug data")
        self.delete.clicked.connect(controller.delete_debug_data)
        row.addWidget(self.delete)
        row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row.addWidget(close)
        layout.addLayout(row)

    def show_checks(self, checks: list[Check]) -> None:
        self.table.setRowCount(len(checks))
        for row, check in enumerate(checks):
            for column, text in enumerate((check.name, check.status.upper(), check.detail)):
                self.table.setItem(row, column, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()
