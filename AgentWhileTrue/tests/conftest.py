"""Shared fixtures.

The helpers here build ``ProcessInfo`` values that mirror what was observed on a
real Manjaro/KDE machine, so the classifier tests exercise the shapes that
actually occur rather than idealised ones.
"""

from __future__ import annotations

import pytest

from agent_watch.proc import ProcessIdentity, ProcessInfo


def make_info(
    *,
    pid: int = 1000,
    start_time: int = 123456,
    tty: str = "pts/3",
    exe: str = "/usr/bin/zsh",
    ppid: int = 999,
    comm: str = "zsh",
    cmdline: tuple[str, ...] = ("zsh",),
    cwd: str = "/home/user",
    environ_keys: frozenset[str] = frozenset({"HOME", "PATH"}),
) -> ProcessInfo:
    """Build a ``ProcessInfo`` without touching ``/proc``."""
    return ProcessInfo(
        identity=ProcessIdentity(pid=pid, start_time=start_time, tty=tty, exe=exe),
        ppid=ppid,
        comm=comm,
        cmdline=cmdline,
        cwd=cwd,
        environ_keys=environ_keys,
    )


@pytest.fixture
def info_factory():
    return make_info


@pytest.fixture(autouse=True)
def _isolate_process_tree(monkeypatch):
    """Keep classifier tests off the real process tree by default.

    Individual tests opt back in by patching these again.
    """
    from agent_watch import classify as classify_module

    monkeypatch.setattr(classify_module, "_child_comms", lambda pid: ())
    monkeypatch.setattr(classify_module, "_ancestor_blocker", lambda info: None)
    monkeypatch.setattr(classify_module, "_detect_container", lambda info: None)
