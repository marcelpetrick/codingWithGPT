"""Terminal adapters.

The supervisor talks to terminals only through :class:`TerminalAdapter`, so a
future Kitty or WezTerm adapter can be added without touching the state machine,
and so tests can drive the whole system through :class:`FakeAdapter`.
"""

from __future__ import annotations

from agent_watch.terminal.base import (
    SessionRef,
    TerminalAdapter,
    TerminalError,
    TerminalSession,
    TerminalUnavailableError,
)

__all__ = [
    "SessionRef",
    "TerminalAdapter",
    "TerminalError",
    "TerminalSession",
    "TerminalUnavailableError",
]
