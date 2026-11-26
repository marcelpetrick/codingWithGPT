# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests for the command line (REQ-OPS-1, REQ-DB-2)."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from mrreview import cli
from mrreview.demo import fake_gitlab, fake_ollama
from mrreview.demo.fixture import build_fixture


@pytest.fixture
def servers(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with (
        fake_gitlab.serve(fake_gitlab.FakeGitLab(build_fixture(seed=3), token="cli-tok")) as gurl,
        fake_ollama.serve(fake_ollama.FakeOllama()) as ourl,
    ):
        monkeypatch.setenv("MRREVIEW_GITLAB_URL", gurl)
        monkeypatch.setenv("MRREVIEW_GITLAB_TOKEN", "cli-tok")
        monkeypatch.setenv("MRREVIEW_OLLAMA_URL", ourl)
        monkeypatch.setenv("MRREVIEW_OLLAMA_MODEL", fake_ollama.STUB_MODEL)
        yield


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "mrreview" in capsys.readouterr().out


def test_demo_stub(tmp_path: Path) -> None:
    assert cli.main(["demo", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "dashboard.html").stat().st_size > 50_000


def test_stage_commands(servers: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dbp = str(tmp_path / "x.sqlite3")
    assert cli.main(["--db", dbp, "collect", "--max-projects", "1", "--max-mrs", "4"]) == 0
    assert cli.main(["--db", dbp, "analyze", "--limit", "3"]) == 0
    assert cli.main(["--db", dbp, "evaluate"]) == 0
    assert cli.main(["--db", dbp, "report", "--demo", "--out", str(tmp_path / "r.html")]) == 0
    assert (tmp_path / "r.html").exists()
    capsys.readouterr()
    assert cli.main(["--db", dbp, "status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["projects_selected"] == 1
    assert cli.main(["--db", dbp, "sample", "--n", "2", "--out", str(tmp_path / "s.csv")]) == 0
    assert cli.main(["agreement", str(tmp_path / "s.csv")]) == 0
    assert '"intent"' in capsys.readouterr().out


def test_run_all(servers: None, tmp_path: Path) -> None:
    out = tmp_path / "d.html"
    args = [
        "--db",
        str(tmp_path / "y.sqlite3"),
        "run",
        "--out",
        str(out),
        "--max-projects",
        "1",
        "--max-mrs",
        "3",
    ]
    assert cli.main(args) == 0
    assert out.exists()


def test_smoke_requires_authorization(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["smoke", "--out", str(tmp_path)]) == 2
    assert "refused" in capsys.readouterr().err


def test_smoke_authorized(
    servers: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        cli.main(
            [
                "smoke",
                "--authorized",
                "--out",
                str(tmp_path),
                "--max-projects",
                "1",
                "--max-mrs",
                "2",
            ]
        )
        == 0
    )
    assert (tmp_path / "smoke_dashboard.html").exists()
    assert "done" in capsys.readouterr().out


def test_missing_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MRREVIEW_GITLAB_TOKEN", raising=False)
    monkeypatch.delenv("MRREVIEW_GITLAB_URL", raising=False)
    assert cli.main(["--db", str(tmp_path / "z.sqlite3"), "collect"]) == 1
    assert "MRREVIEW_GITLAB_TOKEN" in capsys.readouterr().err
    assert cli.main(["--db", str(tmp_path / "z.sqlite3"), "evaluate"]) == 1


def test_config_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "c.toml"
    cfg.write_text('gitlab_token = "x"\n', encoding="utf-8")
    assert cli.main(["--config", str(cfg), "status"]) == 1
    assert "environment" in capsys.readouterr().err
