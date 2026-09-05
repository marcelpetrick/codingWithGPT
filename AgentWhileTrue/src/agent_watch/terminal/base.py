"""The terminal adapter protocol.

Everything the supervisor needs from a terminal emulator is here: enumerate
sessions, find the foreground process of one, read a *bounded* amount of what is
currently displayed, and send text. Scrollback is deliberately not part of the
interface - the vision forbids retaining it, and an adapter that cannot offer it
is therefore not a limited adapter but a correct one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

#: How many of the most recent displayed lines a recognizer may look at. Enough
#: to hold a limit banner plus the prompt beneath it, small enough that stale
#: output scrolls out of consideration on its own.
DEFAULT_VISIBLE_LINES = 40


class TerminalError(RuntimeError):
    """A terminal operation failed."""


class TerminalUnavailableError(TerminalError):
    """The terminal application is not reachable at all.

    Distinct from a per-session failure: it means rediscovery should be
    attempted rather than the session being marked unsafe.
    """


@dataclass(frozen=True, slots=True)
class SessionRef:
    """A stable reference to one terminal session.

    ``service`` and ``session_id`` together survive a rescan, which is what lets
    a user's selection be re-bound to the same tab rather than to a numeric
    label that another tab could later reuse (vision DANGER 20).
    """

    adapter: str
    service: str
    session_id: str

    def key(self) -> str:
        return f"{self.adapter}/{self.service}{self.session_id}"


@dataclass(frozen=True, slots=True)
class TerminalSession:
    """A session as observed during one scan."""

    ref: SessionRef
    shell_pid: int
    foreground_pid: int
    title: str


class TerminalAdapter(ABC):
    """Adapter for one terminal emulator."""

    #: Short adapter name, used in :class:`SessionRef` keys and in logs.
    name: str = "abstract"

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this adapter can be used on this machine right now."""

    @abstractmethod
    def list_sessions(self) -> list[TerminalSession]:
        """Enumerate every session this adapter can see.

        Must not raise for a session that vanished mid-scan; such sessions are
        simply omitted.
        """

    @abstractmethod
    def foreground_pid(self, ref: SessionRef) -> int:
        """Return the current foreground PID of ``ref``, or 0 if it is gone."""

    @abstractmethod
    def read_visible_text(self, ref: SessionRef, lines: int = DEFAULT_VISIBLE_LINES) -> list[str]:
        """Return at most ``lines`` of the currently displayed text.

        The result is bounded on purpose. Callers must never persist it; only
        its fingerprint may be logged.
        """

    @abstractmethod
    def send_text(self, ref: SessionRef, text: str) -> None:
        """Send ``text`` verbatim to ``ref``.

        The adapter performs no interpretation: a caller that wants a newline
        includes ``\\r`` in ``text``. Callers are responsible for having
        revalidated process identity immediately beforehand.
        """
