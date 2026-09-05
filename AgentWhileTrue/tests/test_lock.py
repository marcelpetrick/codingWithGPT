"""Tests for the single-instance lock."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from agent_watch.lock import LockHeldError, SingleInstanceLock

# The lock must exclude a separate *process*; two flocks from one process on
# separate descriptors do not conflict, so this has to be a real subprocess.
_CHILD = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, sys.argv[2])
    from agent_watch.lock import LockHeldError, SingleInstanceLock
    from pathlib import Path
    try:
        SingleInstanceLock(path=Path(sys.argv[1])).acquire()
    except LockHeldError:
        sys.exit(3)
    sys.exit(0)
    """
)


def _child_can_lock(path: Path) -> bool:
    source_root = str(Path(__file__).resolve().parent.parent / "src")
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, str(path), source_root],
        capture_output=True,
        check=False,
    )
    if completed.returncode not in (0, 3):
        pytest.fail(completed.stderr.decode())
    return completed.returncode == 0


def test_lock_excludes_a_second_process(tmp_path: Path) -> None:
    path = tmp_path / "agent-watch.lock"
    assert _child_can_lock(path)  # nobody holds it yet
    with SingleInstanceLock(path=path) as lock:
        assert lock.held
        assert not _child_can_lock(path)
    assert _child_can_lock(path)


def test_acquire_twice_raises(tmp_path: Path) -> None:
    path = tmp_path / "agent-watch.lock"
    with SingleInstanceLock(path=path), pytest.raises(LockHeldError):
        SingleInstanceLock(path=path).acquire()


def test_lock_file_is_owner_only(tmp_path: Path) -> None:
    lock = SingleInstanceLock.in_directory(tmp_path / "runtime")
    with lock:
        assert lock.path.stat().st_mode & 0o777 == 0o600
        assert lock.path.parent.stat().st_mode & 0o077 == 0


def test_release_is_idempotent(tmp_path: Path) -> None:
    lock = SingleInstanceLock(path=tmp_path / "agent-watch.lock")
    lock.acquire()
    lock.release()
    lock.release()
    assert not lock.held


def test_pid_is_written_for_diagnostics(tmp_path: Path) -> None:
    with SingleInstanceLock(path=tmp_path / "agent-watch.lock") as lock:
        assert lock.path.read_text().strip() == str(os.getpid())
