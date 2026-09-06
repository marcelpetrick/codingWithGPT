"""Process inspection via ``/proc`` and the composite identity built from it.

Linux reuses process IDs, so a PID on its own is never a safe handle for
something the supervisor is allowed to type into (vision DANGER 1). Every
decision in this project is therefore keyed on a :class:`ProcessIdentity` that
combines the PID with the kernel's start-time counter for that PID, the
controlling TTY and the executable. The start time is the decisive field: it is
assigned by the kernel at ``fork`` and a recycled PID gets a different one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROC = Path("/proc")

#: Field index of ``starttime`` in ``/proc/<pid>/stat``, counting from 1 as the
#: man page does, *after* the ``comm`` field has been split off.
_STARTTIME_FIELD = 22


class ProcessGoneError(LookupError):
    """The process disappeared while it was being inspected."""


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    """A handle for a process that survives PID reuse.

    Two identities are equal only when the PID *and* the kernel start time
    match, which is what makes ``==`` a safe revalidation check.
    """

    pid: int
    start_time: int
    tty: str
    exe: str

    def key(self) -> str:
        """A stable, log-safe string for this identity."""
        return f"{self.pid}:{self.start_time}"


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """Everything the classifier and the policy gate need about one process."""

    identity: ProcessIdentity
    ppid: int
    comm: str
    cmdline: tuple[str, ...]
    cwd: str
    environ_keys: frozenset[str]

    @property
    def pid(self) -> int:
        return self.identity.pid

    @property
    def exe(self) -> str:
        return self.identity.exe

    @property
    def tty(self) -> str:
        return self.identity.tty


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise ProcessGoneError(str(path)) from exc
    except (PermissionError, ProcessLookupError, OSError):
        # A process owned by another user, or one that exited mid-read. Either
        # way the supervisor must not act on it, so treat it as absent.
        return ""


def _read_link(path: Path) -> str:
    try:
        return str(path.readlink())
    except FileNotFoundError as exc:
        raise ProcessGoneError(str(path)) from exc
    except (PermissionError, OSError):
        return ""


def read_start_time(pid: int) -> int:
    """Return the kernel start-time counter for ``pid``.

    ``/proc/<pid>/stat`` embeds the command name in parentheses and that name
    may itself contain spaces or parentheses, so the fields are split after the
    *last* closing parenthesis rather than by naive whitespace splitting.
    """
    raw = _read_text(PROC / str(pid) / "stat")
    close = raw.rfind(")")
    if close == -1:
        raise ProcessGoneError(f"unparseable /proc/{pid}/stat")
    # After "pid (comm) ", field 3 is `state`; starttime is field 22 overall,
    # i.e. index 22 - 3 = 19 of the remainder.
    fields = raw[close + 2 :].split()
    index = _STARTTIME_FIELD - 3
    if len(fields) <= index:
        raise ProcessGoneError(f"truncated /proc/{pid}/stat")
    return int(fields[index])


def read_comm(pid: int) -> str:
    return _read_text(PROC / str(pid) / "comm").strip()


def read_ppid(pid: int) -> int:
    for line in _read_text(PROC / str(pid) / "status").splitlines():
        if line.startswith("PPid:"):
            return int(line.split()[1])
    return 0


def read_cmdline(pid: int) -> tuple[str, ...]:
    raw = _read_text(PROC / str(pid) / "cmdline")
    return tuple(part for part in raw.split("\0") if part)


def read_cwd(pid: int) -> str:
    return _read_link(PROC / str(pid) / "cwd")


def read_exe(pid: int) -> str:
    return _read_link(PROC / str(pid) / "exe")


def read_environ_keys(pid: int) -> frozenset[str]:
    """Return only the *names* of a process's environment variables.

    The values routinely hold tokens and credentials, so they are never read:
    the classifier only needs to know whether markers such as ``SSH_TTY`` or
    ``TMUX`` are present (vision DANGER 15).
    """
    raw = _read_text(PROC / str(pid) / "environ")
    return frozenset(entry.split("=", 1)[0] for entry in raw.split("\0") if "=" in entry)


def read_tty(pid: int) -> str:
    """Return the controlling terminal as a ``pts/N`` style name, or ``""``."""
    fd_dir = PROC / str(pid) / "fd"
    for fd in ("0", "1", "2"):
        target = _read_link(fd_dir / fd)
        if target.startswith("/dev/pts/") or target.startswith("/dev/tty"):
            return target.removeprefix("/dev/")
    return ""


def exists(pid: int) -> bool:
    return (PROC / str(pid)).is_dir()


def identify(pid: int) -> ProcessIdentity:
    """Build a reuse-proof identity for ``pid``.

    :raises ProcessGoneError: if the process vanished during inspection.
    """
    return ProcessIdentity(
        pid=pid,
        start_time=read_start_time(pid),
        tty=read_tty(pid),
        exe=read_exe(pid),
    )


def inspect(pid: int) -> ProcessInfo:
    """Collect the full process picture used by classification and policy."""
    identity = identify(pid)
    return ProcessInfo(
        identity=identity,
        ppid=read_ppid(pid),
        comm=read_comm(pid),
        cmdline=read_cmdline(pid),
        cwd=read_cwd(pid),
        environ_keys=read_environ_keys(pid),
    )


def children(pid: int) -> tuple[int, ...]:
    """Return the direct children of ``pid``.

    Needed because Codex ships as a Node shim that execs a native child, so the
    foreground process alone does not tell the whole story.
    """
    found: list[int] = []
    for task in (PROC / str(pid) / "task").glob("*"):
        try:
            raw = _read_text(task / "children")
        except ProcessGoneError:
            # Threads routinely disappear between glob() and read_text().
            # Losing one branch of discovery must not terminate the watcher.
            continue
        found.extend(int(part) for part in raw.split() if part.isdigit())
    return tuple(dict.fromkeys(found))


def still_the_same(identity: ProcessIdentity) -> bool:
    """Re-read ``/proc`` and report whether ``identity`` still describes reality.

    This is the check performed immediately before any input is injected
    (vision DANGER 2 and DANGER 18).
    """
    try:
        return identify(identity.pid) == identity
    except ProcessGoneError:
        return False
