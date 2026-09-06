"""Interactive terminal controls for the Agent While True dashboard."""

from __future__ import annotations

import os
import select
import sys
import termios
import tty
from dataclasses import dataclass

INTERVALS = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 60.0)
THEMES = ("dark", "vivid", "plain")
HISTORY_LENGTHS = (5, 10, 20, 50)


def nearest_interval_index(value: float) -> int:
    return min(range(len(INTERVALS)), key=lambda index: abs(INTERVALS[index] - value))


@dataclass(slots=True)
class DashboardState:
    """Mutable presentation state; it never grants terminal-input policy."""

    interval_index: int
    paused: bool = False
    help_visible: bool = False
    theme_index: int = 0
    rescan_requested: bool = False
    show_events: bool = True
    history_index: int = 0

    @classmethod
    def from_interval(cls, value: float) -> DashboardState:
        return cls(interval_index=nearest_interval_index(value))

    @property
    def interval(self) -> float:
        return INTERVALS[self.interval_index]

    @property
    def theme(self) -> str:
        return THEMES[self.theme_index]

    @property
    def history_length(self) -> int:
        return HISTORY_LENGTHS[self.history_index]

    def handle(self, key: str) -> bool:
        """Apply one key. Return True only when the user requested quit."""
        lowered = key.lower()
        if lowered == "q":
            return True
        if lowered in {"h", "?"}:
            self.help_visible = not self.help_visible
        elif lowered == "p":
            self.paused = not self.paused
        elif lowered == "r":
            self.rescan_requested = True
        elif key in {"+", "="}:
            self.interval_index = min(self.interval_index + 1, len(INTERVALS) - 1)
        elif key in {"-", "_"}:
            self.interval_index = max(self.interval_index - 1, 0)
        elif lowered == "t":
            self.theme_index = (self.theme_index + 1) % len(THEMES)
        elif lowered == "e":
            self.show_events = not self.show_events
        elif lowered == "l":
            self.history_index = (self.history_index + 1) % len(HISTORY_LENGTHS)
        return False


class TerminalKeys:
    """Read one key with a timeout, restoring terminal mode after every wait."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def read(self, timeout: float) -> str:
        if not self.enabled:
            return ""
        descriptor = sys.stdin.fileno()
        previous = termios.tcgetattr(descriptor)
        try:
            tty.setcbreak(descriptor)
            ready, _, _ = select.select([descriptor], [], [], timeout)
            if not ready:
                return ""
            return os.read(descriptor, 8).decode(errors="ignore")[:1]
        finally:
            termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)
