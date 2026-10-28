# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Capture & Draft command (§8): one code path for the button and the hotkey.

The steps run in a worker thread. Each step checks the cancel token, and each step's time is
measured for the diagnostics (§22.4).
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from linkedin_reply_assistant.cancel import CancelToken
from linkedin_reply_assistant.capture.frame import Capture
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.capture.source import CaptureError, CaptureSource
from linkedin_reply_assistant.config.loader import Config
from linkedin_reply_assistant.events import EventLog
from linkedin_reply_assistant.extraction.base import (
    ExtractionContext,
    ExtractionResult,
    Extractor,
)
from linkedin_reply_assistant.extraction.language import guess_language
from linkedin_reply_assistant.reply_engine.generator import Draft, ReplyGenerator

SOURCE_UNAVAILABLE = "Browser capture source is unavailable. Select the browser window again."


@dataclass
class Timings:
    capture_ms: float = 0.0
    extraction_ms: float = 0.0
    generation_ms: float = 0.0
    started: float = field(default_factory=time.monotonic)

    @property
    def total_ms(self) -> float:
        return (time.monotonic() - self.started) * 1000


def generation_input(result: ExtractionResult | None, text: str) -> tuple[str, str]:
    """(incoming text, transcript). Structured messages are used unless the user edited the text."""
    if result is not None and text == result.raw_text and result.messages:
        incoming = [m.text for m in result.messages if m.direction == "incoming"]
        transcript = "\n".join(f"{m.sender}: {m.text}" for m in result.messages)
        return "\n".join(incoming) or transcript, transcript
    return text, text


class Pipeline:
    def __init__(
        self,
        config: Config,
        extractor: Extractor,
        generator: ReplyGenerator,
        events: EventLog,
        debug_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.extractor = extractor
        self.generator = generator
        self.events = events
        self.debug_dir = debug_dir

    def capture(
        self,
        seq: int,
        source: CaptureSource | None,
        roi: Roi | None,
        token: CancelToken,
        timings: Timings,
    ) -> Capture:
        start = time.monotonic()
        token.raise_if_cancelled()
        if source is None or not source.is_ready():
            raise CaptureError(SOURCE_UNAVAILABLE)
        image = source.grab()
        capture = Capture(seq, image, source.name, roi)
        timings.capture_ms = (time.monotonic() - start) * 1000
        self.events(
            "capture_succeeded",
            seq=seq,
            size=f"{image.width}x{image.height}",
            roi=roi is not None,
            ms=round(timings.capture_ms),
        )
        if self.debug_dir is not None and self.config.app.save_debug_captures:
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            capture.cropped().save(self.debug_dir / f"capture-{stamp}-{seq}.png")
        return capture

    def extract(
        self, capture: Capture, token: CancelToken, timings: Timings
    ) -> tuple[ExtractionResult, bool]:
        start = time.monotonic()
        settings = self.config.app.extraction
        context = ExtractionContext(
            self.config.user_profile.name, settings.min_confidence, settings.min_characters, token
        )
        result = self.extractor.extract(capture.cropped(), context)
        timings.extraction_ms = (time.monotonic() - start) * 1000
        usable = len(result.raw_text.strip()) >= settings.min_characters
        self.events(
            "extraction_done",
            seq=capture.sequence_id,
            extractor=result.extractor,
            confidence=round(result.confidence, 2),
            warnings=len(result.warnings),
            ms=round(timings.extraction_ms),
        )
        return result, usable

    def draft(
        self,
        seq: int,
        result: ExtractionResult | None,
        text: str,
        token: CancelToken,
        timings: Timings,
        category: str | None = None,
    ) -> Draft:
        start = time.monotonic()
        incoming, transcript = generation_input(result, text)
        language = result.language if result is not None and text == result.raw_text else "und"
        if language == "und":
            language = guess_language(incoming)
        draft = self.generator.generate(incoming, transcript, language, token, category)
        timings.generation_ms = (time.monotonic() - start) * 1000
        self.events(
            "draft_ready",
            seq=seq,
            classification=draft.classification.category,
            source=draft.classification.source,
            backend=draft.result.backend,
            model=draft.result.model,
            generation_ms=round(timings.generation_ms),
            fallback=draft.result.fallback_used,
            reply=draft.reply,
        )
        return draft


def run_full(
    pipeline: Pipeline,
    seq: int,
    source: CaptureSource | None,
    roi: Roi | None,
    token: CancelToken,
    on_step: Callable[[str, object], None],
) -> Timings:
    """Run all steps. on_step("captured"|"extracted"|"drafted", payload) reports progress."""
    timings = Timings()
    capture = pipeline.capture(seq, source, roi, token, timings)
    on_step("captured", capture)
    result, usable = pipeline.extract(capture, token, timings)
    on_step("extracted", (result, usable))
    if not usable:
        return timings
    token.raise_if_cancelled()
    draft = pipeline.draft(seq, result, result.raw_text, token, timings)
    on_step("drafted", draft)
    return timings
