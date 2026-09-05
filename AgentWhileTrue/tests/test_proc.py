"""Tests for ``/proc`` inspection and the PID-reuse-proof identity."""

from __future__ import annotations

import os

import pytest

from agent_watch import proc


def test_identify_self_matches_reality() -> None:
    me = proc.identify(os.getpid())
    assert me.pid == os.getpid()
    assert me.start_time > 0
    assert me.exe  # the running interpreter


def test_start_time_survives_a_comm_containing_spaces_and_parens(tmp_path, monkeypatch) -> None:
    # The kernel does not escape `comm`, so a process named ")x (y" would break
    # naive whitespace splitting. Fields must be taken after the LAST ')'.
    fake_root = tmp_path
    pid_dir = fake_root / "4242"
    pid_dir.mkdir()
    fields = " ".join(str(n) for n in range(3, 60))
    (pid_dir / "stat").write_text(f"4242 () x (y) {fields}\n")
    monkeypatch.setattr(proc, "PROC", fake_root)
    # Overall field 22 is starttime; our synthetic fields start at 3 and count
    # up, so field 22 holds the value 22.
    assert proc.read_start_time(4242) == 22


def test_missing_process_raises_process_gone(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(proc, "PROC", tmp_path)
    with pytest.raises(proc.ProcessGoneError):
        proc.read_start_time(1)


def test_environ_keys_never_expose_values(tmp_path, monkeypatch) -> None:
    pid_dir = tmp_path / "7"
    pid_dir.mkdir()
    (pid_dir / "environ").write_text("SSH_TTY=/dev/pts/3\0ANTHROPIC_API_KEY=sk-secret\0")
    monkeypatch.setattr(proc, "PROC", tmp_path)
    keys = proc.read_environ_keys(7)
    assert keys == {"SSH_TTY", "ANTHROPIC_API_KEY"}
    assert not any("secret" in key for key in keys)


def test_still_the_same_rejects_a_changed_start_time() -> None:
    me = proc.identify(os.getpid())
    assert proc.still_the_same(me)
    recycled = proc.ProcessIdentity(
        pid=me.pid, start_time=me.start_time + 1, tty=me.tty, exe=me.exe
    )
    assert not proc.still_the_same(recycled)


def test_still_the_same_is_false_for_a_vanished_pid() -> None:
    # PID 0 never appears in /proc.
    gone = proc.ProcessIdentity(pid=0, start_time=1, tty="", exe="")
    assert not proc.still_the_same(gone)


def test_identity_key_is_log_safe() -> None:
    identity = proc.ProcessIdentity(pid=123, start_time=456, tty="pts/1", exe="/usr/bin/zsh")
    assert identity.key() == "123:456"


def test_inspect_reports_cmdline_and_cwd_for_self() -> None:
    info = proc.inspect(os.getpid())
    assert info.cmdline
    assert info.cwd
    assert info.ppid > 0
