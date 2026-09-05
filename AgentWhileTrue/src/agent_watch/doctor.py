"""Environment diagnostics.

``agent-watch doctor`` exists so that an unsupported environment says so in one
screen instead of being discovered as a silent no-op hours later. It reports on
everything the supervisor depends on, and - importantly - states whether
automatic mode is currently safe, since that is the question the user actually
has.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from agent_watch.config import Config
from agent_watch.lock import LockHeldError, SingleInstanceLock
from agent_watch.terminal.konsole import KonsoleAdapter, find_qdbus

_VERSION_TIMEOUT_SECONDS = 15.0


class Status(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class Check:
    """One diagnostic line."""

    name: str
    status: Status
    detail: str = ""

    def render(self) -> str:
        return f"{self.name:<22} {self.status.value:<5} {self.detail}".rstrip()


def _tool_version(executable: str, *args: str) -> str | None:
    path = shutil.which(executable)
    if path is None:
        return None
    try:
        completed = subprocess.run(
            [path, *args],
            capture_output=True,
            text=True,
            timeout=_VERSION_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""


def _writable_dir(label: str, path: Path) -> Check:
    """Check that a directory exists, is ours, and can be written to.

    The label is passed in because all three of these directories can resolve
    to the same place, and three rows reading "agent-watch" would tell the
    reader nothing about which one is which.
    """
    name = label
    try:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        return Check(name, Status.FAIL, f"{path}: {exc.strerror}")
    if not os.access(path, os.W_OK):
        return Check(name, Status.FAIL, f"{path}: not writable")
    return Check(name, Status.OK, str(path))


def check_privileges() -> Check:
    """Running as root is not needed and makes every bug more expensive."""
    if os.geteuid() == 0:
        return Check("Privileges", Status.WARN, "running as root; use your desktop user")
    if os.geteuid() != os.getuid():
        return Check("Privileges", Status.WARN, "setuid context")
    return Check("Privileges", Status.OK, f"uid={os.getuid()}")


def check_platform() -> Check:
    if platform.system() != "Linux":
        return Check("Linux", Status.FAIL, platform.system())
    return Check("Linux", Status.OK, platform.release())


def check_desktop() -> Check:
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    session = os.environ.get("XDG_SESSION_TYPE", "")
    if "KDE" not in desktop.upper():
        return Check("KDE Plasma", Status.WARN, desktop or "not detected")
    return Check("KDE Plasma", Status.OK, f"{desktop} ({session or 'unknown session'})")


def check_qdbus() -> Check:
    found = find_qdbus()
    if found is None:
        return Check("qdbus", Status.FAIL, "install qdbus6 (qt6-tools)")
    return Check("qdbus", Status.OK, found)


def check_konsole(adapter: KonsoleAdapter) -> tuple[Check, Check, Check]:
    if not adapter.is_available():
        unavailable = Check("Konsole D-Bus", Status.FAIL, "no session bus or no qdbus")
        return (
            unavailable,
            Check("Konsole sessions", Status.FAIL, "cannot enumerate"),
            Check("Konsole input", Status.FAIL, "cannot probe"),
        )
    try:
        services = adapter.services()
    except Exception as exc:  # a broken bus must not crash the diagnostic
        return (
            Check("Konsole D-Bus", Status.FAIL, type(exc).__name__),
            Check("Konsole sessions", Status.FAIL, "cannot enumerate"),
            Check("Konsole input", Status.FAIL, "cannot probe"),
        )
    if not services:
        return (
            Check("Konsole D-Bus", Status.WARN, "no Konsole running"),
            Check("Konsole sessions", Status.WARN, "0 found"),
            Check("Konsole input", Status.WARN, "no session to probe"),
        )
    sessions = adapter.list_sessions()
    input_check = Check("Konsole input", Status.WARN, "no session to probe")
    if sessions:
        try:
            # Empty text exercises the security permission without typing.
            adapter.send_text(sessions[0].ref, "")
            input_check = Check("Konsole input", Status.OK, "sendText permitted")
        except Exception:
            input_check = Check(
                "Konsole input",
                Status.FAIL,
                "disabled; enable KonsoleWindow/EnableSecuritySensitiveDBusAPI and restart Konsole",
            )
    return (
        Check("Konsole D-Bus", Status.OK, f"{len(services)} service(s)"),
        Check("Konsole sessions", Status.OK, f"{len(sessions)} session(s)"),
        input_check,
    )


def check_agent(name: str, *args: str) -> Check:
    version = _tool_version(name, *args)
    if version is None:
        return Check(name.title(), Status.WARN, "not installed")
    return Check(name.title(), Status.OK, version or "installed")


def check_lock(config: Config) -> Check:
    lock = SingleInstanceLock.in_directory(config.resolved_runtime_dir())
    try:
        lock.acquire()
    except LockHeldError:
        return Check("Single instance", Status.WARN, "another agent-watch is running")
    except OSError as exc:
        return Check("Single instance", Status.FAIL, str(exc))
    lock.release()
    return Check("Single instance", Status.OK, str(lock.path))


def check_optional(name: str) -> Check:
    path = shutil.which(name)
    # Optional means optional: absence is informational, never a failure.
    return Check(name, Status.OK, path or "not installed (optional)")


def run(
    config: Config,
    *,
    adapter_factory: Callable[[], KonsoleAdapter] = KonsoleAdapter,
) -> list[Check]:
    """Run every diagnostic and return the results in display order."""
    adapter = adapter_factory()
    konsole_bus, konsole_sessions, konsole_input = check_konsole(adapter)
    checks = [
        check_platform(),
        check_desktop(),
        check_privileges(),
        check_qdbus(),
        konsole_bus,
        konsole_sessions,
        konsole_input,
        check_agent("codex", "--version"),
        check_agent("claude", "--version"),
        check_optional("fzf"),
        check_optional("jq"),
        _writable_dir("State dir", config.resolved_state_dir()),
        _writable_dir("Runtime dir", config.resolved_runtime_dir()),
        _writable_dir("Log dir", config.resolved_log_file().parent),
        check_lock(config),
    ]
    checks.append(_auto_mode_verdict(checks, config))
    return checks


def _auto_mode_verdict(checks: list[Check], config: Config) -> Check:
    """Answer the question the user actually has: can auto mode work here?"""
    blocking = [check for check in checks if check.status is Status.FAIL]
    if blocking:
        return Check("Auto mode", Status.FAIL, f"blocked by: {blocking[0].name}")
    if not config.policy.resume_after_reset:
        return Check("Auto mode", Status.WARN, "disabled by policy")
    return Check("Auto mode", Status.OK, "SAFE")


def render(checks: list[Check]) -> str:
    lines = ["Agent While True Doctor", ""]
    lines.extend(check.render() for check in checks)
    return "\n".join(lines)


def exit_code(checks: list[Check]) -> int:
    """0 when nothing failed, 1 otherwise, so CI and scripts can rely on it."""
    return 1 if any(check.status is Status.FAIL for check in checks) else 0
