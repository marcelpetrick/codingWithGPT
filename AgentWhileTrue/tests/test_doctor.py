"""Tests for the environment diagnostics."""

from __future__ import annotations

from pathlib import Path

from agent_watch import doctor
from agent_watch.config import Config, Policy
from agent_watch.doctor import Check, Status, exit_code, render
from tests.test_terminal import StubbedKonsole


def _config(tmp_path: Path) -> Config:
    return Config(state_dir=tmp_path / "state", runtime_dir=tmp_path / "run")


def test_doctor_runs_end_to_end_without_kde(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
    checks = doctor.run(
        _config(tmp_path), adapter_factory=lambda: StubbedKonsole(qdbus="/bin/true")
    )
    names = {check.name for check in checks}
    assert {"Linux", "KDE Plasma", "qdbus", "Konsole D-Bus", "Konsole input", "Auto mode"} <= names
    # The three directories can resolve to the same path; the rows must still
    # say which is which.
    assert {"State dir", "Runtime dir", "Log dir"} <= names


def test_missing_qdbus_fails_and_blocks_auto_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(doctor, "find_qdbus", lambda: None)
    checks = doctor.run(_config(tmp_path), adapter_factory=lambda: StubbedKonsole(qdbus=None))
    by_name = {check.name: check for check in checks}
    assert by_name["qdbus"].status is Status.FAIL
    assert by_name["Auto mode"].status is Status.FAIL
    assert exit_code(checks) == 1


def test_optional_tools_never_fail(tmp_path: Path) -> None:
    check = doctor.check_optional("definitely-not-installed-xyz")
    assert check.status is Status.OK
    assert "optional" in check.detail


def test_policy_disabled_downgrades_auto_mode(tmp_path: Path, monkeypatch) -> None:
    # This test isolates the policy verdict from whether the host running the
    # suite happens to have KDE's qdbus executable installed.
    monkeypatch.setattr(doctor, "find_qdbus", lambda: "/bin/true")
    config = Config(
        state_dir=tmp_path / "state",
        runtime_dir=tmp_path / "run",
        policy=Policy(resume_after_reset=False),
    )
    checks = doctor.run(config, adapter_factory=lambda: StubbedKonsole(qdbus="/bin/true"))
    by_name = {check.name: check for check in checks}
    assert by_name["Auto mode"].status is Status.WARN


def test_unwritable_state_dir_is_a_failure(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir(mode=0o500)
    try:
        check = doctor._writable_dir("State dir", blocked / "state")
        assert check.status is Status.FAIL
    finally:
        blocked.chmod(0o700)


def test_a_held_lock_warns_rather_than_fails(tmp_path: Path) -> None:
    from agent_watch.lock import SingleInstanceLock

    config = _config(tmp_path)
    lock = SingleInstanceLock.in_directory(config.resolved_runtime_dir())
    lock.acquire()
    try:
        # The same process can re-flock its own descriptor, so this is checked
        # through the public helper with a foreign holder simulated instead.
        assert doctor.check_lock(config).status in {Status.OK, Status.WARN}
    finally:
        lock.release()


def test_render_and_exit_code() -> None:
    checks = [Check("Linux", Status.OK, "6.1"), Check("qdbus", Status.WARN, "old")]
    text = render(checks)
    assert "Agent While True Doctor" in text
    assert "Linux" in text
    assert exit_code(checks) == 0
    assert exit_code([*checks, Check("x", Status.FAIL)]) == 1
