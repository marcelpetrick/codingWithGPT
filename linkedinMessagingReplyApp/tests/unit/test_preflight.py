# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

import pytest

from linkedin_reply_assistant.backends.base import Health
from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.diagnostics import preflight
from linkedin_reply_assistant.diagnostics.preflight import Check
from linkedin_reply_assistant.portal.bus import GLOBAL_SHORTCUTS, SCREENCAST
from tests.unit.backends.conftest import make_config
from tests.unit.backends.test_manager import FakeBackend


def test_session_checks() -> None:
    ok = preflight.check_session({"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"})
    assert [c.status for c in ok] == ["ok", "ok"]
    unknown = preflight.check_session({})
    assert [c.status for c in unknown] == ["warn", "warn"]


def test_portal_checks() -> None:
    both = preflight.check_portals(lambda: {SCREENCAST: 5, GLOBAL_SHORTCUTS: 2})
    assert [c.detail for c in both] == ["version 5", "version 2"]
    none = preflight.check_portals(lambda: {SCREENCAST: None, GLOBAL_SHORTCUTS: None})
    assert [c.status for c in none] == ["fail", "warn"]

    def broken() -> dict[str, int | None]:
        raise OSError("no bus")

    assert "OSError" in preflight.check_portals(broken)[0].detail


def test_pipewire_check(tmp_path: Path) -> None:
    assert preflight.check_pipewire({}, lambda n: True).status == "fail"
    env = {"XDG_RUNTIME_DIR": str(tmp_path)}
    assert "socket" in preflight.check_pipewire(env, lambda n: True).detail
    (tmp_path / "pipewire-0").touch()
    assert preflight.check_pipewire(env, lambda n: False).detail.endswith("missing")
    assert preflight.check_pipewire(env, lambda n: True).status == "ok"


def test_gst_has_element() -> None:
    assert preflight.gst_has_element("fakesrc")
    assert not preflight.gst_has_element("no-such-element")


def test_gst_has_element_without_gi(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real = builtins.__import__

    def fake_import(name: str, *args: object, **kw: object) -> object:
        if name == "gi":
            raise ImportError(name)
        return real(name, *args, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert not preflight.gst_has_element("fakesrc")


def test_tesseract_check(tmp_path: Path) -> None:
    missing = preflight.check_tesseract(which=lambda n: None)
    assert missing.status == "fail"
    seen: list[list[str]] = []

    def run(cmd: list[str]) -> str:
        seen.append(cmd)
        return "List of available languages (2):\nafr\nosd\n"

    no_eng = preflight.check_tesseract(lambda n: "/bin/t", run, tmp_path / "none")
    assert no_eng.detail == "no English data (afr osd)" and seen[0] == ["tesseract", "--list-langs"]
    ok = preflight.check_tesseract(lambda n: "/bin/t", lambda c: "List (1):\neng\ndeu\n", tmp_path)
    assert ok.status == "ok" and ok.detail == "languages eng deu"
    empty = preflight.check_tesseract(lambda n: "/bin/t", lambda c: "", tmp_path)
    assert empty.detail == "no English data (none)"


def test_tesseract_check_default_runner() -> None:
    check = preflight.check_tesseract()
    assert check.name == "tesseract"


def test_backend_checks() -> None:
    net = FakeBackend(make_config("net", 10), Health(True, "0.40", ("big:1", "eye:1")))
    local = FakeBackend(make_config("local", 20), Health(False, error="timeout after 300 ms"))
    other = FakeBackend(make_config("other", 30), Health(True, "0.40", ("x:1",)))
    checks = preflight.check_backends(BackendManager([net, local, other], 30))
    assert checks[0].status == "ok" and "reply model big:1" in checks[0].detail
    assert "(HTTP)" in checks[0].detail
    assert checks[1].detail.endswith("timeout after 300 ms")
    assert checks[2].status == "warn" and "reply model missing" in checks[2].detail
    dead = FakeBackend(make_config("net", 10), Health(False, error="down"))
    assert preflight.check_backends(BackendManager([dead], 30))[-1].status == "fail"


def test_bridge_check() -> None:
    assert preflight.check_bridge(None).status == "warn"
    assert preflight.check_bridge("connected").status == "ok"
    assert preflight.check_bridge("disconnected").status == "warn"


def test_run_preflight_and_report(tmp_path: Path) -> None:
    net = FakeBackend(make_config("net", 10), Health(True, "0.40", ("big:1",)))
    (tmp_path / "pipewire-0").touch()
    checks = preflight.run_preflight(
        BackendManager([net], 30),
        env={
            "XDG_SESSION_TYPE": "wayland",
            "XDG_CURRENT_DESKTOP": "KDE",
            "XDG_RUNTIME_DIR": str(tmp_path),
        },
        portal_probe=lambda: {SCREENCAST: 5, GLOBAL_SHORTCUTS: 2},
        has_element=lambda n: True,
        tesseract=lambda: Check("tesseract", "ok", "languages eng"),
        bridge_status="connected",
    )
    assert all(c.status == "ok" for c in checks)
    report = preflight.format_report(checks)
    assert report.splitlines()[0].startswith("OK    session")


def test_default_portal_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(address: str | None = None) -> dict[str, int | None]:
        return {SCREENCAST: 1}

    monkeypatch.setattr(preflight, "portal_versions", fake)
    assert preflight.default_portal_probe() == {SCREENCAST: 1}
