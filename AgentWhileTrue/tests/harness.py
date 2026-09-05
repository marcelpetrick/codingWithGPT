"""A whole supervisor wired to fakes, so scenarios run in milliseconds.

Real quota resets take hours, so the danger cases from section 40 of the vision
can only be covered if the entire loop can be driven synthetically. This harness
provides a fake terminal, a fake process table and a controllable clock, and is
shared by the FSM tests and the ``simulate`` command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_watch.config import Config, Mode
from agent_watch.fsm import Supervisor
from agent_watch.logging_setup import setup
from agent_watch.proc import ProcessIdentity, ProcessInfo
from agent_watch.quota import Availability, QuotaSnapshot, QuotaSource, QuotaWindow, unknown
from agent_watch.state_store import StateStore
from agent_watch.terminal.fake import FakeAdapter

CLAUDE_EXE = "/home/user/.local/share/claude/versions/2.1.261"
CODEX_EXE = "/opt/@openai/codex/bin/codex"


@dataclass(slots=True)
class FakeInspector:
    """An injectable stand-in for ``/proc``."""

    processes: dict[int, ProcessInfo] = field(default_factory=dict)

    def add_claude(self, pid: int, *, start_time: int = 111, tty: str = "pts/3") -> ProcessInfo:
        info = ProcessInfo(
            identity=ProcessIdentity(pid=pid, start_time=start_time, tty=tty, exe=CLAUDE_EXE),
            ppid=1,
            comm="claude",
            cmdline=("claude", "--resume"),
            cwd="/home/user/project",
            environ_keys=frozenset({"HOME"}),
        )
        self.processes[pid] = info
        return info

    def add_codex(self, pid: int, *, start_time: int = 222, tty: str = "pts/5") -> ProcessInfo:
        info = ProcessInfo(
            identity=ProcessIdentity(pid=pid, start_time=start_time, tty=tty, exe=CODEX_EXE),
            ppid=1,
            comm="codex",
            cmdline=(CODEX_EXE, "resume"),
            cwd="/home/user/other",
            environ_keys=frozenset({"HOME"}),
        )
        self.processes[pid] = info
        return info

    def add_shell(self, pid: int, *, start_time: int = 333, tty: str = "pts/3") -> ProcessInfo:
        info = ProcessInfo(
            identity=ProcessIdentity(pid=pid, start_time=start_time, tty=tty, exe="/usr/bin/zsh"),
            ppid=1,
            comm="zsh",
            cmdline=("zsh",),
            cwd="/home/user",
            environ_keys=frozenset({"HOME"}),
        )
        self.processes[pid] = info
        return info

    def remove(self, pid: int) -> None:
        self.processes.pop(pid, None)

    def inspect(self, pid: int) -> ProcessInfo | None:
        return self.processes.get(pid)

    def identify(self, pid: int) -> ProcessIdentity | None:
        info = self.processes.get(pid)
        return info.identity if info else None


@dataclass(slots=True)
class ScriptedQuota(QuotaSource):
    """A quota source whose answer the test sets directly."""

    provider: str = "claude"
    name: str = "scripted"
    availability: Availability = Availability.AVAILABLE
    windows: tuple[QuotaWindow, ...] = ()
    observed_at: datetime | None = None
    note: str = ""

    def snapshot(self, *, pid: int | None = None) -> QuotaSnapshot:
        del pid
        if self.availability is Availability.UNKNOWN:
            return unknown(self.provider, self.name, self.note or "scripted-unknown")
        return QuotaSnapshot(
            provider=self.provider,
            availability=self.availability,
            source=self.name,
            observed_at=self.observed_at,
            windows=self.windows,
            note=self.note,
        )


@dataclass(slots=True)
class Clock:
    """A wall clock and a monotonic clock that can be moved independently.

    Moving only the wall clock is how a suspend or an NTP correction is
    simulated.
    """

    wall: datetime
    monotonic: float = 1000.0

    def advance(self, seconds: float) -> None:
        self.wall += timedelta(seconds=seconds)
        self.monotonic += seconds

    def suspend(self, seconds: float) -> None:
        """Wall time passes while the monotonic clock barely moves."""
        self.wall += timedelta(seconds=seconds)
        self.monotonic += 1.0

    def now(self) -> datetime:
        return self.wall

    def mono(self) -> float:
        return self.monotonic


@dataclass(slots=True)
class Harness:
    """Everything a scenario needs, already wired together."""

    terminal: FakeAdapter
    inspector: FakeInspector
    clock: Clock
    supervisor: Supervisor
    quota: dict[str, ScriptedQuota]

    @property
    def sent(self) -> list[tuple[str, str]]:
        return self.terminal.sent


def build(
    tmp_path: Path,
    *,
    mode: Mode = Mode.AUTO,
    now: datetime | None = None,
    confirm: bool | None = None,
    config: Config | None = None,
) -> Harness:
    """Wire a supervisor to fakes."""
    clock = Clock(wall=now or datetime(2026, 9, 5, 20, 0, tzinfo=UTC))
    terminal = FakeAdapter()
    inspector = FakeInspector()
    quota = {
        "claude": ScriptedQuota(provider="claude", observed_at=clock.wall),
        "codex": ScriptedQuota(provider="codex", observed_at=clock.wall),
    }
    effective = config or Config(mode=mode)
    supervisor = Supervisor(
        terminal=terminal,
        config=effective,
        store=StateStore.in_directory(tmp_path).load(),
        quota_sources=dict(quota),
        log=setup(tmp_path / "agent-watch.log"),
        inspector=inspector,
        confirm=None if confirm is None else (lambda observation, decision: confirm),
        now_fn=clock.now,
        monotonic_fn=clock.mono,
        verify_delay=5.0,
    )
    return Harness(
        terminal=terminal,
        inspector=inspector,
        clock=clock,
        supervisor=supervisor,
        quota=quota,
    )


def refresh_quota(harness: Harness) -> None:
    """Keep the scripted quota snapshots fresh as the clock advances."""
    for source in harness.quota.values():
        source.observed_at = harness.clock.wall
