# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import runpy
import sys
from pathlib import Path

import pytest

from conftest import NOW, FakeHome
from tokenusage2.cli import main, resolve_tz
from tokenusage2.store import Store
from tokenusage2.version import __version__


def call(
    args: list[str], env: dict[str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    code = main(args, env=env, proc=tmp_path / "proc", clock=lambda: NOW)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0
    assert f"tokenusage2 {__version__}" in capsys.readouterr().out


def test_demo_frame(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = call(
        ["--demo", "--once", "--tz", "Europe/Berlin", "--width", "120", "--height", "40"],
        {"HOME": str(tmp_path)},
        tmp_path,
        capsys,
    )
    lines = out.rstrip("\n").split("\n")
    assert code == 0
    assert len(lines) == 40
    assert {len(line) for line in lines} == {120}
    assert "DEMO" in lines[0]


def test_demo_json_is_redactable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = call(
        ["--demo", "--json", "--redact", "--period", "week", "--tz", "UTC"],
        {"HOME": str(tmp_path)},
        tmp_path,
        capsys,
    )
    data = json.loads(out)
    assert code == 0
    assert data["period"] == "week"
    assert len(data["accounts"]) == 4
    assert data["accounts"][0]["identity"] == "y…@e….com"
    assert data["totals"]["all"]["total"] > 0
    assert data["buckets"]
    assert data["breakdown"]["by"] == "model"


def test_doctor_reports_discovery_and_reconciliation(
    home: FakeHome, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = call(
        ["--doctor", "--no-archive", "--tz", "Europe/Berlin"], home.env, tmp_path, capsys
    )
    assert code == 0
    for needle in (
        "found via rc:.zshrc",
        "work@corp.example",
        "ollama@10.0.0.5",
        "parsed 3.3k vs Codex threads.tokens_used 3.3k (+0.0%)",
        "quota 5h: 22%",
        "in memory",
        "database · 1 events",
        "claude-proxy",
    ):
        assert needle in out
    for secret in ("SECRET", "sk-secret", "secret@"):
        assert secret not in out


def test_live_frame_uses_the_archive(
    home: FakeHome, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive.sqlite"
    args = [
        "--once",
        "--archive",
        str(archive),
        "--tz",
        "Europe/Berlin",
        "--width",
        "160",
        "--height",
        "48",
        "--color",
        "never",
    ]
    code, out, _ = call(args, home.env, tmp_path, capsys)
    assert code == 0
    assert "work@corp.example" in out
    assert "codex-client" in out
    assert archive.exists()
    code, out, _ = call([*args, "--color", "always"], home.env, tmp_path, capsys)
    assert code == 0
    assert "\x1b[" in out


def test_account_filter(home: FakeHome, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = call(
        ["--json", "--no-archive", "--account", "codex-work", "--tz", "UTC"],
        home.env,
        tmp_path,
        capsys,
    )
    data = json.loads(out)
    assert code == 0
    assert [account["label"] for account in data["accounts"]] == ["codex-work"]
    assert data["totals"]["all"]["total"] == 5000
    code, _, err = call(["--json", "--no-archive", "--account", "nope"], home.env, tmp_path, capsys)
    assert code == 2
    assert "unknown account" in err


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--tz", "Mars/Olympus"], "unknown time zone"),
        (["--interval", "0"], "--interval"),
        (["--config", "/nonexistent/tokenusage2.toml"], "config file not found"),
    ],
)
def test_usage_errors(
    home: FakeHome,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
    message: str,
) -> None:
    code, _, err = call([*args, "--once", "--no-archive"], home.env, tmp_path, capsys)
    assert code == 2
    assert message in err


def test_incompatible_archive(
    home: FakeHome, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "old.sqlite"
    store = Store(path)
    store.set_meta("schema", "0")
    store.commit()
    store.close()
    code, _, err = call(["--once", "--archive", str(path)], home.env, tmp_path, capsys)
    assert code == 2
    assert "schema 0" in err


def test_dashboard_needs_a_terminal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = call(["--demo"], {"HOME": str(tmp_path)}, tmp_path, capsys)
    assert code == 2
    assert "needs a terminal" in err


def test_no_color_selects_the_plain_theme(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = call(
        [
            "--demo",
            "--once",
            "--color",
            "always",
            "--tz",
            "UTC",
            "--width",
            "100",
            "--height",
            "30",
        ],
        {"HOME": str(tmp_path), "NO_COLOR": "1"},
        tmp_path,
        capsys,
    )
    assert code == 0
    assert "\x1b[" not in out


def test_resolve_tz() -> None:
    assert str(resolve_tz(None, {"TZ": ":Europe/Berlin"})) == "Europe/Berlin"
    assert str(resolve_tz("UTC", {})) == "UTC"
    assert resolve_tz(None, {}) is not None


def test_module_entry_point(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["tokenusage2", "--version"])
    with pytest.raises(SystemExit) as stop:
        runpy.run_module("tokenusage2", run_name="__main__")
    assert stop.value.code == 0
    assert "tokenusage2" in capsys.readouterr().out
