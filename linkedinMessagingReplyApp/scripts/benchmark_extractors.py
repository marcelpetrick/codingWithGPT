#!/usr/bin/env python3
# benchmark_extractors.py: compare OCR and vision extraction on the screenshot fixtures (D9).
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Usage:  .venv/bin/python scripts/benchmark_extractors.py [--backend NAME] [--model MODEL]
#         --backend picks one entry of backends.yaml (default: all, by priority).
#         --model overrides the vision model of that backend.
# Output: one Markdown table row per fixture and extractor: similarity, participant, seconds.
# Note:   Live: calls Ollama. Check the box with `curl <url>/api/ps` first; do not evict a model
#         someone else uses (AGENTS.md, "Tests and requests" 4).
# Exit:   0 done; 1 a backend was not usable.
import argparse
import difflib
import sys
import time
from dataclasses import replace
from pathlib import Path

import yaml
from PIL import Image

from linkedin_reply_assistant.backends.manager import BackendManager
from linkedin_reply_assistant.backends.ollama import OllamaBackend
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.config.loader import load_config
from linkedin_reply_assistant.extraction.base import ExtractionContext, ExtractionError
from linkedin_reply_assistant.extraction.ocr import TesseractExtractor
from linkedin_reply_assistant.extraction.vision import VisionExtractor
from linkedin_reply_assistant.model import load_conversation

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
ROI = Roi(0.27, 0.0, 0.73, 0.84)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend")
    parser.add_argument("--model")
    args = parser.parse_args()
    config = load_config()
    entries = [b for b in config.backends.backends if args.backend in (None, b.name)]
    if args.model:
        entries = [replace(b, vision_models=(args.model,)) for b in entries]
    manager = BackendManager([OllamaBackend(b) for b in entries], 30)
    extractors = [TesseractExtractor(config.app.extraction.ocr_languages), VisionExtractor(manager)]
    index = yaml.safe_load((FIXTURES / "screenshots" / "index.yaml").read_text())
    print("| fixture | extractor | similarity | participant ok | seconds | detail |")
    print("|---|---|---|---|---|---|")
    failed = False
    for name, meta in sorted(index.items()):
        conversation = load_conversation(FIXTURES / "messages" / f"{meta['messages']}.yaml")
        image = ROI.crop(Image.open(FIXTURES / "screenshots" / f"{name}.png").convert("RGB"))
        for extractor in extractors:
            start = time.monotonic()
            try:
                result = extractor.extract(image, ExtractionContext("Marcel", 55, 20))
            except ExtractionError as exc:
                print(f"| {name} | {extractor.name} | error | - | - | {exc} |")
                failed = True
                continue
            seconds = time.monotonic() - start
            got = " ".join(m.text for m in result.messages if m.direction == "incoming")
            similarity = difflib.SequenceMatcher(None, conversation.incoming_text(), got).ratio()
            ok = result.participant == conversation.participant
            cells = [name, extractor.name, f"{similarity:.3f}", ok, f"{seconds:.1f}", result.detail]
            print("| " + " | ".join(str(c) for c in cells) + " |")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
