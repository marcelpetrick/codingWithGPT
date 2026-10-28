# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Command line entry point `lra`."""

import argparse
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from importlib import resources
from pathlib import Path

from linkedin_reply_assistant.backends.factory import build_manager
from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.capture.source import ImageFileSource
from linkedin_reply_assistant.config.loader import Config, ConfigError, load_config
from linkedin_reply_assistant.diagnostics.preflight import format_report, run_preflight
from linkedin_reply_assistant.version import __version__

# The conversation panel of the bundled self-test image (a Capture Test Window rendering).
SELFTEST_ROI = Roi(0.27, 0.0, 0.73, 0.84)


def defaults_file(name: str) -> Path:
    return Path(str(resources.files("linkedin_reply_assistant") / "defaults" / name))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lra",
        description="LinkedIn Reply Assistant: capture, draft, insert. Never sends.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config-dir", type=Path, help="override ~/.config/linkedin-reply-assistant"
    )
    commands = parser.add_subparsers(dest="command")
    gui = commands.add_parser("gui", help="start the desktop application")
    gui.add_argument("--demo", action="store_true", help="offline demo backend instead of Ollama")
    gui.add_argument("--image", type=Path, help="capture from an image file instead of the portal")
    commands.add_parser("preflight", help="report what this desktop and the AI backends support")
    selftest = commands.add_parser("selftest", help="run the whole pipeline on a bundled image")
    selftest.add_argument("--live", action="store_true", help="use the configured Ollama backends")
    window = commands.add_parser("test-window", help="show the deterministic Capture Test Window")
    window.add_argument("--sample", default="friendly_connection_01")
    window.add_argument("--theme", choices=["light", "dark"], default="light")
    window.add_argument("--zoom", type=float, default=1.0)
    shot = commands.add_parser("screenshot", help="render the real main window to a PNG (demo)")
    shot.add_argument("output", type=Path)
    shot.add_argument("--about", type=Path, help="also render the About dialog to this PNG")
    return parser


def cmd_preflight(config: Config) -> int:
    checks = run_preflight(build_manager(config.backends))
    print(format_report(checks))
    return 1 if any(c.status == "fail" for c in checks) else 0


def ocr_only(config: Config) -> Config:
    """The demo backend has no vision model, so offline runs extract with OCR."""
    extraction = replace(config.app.extraction, mode="ocr")
    return replace(config, app=replace(config.app, extraction=extraction))


def cmd_selftest(config: Config, live: bool) -> int:
    from linkedin_reply_assistant.app import make_manager, make_pipeline
    from linkedin_reply_assistant.extraction.base import ExtractionResult
    from linkedin_reply_assistant.pipeline import run_full
    from linkedin_reply_assistant.reply_engine.generator import Draft

    if not live:
        config = ocr_only(config)
    pipeline = make_pipeline(config, make_manager(config, demo=not live))
    results: list[ExtractionResult] = []
    drafts: list[Draft] = []

    def on_step(step: str, payload: object) -> None:
        if isinstance(payload, tuple):
            results.append(payload[0])
        elif isinstance(payload, Draft):
            drafts.append(payload)

    source = ImageFileSource(defaults_file("selftest.png"))
    timings = run_full(pipeline, 1, source, SELFTEST_ROI, CancelToken(), on_step)
    result = results[0]
    print(f"capture     {timings.capture_ms:.0f} ms")
    print(f"extraction  {result.extractor} {timings.extraction_ms:.0f} ms, {result.participant!r}")
    problems = []
    if result.participant != "Kevin Doyle":
        problems.append("extraction did not find the sample conversation")
    if not drafts:
        problems.append("no draft")
    else:
        draft = drafts[0]
        category = draft.classification.category
        print(f"category    {category} ({draft.classification.source})")
        print(f"backend     {draft.result.backend} / {draft.result.model}")
        print(f"generation  {timings.generation_ms:.0f} ms")
        print(f"draft       {draft.reply!r}")
        if category != "sales_outreach":
            problems.append(f"unexpected category {category}")
    print("selftest    " + ("FAILED: " + "; ".join(problems) if problems else "OK"))
    return 1 if problems else 0


def cmd_test_window(sample: str, theme: str, zoom: float) -> int:  # pragma: no cover - interactive
    from PySide6.QtWidgets import QApplication

    from linkedin_reply_assistant.model import load_conversation
    from linkedin_reply_assistant.testwindow import CaptureTestWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = CaptureTestWindow(
        load_conversation(defaults_file(f"samples/{sample}.yaml")), theme, zoom
    )
    window.show()
    return int(app.exec())


def cmd_screenshot(
    config: Config, config_dir: Path | None, output: Path, about: Path | None = None
) -> int:
    """Render the real main window after a demo Capture & Draft (used for the README)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from linkedin_reply_assistant.app import build_services
    from linkedin_reply_assistant.browser_bridge.server import BridgeServer
    from linkedin_reply_assistant.shortcuts.base import DisabledShortcuts
    from linkedin_reply_assistant.state.settings import Settings
    from linkedin_reply_assistant.ui.controller import Controller
    from linkedin_reply_assistant.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    config = replace(
        config, app=replace(config.app, extraction=replace(config.app.extraction, mode="ocr"))
    )
    bridge = BridgeServer(output.parent / ".lra-screenshot.sock")
    services = build_services(
        config,
        config_dir,
        demo=True,
        image=defaults_file("selftest.png"),
        bridge=bridge,
        shortcuts=DisabledShortcuts("Global hotkey: Ctrl+Alt+L (example)"),
    )
    services = replace(services, settings_path=output.parent / ".lra-screenshot-state.yaml")
    controller = Controller(services, Settings(roi=SELFTEST_ROI))
    window = MainWindow(controller)
    window.resize(1400, 780)
    window.show()
    controller.refresh_health()
    controller.select_source()
    deadline = time.monotonic() + 30
    stage = "select"
    while time.monotonic() < deadline:
        app.processEvents()
        if stage == "select" and controller.source is not None:
            controller.capture_and_draft()
            stage = "draft"
        if stage == "draft" and controller.workflow.draft is not None and window.checks:
            break
        time.sleep(0.02)
    window.refresh_bridge()
    app.processEvents()
    ok = window.grab().save(str(output), "PNG")
    if about is not None:
        dialog = window.show_about()
        app.processEvents()
        ok = dialog.grab().save(str(about), "PNG") and ok
        dialog.close()
    window.close()
    for leftover in (output.parent / ".lra-screenshot-state.yaml",):
        leftover.unlink(missing_ok=True)
    print(f"wrote {output}" if ok else f"cannot write {output}")
    return 0 if ok and controller.workflow.draft is not None else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        config = load_config(args.config_dir)
        if args.command == "preflight":
            return cmd_preflight(config)
        if args.command == "selftest":
            return cmd_selftest(config, args.live)
        if args.command == "screenshot":
            return cmd_screenshot(config, args.config_dir, args.output, args.about)
        if args.command == "test-window":  # pragma: no cover - interactive
            return cmd_test_window(args.sample, args.theme, args.zoom)
        from linkedin_reply_assistant.app import run_gui  # pragma: no cover - interactive

        return run_gui(config, args.config_dir, args.demo, args.image)  # pragma: no cover
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
