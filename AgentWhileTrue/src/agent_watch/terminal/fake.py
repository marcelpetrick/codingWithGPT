"""A scriptable in-memory terminal adapter.

A real quota reset takes hours, so every dangerous path in this project has to
be reachable without one. :class:`FakeAdapter` lets a test or the ``simulate``
command drive an entire scenario - limit reached, reset, suspend, PID reuse,
process swap, crash mid-send - deterministically and in milliseconds.

It also records everything sent, which is how the idempotency guarantees are
asserted rather than assumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_watch.terminal.base import (
    DEFAULT_VISIBLE_LINES,
    SessionRef,
    TerminalAdapter,
    TerminalSession,
    TerminalUnavailableError,
)

ADAPTER_NAME = "fake"


@dataclass(slots=True)
class FakeSession:
    """One scripted session."""

    session_id: str
    shell_pid: int
    foreground_pid: int
    screen: list[str] = field(default_factory=list)
    title: str = ""
    #: When set, every call touching this session behaves as if the tab closed.
    closed: bool = False


@dataclass(slots=True)
class FakeAdapter(TerminalAdapter):
    """In-memory adapter over a dictionary of :class:`FakeSession`."""

    sessions: dict[str, FakeSession] = field(default_factory=dict)
    service: str = "fake.service-1"
    available: bool = True
    sent: list[tuple[str, str]] = field(default_factory=list)
    #: Set to make ``send_text`` raise, modelling a wedged terminal.
    send_fails: bool = False
    name: str = ADAPTER_NAME

    # -- construction helpers ---------------------------------------------

    def add(
        self,
        session_id: str,
        *,
        shell_pid: int,
        foreground_pid: int,
        screen: list[str] | None = None,
        title: str = "",
    ) -> SessionRef:
        self.sessions[session_id] = FakeSession(
            session_id=session_id,
            shell_pid=shell_pid,
            foreground_pid=foreground_pid,
            screen=list(screen or []),
            title=title,
        )
        return self.ref(session_id)

    def ref(self, session_id: str) -> SessionRef:
        return SessionRef(adapter=self.name, service=self.service, session_id=session_id)

    def set_screen(self, session_id: str, screen: list[str]) -> None:
        self.sessions[session_id].screen = list(screen)

    def set_foreground(self, session_id: str, pid: int) -> None:
        self.sessions[session_id].foreground_pid = pid

    def close(self, session_id: str) -> None:
        self.sessions[session_id].closed = True

    # -- adapter interface -------------------------------------------------

    def is_available(self) -> bool:
        return self.available

    def list_sessions(self) -> list[TerminalSession]:
        if not self.available:
            raise TerminalUnavailableError("fake adapter marked unavailable")
        return [
            TerminalSession(
                ref=self.ref(session.session_id),
                shell_pid=session.shell_pid,
                foreground_pid=session.foreground_pid,
                title=session.title,
            )
            for session in self.sessions.values()
            if not session.closed
        ]

    def foreground_pid(self, ref: SessionRef) -> int:
        session = self.sessions.get(ref.session_id)
        if session is None or session.closed:
            return 0
        return session.foreground_pid

    def read_visible_text(self, ref: SessionRef, lines: int = DEFAULT_VISIBLE_LINES) -> list[str]:
        session = self.sessions.get(ref.session_id)
        if session is None or session.closed:
            return []
        return session.screen[-lines:]

    def send_text(self, ref: SessionRef, text: str) -> None:
        session = self.sessions.get(ref.session_id)
        if session is None or session.closed:
            raise TerminalUnavailableError(f"session gone: {ref.key()}")
        if self.send_fails:
            raise TerminalUnavailableError(f"sendText failed for {ref.key()}")
        self.sent.append((ref.session_id, text))
