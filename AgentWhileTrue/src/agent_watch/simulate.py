"""Runnable safety scenarios.

Section 40 of the vision lists the situations that must be exercised before the
tool can be trusted, and points out the practical problem: a real quota reset
takes hours, so none of them can be reproduced on demand. These scenarios drive
the whole supervisor against an in-memory terminal and a controllable clock, so
each one runs in milliseconds.

They exist for two audiences. The test suite asserts on them, which is how the
guarantees stay true as the code changes. And ``agent-watch simulate <name>``
lets a person watch a specific danger play out and read the decisions the
supervisor made, which is a far better way to gain confidence in a tool that
types into terminals than reading its source.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from agent_watch.config import Config, Mode, Policy
from agent_watch.fsm import Supervisor
from agent_watch.logging_setup import setup
from agent_watch.proc import ProcessIdentity, ProcessInfo
from agent_watch.quota import Availability, QuotaSnapshot, QuotaSource, QuotaWindow, unknown
from agent_watch.state_store import StateStore
from agent_watch.terminal.fake import FakeAdapter

SESSION = "/Sessions/1"
AGENT_PID = 15102
START = datetime(2026, 9, 5, 19, 30, tzinfo=UTC)

CLAUDE_EXE = "/home/user/.local/share/claude/versions/2.1.261"
CODEX_EXE = "/opt/@openai/codex/bin/codex"

BLOCKED_SCREEN = [
    "  ⎿  You've hit your session limit · resets in 5m",
    "",
    "❯ ",
]
READY_SCREEN = [
    "● Usage limit has reset · press enter to continue",
    "",
    "❯ ",
]
ACTIVE_SCREEN = ["● Reading src/main.py", "", "❯ "]
SHELL_SCREEN = ["user@host ~/project %"]
SELF_HEALING_SCREEN = [
    "● Usage limit reached · resets in 5m",
    "  Continuing automatically when your limit resets",
    "❯ ",
]
CODEX_BLOCKED_SCREEN = ["▌ You've hit your usage limit. Try again at 8:10 PM.", "", "› "]


@dataclass(slots=True)
class Step:
    """One thing that happened, and what the supervisor decided about it."""

    label: str
    decision_reason: str
    sent: int


@dataclass(slots=True)
class Result:
    """The outcome of one scenario."""

    name: str
    description: str
    expectation: str
    passed: bool
    steps: list[Step] = field(default_factory=list)
    sent: list[tuple[str, str]] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            f"scenario   {self.name}",
            f"about      {self.description}",
            f"expects    {self.expectation}",
            "",
        ]
        lines.extend(
            f"  {index:>2}. {step.label:<44} -> {step.decision_reason} (sent={step.sent})"
            for index, step in enumerate(self.steps, start=1)
        )
        lines.append("")
        lines.append(f"keystrokes {self.sent or 'none'}")
        lines.append(f"result     {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)


# -- the simulated world ---------------------------------------------------


@dataclass(slots=True)
class _Clock:
    wall: datetime = START
    monotonic: float = 1000.0

    def advance(self, seconds: float) -> None:
        self.wall = self.wall.fromtimestamp(self.wall.timestamp() + seconds, tz=UTC)
        self.monotonic += seconds

    def suspend(self, seconds: float) -> None:
        """Wall time passes; the monotonic clock barely moves."""
        self.wall = self.wall.fromtimestamp(self.wall.timestamp() + seconds, tz=UTC)
        self.monotonic += 1.0


@dataclass(slots=True)
class _Processes:
    table: dict[int, ProcessInfo] = field(default_factory=dict)

    def agent(self, pid: int, *, provider: str = "claude", start_time: int = 111) -> ProcessInfo:
        claude = provider == "claude"
        info = ProcessInfo(
            identity=ProcessIdentity(
                pid=pid,
                start_time=start_time,
                tty="pts/3",
                exe=CLAUDE_EXE if claude else CODEX_EXE,
            ),
            ppid=1,
            comm="claude" if claude else "codex",
            cmdline=("claude", "--resume") if claude else (CODEX_EXE, "resume"),
            cwd="/home/user/project",
            environ_keys=frozenset({"HOME"}),
        )
        self.table[pid] = info
        return info

    def shell(self, pid: int) -> ProcessInfo:
        info = ProcessInfo(
            identity=ProcessIdentity(pid=pid, start_time=777, tty="pts/3", exe="/usr/bin/zsh"),
            ppid=1,
            comm="zsh",
            cmdline=("zsh",),
            cwd="/home/user/project",
            environ_keys=frozenset({"HOME"}),
        )
        self.table[pid] = info
        return info

    def inspect(self, pid: int) -> ProcessInfo | None:
        return self.table.get(pid)

    def identify(self, pid: int) -> ProcessIdentity | None:
        info = self.table.get(pid)
        return info.identity if info else None


@dataclass(slots=True)
class _Quota(QuotaSource):
    clock: _Clock
    provider: str = "claude"
    name: str = "simulated"
    availability: Availability = Availability.AVAILABLE
    windows: tuple[QuotaWindow, ...] = ()
    fresh: bool = True

    def snapshot(self, *, pid: int | None = None) -> QuotaSnapshot:
        del pid
        if self.availability is Availability.UNKNOWN:
            return unknown(self.provider, self.name, "simulated-unavailable")
        return QuotaSnapshot(
            provider=self.provider,
            availability=self.availability,
            source=self.name,
            observed_at=self.clock.wall if self.fresh else None,
            windows=self.windows,
        )


@dataclass(slots=True)
class World:
    """Everything a scenario can manipulate."""

    clock: _Clock
    terminal: FakeAdapter
    processes: _Processes
    supervisor: Supervisor
    quota: dict[str, _Quota]
    steps: list[Step] = field(default_factory=list)

    def step(self, label: str) -> None:
        """Advance the supervisor once and record what it decided."""
        decisions = self.supervisor.tick()
        reason = decisions[0].reason if decisions else "no-sessions"
        self.steps.append(Step(label=label, decision_reason=reason, sent=len(self.terminal.sent)))

    def screen(self, lines: list[str]) -> None:
        self.terminal.set_screen(SESSION, list(lines))


def _world(
    directory: Path,
    *,
    mode: Mode = Mode.AUTO,
    policy: Policy | None = None,
    provider: str = "claude",
    screen: list[str] | None = None,
) -> World:
    clock = _Clock()
    terminal = FakeAdapter()
    processes = _Processes()
    info = processes.agent(AGENT_PID, provider=provider)
    terminal.add(
        SESSION,
        shell_pid=100,
        foreground_pid=AGENT_PID,
        screen=list(screen or BLOCKED_SCREEN),
        title=f"project : {provider}",
    )
    quota = {
        "claude": _Quota(clock=clock, provider="claude"),
        "codex": _Quota(clock=clock, provider="codex"),
    }
    supervisor = Supervisor(
        terminal=terminal,
        config=Config(mode=mode, policy=policy or Policy()),
        store=StateStore.in_directory(directory).load(),
        quota_sources=dict(quota),
        log=setup(directory / "simulate.log"),
        inspector=processes,
        now_fn=lambda: clock.wall,
        monotonic_fn=lambda: clock.monotonic,
        verify_delay=5.0,
    )
    supervisor.select(terminal.ref(SESSION), info.identity, provider, "project")
    return World(
        clock=clock,
        terminal=terminal,
        processes=processes,
        supervisor=supervisor,
        quota=quota,
    )


# -- the scenarios ---------------------------------------------------------

ScenarioFn = Callable[[Path], Result]


def _result(name: str, description: str, expectation: str, world: World, passed: bool) -> Result:
    return Result(
        name=name,
        description=description,
        expectation=expectation,
        passed=passed,
        steps=world.steps,
        sent=list(world.terminal.sent),
    )


def scenario_reset_and_resume(directory: Path) -> Result:
    world = _world(directory)
    world.step("limit reached, waiting")
    world.screen(READY_SCREEN)
    world.clock.advance(300)
    world.step("limit reset, prompt offers to continue")
    world.screen(ACTIVE_SCREEN)
    world.clock.advance(10)
    world.step("verify the session resumed")
    return _result(
        "reset-and-resume",
        "The ordinary happy path: a five-hour window resets and the session continues.",
        "exactly one Enter is sent, and the resume is verified",
        world,
        passed=world.terminal.sent == [(SESSION, "\r")],
    )


def scenario_agent_exited(directory: Path) -> Result:
    world = _world(directory)
    world.step("limit reached, waiting")
    world.processes.shell(AGENT_PID + 1)
    world.terminal.set_foreground(SESSION, AGENT_PID + 1)
    world.screen(SHELL_SCREEN)
    world.clock.advance(300)
    world.step("agent exited; zsh now has the foreground")
    return _result(
        "agent-exited",
        "DANGER 2: the agent exits and a shell takes the foreground before the reset.",
        "nothing is typed, because typing here would run a command in zsh",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_pid_reused(directory: Path) -> Result:
    world = _world(directory, screen=READY_SCREEN)
    world.processes.agent(AGENT_PID, start_time=999999)
    world.step("same PID, different process")
    return _result(
        "pid-reused",
        "DANGER 1: the PID is recycled by an unrelated process.",
        "the identity mismatch is caught and nothing is typed",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_suspend_across_reset(directory: Path) -> Result:
    world = _world(directory)
    world.step("limit reached, reset scheduled")
    world.clock.suspend(6 * 3600)
    world.processes.shell(AGENT_PID + 2)
    world.terminal.set_foreground(SESSION, AGENT_PID + 2)
    world.screen(SHELL_SCREEN)
    world.step("laptop wakes six hours later; the agent is long gone")
    return _result(
        "suspend-across-reset",
        "DANGER 9: the machine sleeps through the reset and wakes much later.",
        "the stale schedule is discarded and nothing is replayed",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_stale_banner(directory: Path) -> Result:
    stale = [*READY_SCREEN, *[f"  build output line {n}" for n in range(60)], "❯ "]
    world = _world(directory, screen=stale)
    world.step("an old reset banner has scrolled far up the screen")
    return _result(
        "stale-banner",
        "DANGER 3: a limit message that is visible history, not the current state.",
        "the scrolled-away banner cannot trigger anything",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_weekly_limit_still_blocked(directory: Path) -> Result:
    world = _world(directory, screen=READY_SCREEN)
    world.quota["claude"].availability = Availability.EXHAUSTED
    world.quota["claude"].windows = (
        QuotaWindow("session", 4.0, None),
        QuotaWindow("weekly", 100.0, START),
    )
    world.step("five-hour window reset, weekly window still spent")
    return _result(
        "weekly-limit-still-blocked",
        "Vision section 25: one window resets while another is still exhausted.",
        "the still-spent weekly limit prevents the resume",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_provider_unavailable(directory: Path) -> Result:
    world = _world(directory)
    world.quota["claude"].availability = Availability.UNKNOWN
    world.step("limit reached; the quota source is unavailable")
    world.clock.advance(3600)
    world.step("well past the nominal reset, still no provider state")
    return _result(
        "provider-unavailable",
        "DANGER 19: the quota source is down when the reset time passes.",
        "auto mode fails closed rather than inferring that usage returned",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_self_healing_provider(directory: Path) -> Result:
    world = _world(directory, screen=SELF_HEALING_SCREEN)
    world.step("Claude says it will continue automatically")
    world.clock.advance(600)
    world.step("after the reset")
    return _result(
        "self-healing-provider",
        "Claude Code 2.1.234+ resumes itself and says so on screen.",
        "the supervisor stands down instead of racing the provider",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_duplicate_prompt(directory: Path) -> Result:
    world = _world(directory, screen=READY_SCREEN)
    world.step("ready prompt seen")
    for index in range(4):
        world.clock.advance(1)
        world.step(f"same prompt scanned again ({index + 1})")
    return _result(
        "duplicate-prompt",
        "DANGER 17: the same screen is scanned many times over.",
        "one logical prompt yields exactly one keystroke",
        world,
        passed=world.terminal.sent == [(SESSION, "\r")],
    )


def scenario_crash_between_send_and_persist(directory: Path) -> Result:
    world = _world(directory, screen=READY_SCREEN)
    world.step("ready prompt; the action is planned, sent and recorded")

    # Simulate a crash and restart: a brand new supervisor over the same state
    # directory and the same unchanged screen.
    restarted = _world(directory, screen=READY_SCREEN)
    restarted.processes.agent(AGENT_PID)
    restarted.step("after restart, the same prompt is still on screen")
    combined = World(
        clock=restarted.clock,
        terminal=restarted.terminal,
        processes=restarted.processes,
        supervisor=restarted.supervisor,
        quota=restarted.quota,
        steps=world.steps + restarted.steps,
    )
    return _result(
        "crash-recovery",
        "DANGER 13: the supervisor restarts with the same prompt still displayed.",
        "the persisted record prevents a second keystroke",
        combined,
        passed=restarted.terminal.sent == [],
    )


def scenario_codex_needs_opt_in(directory: Path) -> Result:
    world = _world(directory, provider="codex", screen=CODEX_BLOCKED_SCREEN)
    world.step("Codex is blocked and its window has reset")
    return _result(
        "codex-needs-opt-in",
        "Codex resume means typing into the composer, not pressing Enter.",
        "nothing is typed until the user opts in explicitly",
        world,
        passed=world.terminal.sent == [],
    )


def scenario_observe_mode(directory: Path) -> Result:
    world = _world(directory, mode=Mode.OBSERVE, screen=READY_SCREEN)
    world.step("ready prompt in observe mode")
    return _result(
        "observe-mode",
        "Observe mode runs the whole detection path.",
        "the decision is reached but no input is ever sent",
        world,
        passed=world.terminal.sent == [] and world.steps[0].decision_reason == "observe-mode",
    )


SCENARIOS: dict[str, ScenarioFn] = {
    "reset-and-resume": scenario_reset_and_resume,
    "agent-exited": scenario_agent_exited,
    "pid-reused": scenario_pid_reused,
    "suspend-across-reset": scenario_suspend_across_reset,
    "stale-banner": scenario_stale_banner,
    "weekly-limit-still-blocked": scenario_weekly_limit_still_blocked,
    "provider-unavailable": scenario_provider_unavailable,
    "self-healing-provider": scenario_self_healing_provider,
    "duplicate-prompt": scenario_duplicate_prompt,
    "crash-recovery": scenario_crash_between_send_and_persist,
    "codex-needs-opt-in": scenario_codex_needs_opt_in,
    "observe-mode": scenario_observe_mode,
}


def catalogue() -> list[tuple[str, str]]:
    """Every scenario name with its one-line description."""
    with tempfile.TemporaryDirectory() as directory:
        return [(name, run(name, Path(directory)).description) for name in SCENARIOS]


def run(name: str, directory: Path | None = None) -> Result:
    """Run one scenario. Raises ``KeyError`` for an unknown name."""
    scenario = SCENARIOS[name]
    if directory is not None:
        return scenario(directory / name)
    with tempfile.TemporaryDirectory() as temporary:
        return scenario(Path(temporary))


def run_all(directory: Path | None = None) -> list[Result]:
    return [run(name, directory) for name in SCENARIOS]


__all__ = ["SCENARIOS", "Result", "Step", "catalogue", "run", "run_all"]
