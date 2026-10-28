# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Preflight: detect what this desktop supports, never assume it (VISION §5)."""

import asyncio
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.paths import tessdata_dir as default_tessdata_dir
from linkedin_reply_assistant.portal.bus import GLOBAL_SHORTCUTS, SCREENCAST, portal_versions

Status = Literal["ok", "warn", "fail"]


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str


def check_session(env: Mapping[str, str]) -> list[Check]:
    session = env.get("XDG_SESSION_TYPE", "")
    desktop = env.get("XDG_CURRENT_DESKTOP", "")
    return [
        Check(
            "session",
            "ok" if session == "wayland" else "warn",
            session or "unknown (XDG_SESSION_TYPE not set)",
        ),
        Check("desktop", "ok" if desktop else "warn", desktop or "unknown"),
    ]


def check_portals(probe: Callable[[], dict[str, int | None]]) -> list[Check]:
    try:
        versions = probe()
    except Exception as exc:  # noqa: BLE001 - any bus failure means "portal not usable"
        detail = f"D-Bus session bus not usable: {type(exc).__name__}"
        return [
            Check("screencast portal", "fail", detail),
            Check("global shortcuts", "warn", detail),
        ]
    screencast = versions.get(SCREENCAST)
    shortcuts = versions.get(GLOBAL_SHORTCUTS)
    return [
        Check(
            "screencast portal",
            "ok" if screencast else "fail",
            f"version {screencast}" if screencast else "missing: capture needs it",
        ),
        Check(
            "global shortcuts",
            "ok" if shortcuts else "warn",
            f"version {shortcuts}" if shortcuts else "missing: use the Capture & Draft button",
        ),
    ]


def default_portal_probe() -> dict[str, int | None]:
    return asyncio.run(asyncio.wait_for(portal_versions(), timeout=3))


def check_pipewire(env: Mapping[str, str], has_element: Callable[[str], bool]) -> Check:
    runtime = env.get("XDG_RUNTIME_DIR", "")
    socket = Path(runtime) / "pipewire-0" if runtime else None
    if socket is None or not socket.exists():
        return Check("pipewire", "fail", "no PipeWire socket in XDG_RUNTIME_DIR")
    if not has_element("pipewiresrc"):
        return Check("pipewire", "fail", "GStreamer element pipewiresrc missing")
    return Check("pipewire", "ok", f"socket {socket}, pipewiresrc present")


def gst_has_element(name: str) -> bool:
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        Gst.init(None)
        return Gst.ElementFactory.find(name) is not None
    except ImportError, ValueError:
        return False


def check_tesseract(
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[[list[str]], str] | None = None,
    tessdata_dir: Path | None = None,
) -> Check:
    if which("tesseract") is None:
        return Check("tesseract", "fail", "not installed: OCR extraction unavailable")
    command = ["tesseract", "--list-langs"]
    tessdata_dir = default_tessdata_dir() if tessdata_dir is None else tessdata_dir
    if tessdata_dir.is_dir():
        command[1:1] = ["--tessdata-dir", str(tessdata_dir)]
    output = (run or _run)(command)
    langs = [line.strip() for line in output.splitlines()[1:] if line.strip()]
    if "eng" not in langs:
        return Check("tesseract", "fail", f"no English data ({' '.join(langs) or 'none'})")
    return Check("tesseract", "ok", "languages " + " ".join(langs))


def _run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    return result.stdout + result.stderr


def check_backends(manager: BackendManager) -> list[Check]:
    checks = []
    for backend, health in manager.health_report(refresh=True):
        config = backend.config
        where = f"{config.url} ({config.scheme.upper()})"
        if not health.reachable:
            checks.append(Check(f"ai {config.name}", "warn", f"{where}: {health.error}"))
            continue
        reply = next((m for m in config.reply_models if m in health.models), None)
        vision = next((m for m in config.vision_models if m in health.models), None)
        status: Status = "ok" if reply else "warn"
        detail = (
            f"{where} Ollama {health.version}, reply model {reply or 'missing'}, "
            f"vision model {vision or 'missing'}"
        )
        checks.append(Check(f"ai {config.name}", status, detail))
    selections, _ = manager.candidates("reply")
    if not selections:
        checks.append(Check("ai", "fail", "no backend can generate replies"))
    return checks


def check_bridge(status: str | None) -> Check:
    if status is None:
        return Check("browser extension", "warn", "bridge not running (starts with the app)")
    return Check("browser extension", "ok" if status == "connected" else "warn", status)


def run_preflight(
    manager: BackendManager,
    env: Mapping[str, str] | None = None,
    portal_probe: Callable[[], dict[str, int | None]] = default_portal_probe,
    has_element: Callable[[str], bool] = gst_has_element,
    tesseract: Callable[[], Check] = check_tesseract,
    bridge_status: str | None = None,
) -> list[Check]:
    env = os.environ if env is None else env
    return [
        *check_session(env),
        *check_portals(portal_probe),
        check_pipewire(env, has_element),
        tesseract(),
        check_bridge(bridge_status),
        *check_backends(manager),
    ]


def format_report(checks: list[Check]) -> str:
    marks = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}
    width = max(len(c.name) for c in checks)
    return "\n".join(f"{marks[c.status]}  {c.name:<{width}}  {c.detail}" for c in checks)
