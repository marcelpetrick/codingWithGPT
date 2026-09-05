"""Single-instance guard.

Two supervisors watching the same session would each decide, independently and
correctly, to press Enter once - and the session would receive it twice
(vision DANGER 4). An advisory ``flock`` on a file under ``$XDG_RUNTIME_DIR``
makes that impossible without needing a daemon or a PID file that can go stale.

The lock is held only by the modes that can send input. Observe mode does not
take it, so a read-only watcher can run alongside an automatic one.
"""

from __future__ import annotations

import fcntl
import os
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

LOCK_FILENAME = "agent-watch.lock"


class LockHeldError(RuntimeError):
    """Another instance already holds the lock."""


@dataclass(slots=True)
class SingleInstanceLock:
    """An advisory, non-blocking ``flock`` on a runtime-directory file."""

    path: Path
    _fd: int | None = None

    @classmethod
    def in_directory(cls, directory: Path) -> SingleInstanceLock:
        return cls(path=directory / LOCK_FILENAME)

    def acquire(self) -> None:
        """Take the lock, or raise :class:`LockHeldError`.

        The PID is written for diagnostics only. It is never read back to decide
        anything, because a PID file is exactly the stale-state problem
        ``flock`` exists to avoid.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            raise LockHeldError(f"another agent-watch holds {self.path}") from exc
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def __enter__(self) -> SingleInstanceLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()
