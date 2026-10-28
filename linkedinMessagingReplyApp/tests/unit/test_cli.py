# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

import pytest

import linkedin_reply_assistant
from linkedin_reply_assistant.cli import main


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert linkedin_reply_assistant.__version__ in capsys.readouterr().out


def test_no_arguments_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "Never sends" in capsys.readouterr().out


def test_preflight_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    from linkedin_reply_assistant import cli
    from linkedin_reply_assistant.diagnostics.preflight import Check

    results = [[Check("a", "ok", "fine")], [Check("a", "fail", "broken")]]
    monkeypatch.setattr(cli, "run_preflight", lambda manager: results.pop(0))
    assert main(["--config-dir", str(tmp_path), "preflight"]) == 0
    assert "OK    a  fine" in capsys.readouterr().out
    assert main(["preflight"]) == 1


def test_config_error_exit_code(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "app.yaml").write_text("- not a mapping\n")
    assert main(["--config-dir", str(tmp_path), "preflight"]) == 2
    assert "configuration error" in capsys.readouterr().err
