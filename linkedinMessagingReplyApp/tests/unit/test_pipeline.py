# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import logging
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from linkedin_reply_assistant.backends.demo import DemoBackend
from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.cancel import Cancelled, CancelToken
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.capture.source import CaptureError, ImageFileSource
from linkedin_reply_assistant.config.loader import Config, load_config
from linkedin_reply_assistant.events import EventLog
from linkedin_reply_assistant.extraction.base import ExtractionResult
from linkedin_reply_assistant.extraction.ocr import TesseractExtractor
from linkedin_reply_assistant.model import Message
from linkedin_reply_assistant.pipeline import Pipeline, Timings, generation_input, run_full
from linkedin_reply_assistant.reply_engine.generator import ReplyGenerator
from tests.conftest import FIXTURES

SHOT = FIXTURES / "screenshots" / "dark_normal.png"
ROI = Roi(0.27, 0.0, 0.73, 0.84)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return load_config(tmp_path)


def make(config: Config, debug_dir: Path | None = None) -> Pipeline:
    generator = ReplyGenerator(config, BackendManager([DemoBackend()], 30))
    return Pipeline(config, TesseractExtractor(), generator, EventLog(), debug_dir)


def test_full_run_on_fixture(config: Config, caplog: pytest.LogCaptureFixture) -> None:
    steps: list[str] = []
    caplog.set_level(logging.INFO)
    timings = run_full(
        make(config),
        1,
        ImageFileSource(SHOT),
        ROI,
        CancelToken(),
        lambda name, payload: steps.append(name),
    )
    assert steps == ["captured", "extracted", "drafted"]
    assert timings.capture_ms > 0 and timings.extraction_ms > 0 and timings.total_ms > 0
    log = caplog.text
    assert "classification=sales_outreach" in log and "backend=demo" in log
    assert "Hi, thank you" not in log and "reply=<redacted" in log  # §20.1: no message text


def test_unusable_extraction_stops(config: Config, tmp_path: Path) -> None:
    blank = tmp_path / "blank.png"
    Image.new("RGB", (300, 200), "white").save(blank)
    steps: list[str] = []
    run_full(
        make(config),
        1,
        ImageFileSource(blank),
        None,
        CancelToken(),
        lambda name, payload: steps.append(name),
    )
    assert steps == ["captured", "extracted"]


def test_capture_errors_and_cancel(config: Config, tmp_path: Path) -> None:
    pipeline = make(config)
    with pytest.raises(CaptureError, match="Select the browser window again"):
        pipeline.capture(1, None, None, CancelToken(), Timings())
    with pytest.raises(CaptureError):
        pipeline.capture(1, ImageFileSource(tmp_path / "gone.png"), None, CancelToken(), Timings())
    token = CancelToken()
    token.cancel()
    with pytest.raises(Cancelled):
        run_full(pipeline, 1, ImageFileSource(SHOT), None, token, lambda n, p: None)


def test_debug_captures_only_when_enabled(config: Config, tmp_path: Path) -> None:
    debug = tmp_path / "debug"
    make(config, debug).capture(1, ImageFileSource(SHOT), ROI, CancelToken(), Timings())
    assert not debug.exists()
    enabled = replace(config, app=replace(config.app, save_debug_captures=True))
    make(enabled, debug).capture(2, ImageFileSource(SHOT), ROI, CancelToken(), Timings())
    assert len(list(debug.glob("capture-*-2.png"))) == 1


def test_generation_input() -> None:
    messages = (
        Message("Marcel", "Hi", direction="outgoing"),
        Message("Ann", "Hello back", direction="incoming"),
    )
    result = ExtractionResult("raw", messages, "Ann", 0.9, "en", (), "ocr")
    assert generation_input(result, "raw") == ("Hello back", "Marcel: Hi\nAnn: Hello back")
    assert generation_input(result, "edited") == ("edited", "edited")
    only_out = replace(result, messages=messages[:1])
    assert generation_input(only_out, "raw") == ("Marcel: Hi", "Marcel: Hi")
    assert generation_input(None, "t") == ("t", "t")


def test_draft_with_edited_text_guesses_language(config: Config) -> None:
    result = ExtractionResult("raw", (), "Ann", 0.9, "en", (), "ocr")
    draft = make(config).draft(
        3,
        result,
        "Hallo Marcel, danke für die Anfrage und die Stelle",
        CancelToken(),
        Timings(),
        "recruiting",
    )
    assert draft.language == "de" and draft.classification.source == "override"


def test_event_log_redaction(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    assert EventLog()("x", seq=1, text="secret") == "x seq=1 text=<redacted 6 chars>"
    assert EventLog(log_message_text=True)("x", text="secret") == "x text=secret"
