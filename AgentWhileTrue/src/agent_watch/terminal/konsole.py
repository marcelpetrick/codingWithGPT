"""KDE Konsole adapter, driven through Konsole's per-session D-Bus interface.

Using Konsole's own interface rather than desktop-wide input simulation is what
makes this work under Wayland: no ``xdotool``, no ``ydotool``, no screen
coordinates, no OCR. The methods used here were verified against Konsole on
Manjaro/KDE Plasma with ``XDG_SESSION_TYPE=wayland``:

``org.kde.konsole.Session``
    ``processId``, ``foregroundProcessId``, ``getDisplayedTextList``,
    ``getAllDisplayedTextList``, ``sendText``, ``title``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from agent_watch.terminal.base import (
    DEFAULT_VISIBLE_LINES,
    SessionRef,
    TerminalAdapter,
    TerminalSession,
    TerminalUnavailableError,
)

ADAPTER_NAME = "konsole"

_SERVICE_RE = re.compile(r"^org\.kde\.konsole(?:-\d+)?$")
_SESSION_PATH_RE = re.compile(r"^/Sessions/\d+$")

#: Preferred first; ``qdbus6`` is the Qt6 name shipped by current KDE, ``qdbus``
#: the traditional one. Either is acceptable.
_QDBUS_CANDIDATES = ("qdbus6", "qdbus", "qdbus-qt6", "qdbus-qt5")

#: A D-Bus round trip to a healthy Konsole is sub-millisecond; anything near
#: this bound means the session is wedged and should be skipped, not waited on.
_CALL_TIMEOUT_SECONDS = 5.0

#: Konsole's Session.title() takes a role; 1 is the display/tab title.
_TITLE_ROLE_DISPLAY = 1

#: Default for :attr:`KonsoleAdapter.qdbus`. A distinct sentinel is needed so
#: that passing ``qdbus=None`` explicitly means "there is no qdbus here" - which
#: tests and ``doctor`` rely on - rather than "go and look for one".
AUTODETECT = "<autodetect>"


def find_qdbus() -> str | None:
    """Return the qdbus executable to use, or ``None`` if none is installed."""
    for candidate in _QDBUS_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
    return None


@dataclass(slots=True)
class KonsoleAdapter(TerminalAdapter):
    """Talk to every running Konsole instance on the current user's bus."""

    qdbus: str | None = AUTODETECT
    name: str = ADAPTER_NAME

    def __post_init__(self) -> None:
        if self.qdbus == AUTODETECT:
            self.qdbus = find_qdbus()

    # -- plumbing ---------------------------------------------------------

    def _call(self, *args: str) -> str | None:
        """Run one qdbus call. Returns ``None`` when the call failed.

        Failure is routine - a tab can close between enumeration and use - so it
        is reported as ``None`` rather than raised, and the caller drops that
        session from the current scan.
        """
        if self.qdbus is None:
            raise TerminalUnavailableError("no qdbus executable found")
        try:
            # Fixed executable, fixed argument vector, no shell: nothing is
            # interpolated into a command line.
            completed = subprocess.run(
                [self.qdbus, *args],
                capture_output=True,
                text=True,
                timeout=_CALL_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout

    # -- adapter interface -------------------------------------------------

    def is_available(self) -> bool:
        if self.qdbus is None:
            return False
        return self._call() is not None

    def services(self) -> list[str]:
        """Return every Konsole D-Bus service name currently on the bus."""
        raw = self._call()
        if raw is None:
            raise TerminalUnavailableError("cannot list D-Bus services")
        return [
            stripped for line in raw.splitlines() if _SERVICE_RE.match(stripped := line.strip())
        ]

    def _session_paths(self, service: str) -> list[str]:
        raw = self._call(service)
        if raw is None:
            return []
        return [
            stripped
            for line in raw.splitlines()
            if _SESSION_PATH_RE.match(stripped := line.strip())
        ]

    def _int_call(self, ref: SessionRef, method: str) -> int:
        raw = self._call(ref.service, ref.session_id, f"org.kde.konsole.Session.{method}")
        if raw is None:
            return 0
        try:
            return int(raw.strip())
        except ValueError:
            return 0

    def list_sessions(self) -> list[TerminalSession]:
        sessions: list[TerminalSession] = []
        for service in self.services():
            for path in self._session_paths(service):
                ref = SessionRef(adapter=self.name, service=service, session_id=path)
                shell_pid = self._int_call(ref, "processId")
                if shell_pid == 0:
                    # The tab closed between enumeration and inspection.
                    continue
                foreground_pid = self._int_call(ref, "foregroundProcessId") or shell_pid
                title = self._call(
                    service, path, "org.kde.konsole.Session.title", str(_TITLE_ROLE_DISPLAY)
                )
                sessions.append(
                    TerminalSession(
                        ref=ref,
                        shell_pid=shell_pid,
                        foreground_pid=foreground_pid,
                        title=(title or "").strip(),
                    )
                )
        return sessions

    def foreground_pid(self, ref: SessionRef) -> int:
        return self._int_call(ref, "foregroundProcessId")

    def read_visible_text(self, ref: SessionRef, lines: int = DEFAULT_VISIBLE_LINES) -> list[str]:
        raw = self._call(
            ref.service,
            ref.session_id,
            "org.kde.konsole.Session.getAllDisplayedTextList",
            "true",
        )
        if raw is None:
            return []
        # Only the tail is kept. Older lines are exactly the "historical prompt
        # text" hazard the vision warns about (DANGER 3), and keeping them would
        # also mean holding more terminal content in memory than necessary.
        return raw.splitlines()[-lines:]

    def send_text(self, ref: SessionRef, text: str) -> None:
        result = self._call(ref.service, ref.session_id, "org.kde.konsole.Session.sendText", text)
        if result is None:
            raise TerminalUnavailableError(f"sendText failed for {ref.key()}")
