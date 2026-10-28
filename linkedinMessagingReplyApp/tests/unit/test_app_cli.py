# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The `lra selftest` and `lra screenshot` commands, service wiring and settings persistence."""

import logging
import stat
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image
from pytestqt.qtbot import QtBot

from linkedin_reply_assistant import app as app_module
from linkedin_reply_assistant.app import (
    build_services,
    image_selector,
    make_pipeline,
    portal_selector,
)
from linkedin_reply_assistant.browser_bridge.server import BridgeServer
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.cli import main
from linkedin_reply_assistant.config.loader import load_config
from linkedin_reply_assistant.events import setup_logging
from linkedin_reply_assistant.extraction.vision import HybridExtractor
from linkedin_reply_assistant.portal.runner import AsyncRunner
from linkedin_reply_assistant.shortcuts.base import DisabledShortcuts
from linkedin_reply_assistant.shortcuts.portal_global_shortcuts import PortalGlobalShortcuts
from linkedin_reply_assistant.state.settings import (
    Settings,
    load_settings,
    save_settings,
    settings_path,
)


def test_selftest_offline(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["--config-dir", str(tmp_path), "selftest"]) == 0
    out = capsys.readouterr().out
    assert "selftest    OK" in out and "sales_outreach" in out and "demo / demo" in out


def test_selftest_reports_failure(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from linkedin_reply_assistant import cli

    blank = tmp_path / "blank.png"
    Image.new("RGB", (900, 560), "white").save(blank)
    monkeypatch.setattr(cli, "defaults_file", lambda name: blank)
    assert main(["--config-dir", str(tmp_path), "selftest"]) == 1
    assert (
        "FAILED: extraction did not find the sample conversation; no draft"
        in capsys.readouterr().out
    )


def test_selftest_unexpected_category(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "reply_rules.yaml").write_text(
        (Path(app_module.__file__).parent / "defaults" / "reply_rules.yaml")
        .read_text()
        .replace("category: sales_outreach", "category: recruiting")
    )
    assert main(["--config-dir", str(tmp_path), "selftest"]) == 1
    assert "unexpected category recruiting" in capsys.readouterr().out


def test_screenshot(qtbot: QtBot, tmp_path: Path) -> None:
    out = tmp_path / "ui.png"
    assert main(["--config-dir", str(tmp_path), "screenshot", str(out)]) == 0
    with Image.open(out) as image:
        assert image.width >= 1200
    assert not (tmp_path / ".lra-screenshot-state.yaml").exists()


def test_build_services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_config(tmp_path)
    monkeypatch.setenv("LRA_BRIDGE_SOCKET", str(tmp_path / "run" / "b.sock"))
    services = build_services(config, tmp_path, demo=True, image=tmp_path / "x.png")
    assert isinstance(services.shortcuts, DisabledShortcuts)
    assert services.settings_path == tmp_path / "state.yaml"
    assert services.bridge_connected() is False
    assert [c.name for c in services.preflight()][-1].startswith("ai")
    portal = build_services(config, None, bridge=BridgeServer(tmp_path / "p.sock"))
    assert isinstance(portal.shortcuts, PortalGlobalShortcuts)
    hybrid = replace(
        config, app=replace(config.app, extraction=replace(config.app.extraction, mode="hybrid"))
    )
    assert isinstance(make_pipeline(hybrid, portal.manager).extractor, HybridExtractor)


def test_bridge_start_failure_is_tolerated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("LRA_BRIDGE_SOCKET", str(blocker / "sub" / "b.sock"))
    services = build_services(load_config(tmp_path), tmp_path, demo=True, image=tmp_path / "x.png")
    assert services.bridge_connected() is False


def test_selectors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, token = image_selector(tmp_path / "a.png")(None)
    assert token is None and source.name == "file a.png"

    class Fake:
        def __init__(self, runner: object) -> None:
            self.runner = runner

        def select(self, restore_token: str | None) -> str:
            return f"new-{restore_token}"

    monkeypatch.setattr(app_module, "PortalCaptureSource", Fake)
    runner = AsyncRunner()
    selected, new = portal_selector(runner)("old")
    runner.stop()
    assert new == "new-old" and isinstance(selected, Fake)


def test_settings_round_trip(tmp_path: Path) -> None:
    path = settings_path(tmp_path)
    assert load_settings(path) == Settings()
    saved = Settings(Roi(0.1, 0.1, 0.5, 0.5), "token", "Ctrl+Alt+L", True)
    save_settings(path, saved)
    assert load_settings(path) == saved
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    path.write_text("- a list")
    assert load_settings(path) == Settings()
    path.write_text("roi: [unclosed")
    assert load_settings(path) == Settings()


def test_settings_default_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings_path() == tmp_path / "linkedin-reply-assistant" / "state.yaml"


def test_setup_logging() -> None:
    setup_logging(logging.WARNING)
