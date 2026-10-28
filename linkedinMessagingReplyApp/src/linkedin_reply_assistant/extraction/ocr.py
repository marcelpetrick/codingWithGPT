# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local OCR with the Tesseract command line tool (§9.2). TSV output gives word confidences."""

import csv
import io
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

from linkedin_reply_assistant.capture.frame import png_bytes
from linkedin_reply_assistant.extraction.base import (
    ExtractionContext,
    ExtractionError,
    ExtractionResult,
)
from linkedin_reply_assistant.extraction.language import guess_language
from linkedin_reply_assistant.extraction.layout import split_messages
from linkedin_reply_assistant.extraction.quality import quality_warnings
from linkedin_reply_assistant.paths import tessdata_dir

Runner = Callable[[list[str], bytes], tuple[int, str, str]]
TARGET_TEXT_HEIGHT = 1400  # small captures are scaled up; Tesseract likes ~30 px capitals


def run_tesseract(command: list[str], data: bytes) -> tuple[int, str, str]:
    result = subprocess.run(command, input=data, capture_output=True, timeout=60, check=False)
    return result.returncode, result.stdout.decode("utf-8", "replace"), result.stderr.decode()


def preprocess(image: Image.Image) -> Image.Image:
    """Grayscale, dark theme to dark-on-light, and moderate upscaling. Nothing more (§9.2)."""
    gray = ImageOps.grayscale(image)
    if ImageStat.Stat(gray).mean[0] < 110:
        gray = ImageOps.invert(gray)
    if gray.height < TARGET_TEXT_HEIGHT / 2:
        factor = 2
        gray = gray.resize((gray.width * factor, gray.height * factor), Image.Resampling.LANCZOS)
    return gray


def parse_tsv(tsv: str) -> tuple[list[str], float]:
    """Return text lines and the mean word confidence (0..1) from Tesseract TSV output."""
    lines: dict[tuple[int, int, int], list[str]] = {}
    confidences: list[float] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        if row.get("level") != "5":
            continue
        word = (row.get("text") or "").strip()
        conf = float(row.get("conf") or -1)
        if not word or conf < 0:
            continue
        key = (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))
        lines.setdefault(key, []).append(word)
        confidences.append(conf)
    text_lines = [" ".join(words) for _, words in sorted(lines.items())]
    mean = sum(confidences) / len(confidences) / 100 if confidences else 0.0
    return text_lines, mean


class TesseractExtractor:
    name = "ocr"

    def __init__(
        self,
        languages: str = "eng+deu",
        runner: Runner = run_tesseract,
        which: Callable[[str], str | None] = shutil.which,
        tessdata: Path | None = None,
    ) -> None:
        self.languages = languages
        self._runner = runner
        self._which = which
        self._tessdata = tessdata_dir() if tessdata is None else tessdata

    def command(self) -> list[str]:
        command = ["tesseract", "stdin", "stdout", "-l", self.languages, "--psm", "4"]
        if self._tessdata.is_dir():
            command += ["--tessdata-dir", str(self._tessdata)]
        return command + ["-c", "tessedit_create_tsv=1"]

    def extract(self, image: Image.Image, context: ExtractionContext) -> ExtractionResult:
        if self._which("tesseract") is None:
            raise ExtractionError("Tesseract is not installed")
        context.cancel.raise_if_cancelled()
        code, out, err = self._runner(self.command(), png_bytes(preprocess(image)))
        context.cancel.raise_if_cancelled()
        if code != 0:
            raise ExtractionError(f"Tesseract failed: {err.strip()[:200]}")
        lines, confidence = parse_tsv(out)
        raw = "\n".join(lines)
        participant, messages = split_messages(lines, context.owner_name)
        incoming = " ".join(m.text for m in messages if m.direction == "incoming") or raw
        warnings = quality_warnings(raw, confidence, context.min_confidence, context.min_characters)
        if not messages:
            warnings.append("no message header (name + time) found; check the capture region")
        return ExtractionResult(
            raw_text=raw,
            messages=messages,
            participant=participant,
            confidence=confidence,
            language=guess_language(incoming),
            warnings=tuple(warnings),
            extractor=self.name,
            detail=f"Tesseract {self.languages}",
        )
