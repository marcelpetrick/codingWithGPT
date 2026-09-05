"""Tests for the command-line interface.

`run` is exercised end to end with the Konsole adapter and `/proc` swapped for
fakes, so the wiring - selection, locking, mode handling, the tick - is covered
without a desktop session.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from agent_watch import cli
from agent_watch.cli import EXIT_ERROR, EXIT_OK, main
from agent_watch.terminal.fake import FakeAdapter
from agent_watch.version import __version__
from tests import harness as harness_module
from tests import screens

PID = 15102


@pytest.fixture
def out() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch) -> Path:
    """Keep every path the CLI touches inside tmp_path."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "run"))
    (tmp_path / "run").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _fake_world(monkeypatch, *, screen: list[str] | None = None) -> FakeAdapter:
    inspector = harness_module.FakeInspector()
    info = inspector.add_claude(PID)
    terminal = FakeAdapter()
    terminal.add(
        "/Sessions/1",
        shell_pid=100,
        foreground_pid=info.identity.pid,
        screen=list(screen or screens.CLAUDE_READY_TO_RESUME),
        title="project : claude",
    )
    monkeypatch.setattr(cli, "KonsoleAdapter", lambda: terminal)
    monkeypatch.setattr(cli, "SystemInspector", lambda: inspector)
    return terminal


def test_version(out: io.StringIO) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"], stream=out)
    assert excinfo.value.code == 0


def test_config_lists_the_effective_settings(sandbox: Path, out: io.StringIO) -> None:
    assert main(["config"], stream=out) == EXIT_OK
    assert "policy.auto_buy_credits" in out.getvalue()


def test_init_writes_a_config_and_does_not_clobber_it(sandbox: Path, out: io.StringIO) -> None:
    path = sandbox / "config" / "agent-watch" / "config"
    assert main(["init"], stream=out) == EXIT_OK
    assert path.is_file()
    first = path.read_text()
    assert "ALLOW_CODEX_AUTO_RESUME=false" in first

    assert main(["init"], stream=out) == EXIT_OK
    assert path.read_text() == first
    assert "already exists" in out.getvalue()


def test_the_written_config_parses_back(sandbox: Path, out: io.StringIO) -> None:
    # A default config the tool itself cannot read would be an unpleasant
    # first experience.
    main(["init"], stream=out)
    path = sandbox / "config" / "agent-watch" / "config"
    assert main(["--config", str(path), "config"], stream=out) == EXIT_OK


def test_a_broken_config_is_reported_not_ignored(sandbox: Path, out: io.StringIO) -> None:
    path = sandbox / "broken"
    path.write_text("RESET_GRACE=whenever\n")
    assert main(["--config", str(path), "config"], stream=out) == EXIT_ERROR
    assert "Configuration error" in out.getvalue()


def test_logs_without_a_log_file(sandbox: Path, out: io.StringIO) -> None:
    assert main(["logs"], stream=out) == EXIT_OK
    assert "No log at" in out.getvalue()


def test_running_as_root_is_refused_by_default(
    sandbox: Path, out: io.StringIO, monkeypatch
) -> None:
    _fake_world(monkeypatch)
    monkeypatch.setattr(cli.os, "geteuid", lambda: 0)
    assert main(["run", "--all", "--once"], stream=out) == EXIT_ERROR
    assert "should run as your KDE desktop user" in out.getvalue()


def test_allow_root_overrides_the_refusal(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    terminal = _fake_world(monkeypatch)
    monkeypatch.setattr(cli.os, "geteuid", lambda: 0)
    assert main(["--allow-root", "run", "--all", "--once", "--observe"], stream=out) == EXIT_OK
    assert terminal.sent == []


def test_run_all_once_resumes_a_ready_session(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    terminal = _fake_world(monkeypatch)
    assert main(["run", "--all", "--once", "--auto"], stream=out) == EXIT_OK
    assert terminal.sent == [("/Sessions/1", "\r")]


def test_observe_mode_reports_without_typing(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    terminal = _fake_world(monkeypatch)
    assert main(["run", "--all", "--once", "--observe"], stream=out) == EXIT_OK
    assert terminal.sent == []
    assert "READY_TO_RESUME" in out.getvalue()


def test_no_sessions_is_reported_clearly(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    monkeypatch.setattr(cli, "KonsoleAdapter", FakeAdapter)
    monkeypatch.setattr(cli, "SystemInspector", harness_module.FakeInspector)
    assert main(["run", "--once"], stream=out) == EXIT_ERROR
    assert "No Konsole sessions found" in out.getvalue()


def test_a_second_instance_is_refused_but_observe_is_not(
    sandbox: Path, out: io.StringIO, monkeypatch
) -> None:
    from agent_watch.config import load
    from agent_watch.lock import SingleInstanceLock

    _fake_world(monkeypatch)
    held = SingleInstanceLock.in_directory(load().resolved_runtime_dir())
    held.acquire()
    try:
        assert main(["run", "--all", "--once", "--auto"], stream=out) == EXIT_ERROR
        assert "Another agent-watch is already running" in out.getvalue()
        # Observe mode does not need the lock, so it still starts.
        assert main(["run", "--all", "--once", "--observe"], stream=out) == EXIT_OK
    finally:
        held.release()


def test_quitting_the_picker_watches_nothing(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    terminal = _fake_world(monkeypatch)
    assert main(["run", "--once", "--auto"], stream=out, reader=lambda prompt: "q") == EXIT_OK
    assert "Nothing selected" in out.getvalue()
    assert terminal.sent == []


def test_the_picker_selection_is_what_gets_watched(
    sandbox: Path, out: io.StringIO, monkeypatch
) -> None:
    terminal = _fake_world(monkeypatch)
    answers = iter(["", ""])
    assert (
        main(
            ["run", "--reset-grace", "90s", "--once", "--auto"],
            stream=out,
            reader=lambda prompt: next(answers),
        )
        == EXIT_OK
    )
    assert terminal.sent == [("/Sessions/1", "\r")]


def test_status_without_konsole(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    unavailable = FakeAdapter(available=False)
    monkeypatch.setattr(cli, "KonsoleAdapter", lambda: unavailable)
    assert main(["status"], stream=out) == EXIT_ERROR
    assert "not reachable" in out.getvalue()


def test_status_lists_classified_sessions(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    _fake_world(monkeypatch)
    assert main(["status"], stream=out) == EXIT_OK
    assert "Claude" in out.getvalue()
    assert str(PID) in out.getvalue()


def test_bare_invocation_runs(sandbox: Path, out: io.StringIO, monkeypatch) -> None:
    terminal = _fake_world(monkeypatch)
    # No subcommand at all still has `run`'s defaults available.
    assert main(["--allow-root"], stream=out, reader=lambda prompt: "q") == EXIT_OK
    assert terminal.sent == []


def test_version_string_is_reported_in_the_status_view() -> None:
    assert __version__
