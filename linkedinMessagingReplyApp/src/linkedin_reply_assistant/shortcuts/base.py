# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shortcut service interface and the disabled fallback (§7.4, §21.2)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

UNAVAILABLE = (
    "Global hotkey is unavailable on this desktop. "
    "Capture & Draft remains available from the application."
)


@dataclass(frozen=True)
class Binding:
    shortcut_id: str
    description: str
    trigger: str  # what the desktop reports, for example "Ctrl+Alt+L"; "" if not assigned


@dataclass(frozen=True)
class ShortcutStatus:
    available: bool
    binding: Binding | None
    message: str

    @property
    def active(self) -> bool:
        return self.binding is not None and bool(self.binding.trigger)


class ShortcutService(Protocol):
    def start(self, on_activated: Callable[[str], None]) -> ShortcutStatus: ...

    def bind(self, shortcut_id: str, description: str, preferred: str) -> ShortcutStatus: ...

    def configure(self) -> bool: ...

    def close(self) -> None: ...


class DisabledShortcuts:
    """Used when the GlobalShortcuts portal is missing. Never falls back to input hooks."""

    def __init__(self, reason: str = UNAVAILABLE) -> None:
        self.reason = reason

    def start(self, on_activated: Callable[[str], None]) -> ShortcutStatus:
        return ShortcutStatus(False, None, self.reason)

    def bind(self, shortcut_id: str, description: str, preferred: str) -> ShortcutStatus:
        return ShortcutStatus(False, None, self.reason)

    def configure(self) -> bool:
        return False

    def close(self) -> None:
        """Nothing to release."""
