# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Wire the services together and run the desktop application."""

import contextlib
import sys
from collections.abc import Callable
from pathlib import Path

from linkedin_reply_assistant.backends.demo import DemoBackend
from linkedin_reply_assistant.backends.factory import build_manager
from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.browser_bridge.inserter import Inserter
from linkedin_reply_assistant.browser_bridge.protocol import socket_path
from linkedin_reply_assistant.browser_bridge.server import BridgeServer
from linkedin_reply_assistant.capture.portal_source import PortalCaptureSource
from linkedin_reply_assistant.capture.source import CaptureSource, ImageFileSource
from linkedin_reply_assistant.config.loader import Config, user_config_dir
from linkedin_reply_assistant.diagnostics.preflight import run_preflight
from linkedin_reply_assistant.events import EventLog, setup_logging
from linkedin_reply_assistant.extraction.ocr import TesseractExtractor
from linkedin_reply_assistant.extraction.vision import build_extractor
from linkedin_reply_assistant.paths import user_state_dir
from linkedin_reply_assistant.pipeline import Pipeline
from linkedin_reply_assistant.portal.runner import AsyncRunner
from linkedin_reply_assistant.reply_engine.generator import ReplyGenerator
from linkedin_reply_assistant.shortcuts.base import DisabledShortcuts, ShortcutService
from linkedin_reply_assistant.shortcuts.portal_global_shortcuts import PortalGlobalShortcuts
from linkedin_reply_assistant.state.settings import load_settings, settings_path
from linkedin_reply_assistant.ui.controller import Controller, Services, SourceSelector


def make_manager(config: Config, demo: bool) -> BackendManager:
    if demo:
        return BackendManager([DemoBackend()], config.backends.health_cache_seconds)
    return build_manager(config.backends)


def make_pipeline(config: Config, manager: BackendManager) -> Pipeline:
    ocr = TesseractExtractor(config.app.extraction.ocr_languages)
    extractor = build_extractor(config.app.extraction.mode, ocr, manager)
    events = EventLog(config.app.log_message_text)
    return Pipeline(
        config,
        extractor,
        ReplyGenerator(config, manager),
        events,
        user_state_dir() / "debug_captures",
    )


def image_selector(path: Path) -> SourceSelector:
    def select(restore_token: str | None) -> tuple[CaptureSource, str | None]:
        return ImageFileSource(path), None

    return select


def portal_selector(runner: AsyncRunner) -> SourceSelector:
    def select(restore_token: str | None) -> tuple[CaptureSource, str | None]:
        source = PortalCaptureSource(runner)
        return source, source.select(restore_token)

    return select


def build_services(
    config: Config,
    config_dir: Path | None,
    demo: bool = False,
    image: Path | None = None,
    bridge: BridgeServer | None = None,
    shortcuts: ShortcutService | None = None,
    runner_factory: Callable[[], AsyncRunner] = AsyncRunner,
) -> Services:
    manager = make_manager(config, demo)
    pipeline = make_pipeline(config, manager)
    runner = runner_factory()
    if bridge is None:
        bridge = BridgeServer(socket_path())
        with contextlib.suppress(OSError):  # no insertion then; Copy Draft still works (§21.6)
            bridge.start()
    if shortcuts is None:
        shortcuts = DisabledShortcuts() if image is not None else PortalGlobalShortcuts(runner)
    selector = image_selector(image) if image is not None else portal_selector(runner)
    active_bridge = bridge
    return Services(
        config=config,
        manager=manager,
        pipeline=pipeline,
        select_source=selector,
        shortcuts=shortcuts,
        inserter=Inserter(active_bridge),
        bridge_connected=lambda: active_bridge.connected,
        preflight=lambda: run_preflight(manager, bridge_status=active_bridge.status),
        # Image/demo runs must not overwrite the real ScreenCast restore token or ROI.
        settings_path=settings_path(config_dir or user_config_dir()).with_name(
            "state-image.yaml" if image is not None else "state.yaml"
        ),
        debug_dir=user_state_dir() / "debug_captures",
        events=pipeline.events,
    )


def run_gui(config: Config, config_dir: Path | None, demo: bool, image: Path | None) -> int:
    from PySide6.QtWidgets import QApplication

    from linkedin_reply_assistant.ui.main_window import MainWindow

    setup_logging()
    app = QApplication.instance() or QApplication(sys.argv)
    QApplication.setApplicationName("LinkedIn Reply Assistant")
    QApplication.setDesktopFileName("io.github.marcelpetrick.LinkedInReplyAssistant")
    services = build_services(config, config_dir, demo, image)
    settings = load_settings(services.settings_path)
    controller = Controller(services, settings)
    window = MainWindow(controller)
    window.show()
    controller.start()
    if image is not None:
        controller.select_source()
    return int(app.exec())
