# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import json
from pathlib import Path

import pytest
from PIL import Image

from linkedin_reply_assistant.backends.base import BackendError
from linkedin_reply_assistant.cancel import Cancelled, CancelToken
from linkedin_reply_assistant.extraction.base import (
    ExtractionContext,
    ExtractionError,
    ExtractionResult,
)
from linkedin_reply_assistant.extraction.language import guess_language
from linkedin_reply_assistant.extraction.layout import split_messages
from linkedin_reply_assistant.extraction.ocr import TesseractExtractor, parse_tsv, preprocess
from linkedin_reply_assistant.extraction.quality import quality_warnings
from linkedin_reply_assistant.extraction.vision import (
    HybridExtractor,
    VisionExtractor,
    build_extractor,
)
from linkedin_reply_assistant.jsonout import JsonOutputError, parse_object
from tests.fakes import fake_manager

CTX = ExtractionContext("Marcel", 55, 20)
TSV_HEAD = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
)


def tsv(rows: list[tuple[int, int, int, float, str]]) -> str:
    lines = [TSV_HEAD, "1\t1\t0\t0\t0\t0\t0\t0\t10\t10\t-1\t"]
    lines += [f"5\t1\t{b}\t{p}\t{ln}\t1\t0\t0\t1\t1\t{c}\t{t}" for b, p, ln, c, t in rows]
    return "\n".join(lines) + "\n"


def test_language_guess() -> None:
    assert guess_language("Hi Marcel, thanks for the post") == "en"
    assert guess_language("Hallo Marcel, danke für die Nachricht") == "de"
    assert guess_language("Bonjour, merci pour") == "fr"
    assert guess_language("12345 ???") == "und"


def test_quality_warnings() -> None:
    assert quality_warnings("A normal sentence with enough text.", 0.9, 55, 20) == []
    warnings = quality_warnings("¤¤¤ §§§ ¤¤", 0.3, 55, 20)
    assert len(warnings) == 3
    assert quality_warnings("", 0.0, 55, 20)[0].startswith("almost no text")


def test_split_messages() -> None:
    lines = [
        "Tom Brandt",
        "Marcel 10:01 AM",
        "Thanks for reading.",
        "Tom Brandt · 10:20 AM",
        "In your article you used Qt.",
        "Did it scale?",
        "Julia 14.10",
    ]
    participant, messages = split_messages(lines, "Marcel Petrick")
    assert participant == "Tom Brandt"
    assert [m.direction for m in messages] == ["outgoing", "incoming"]
    assert messages[1].text == "In your article you used Qt. Did it scale?"
    assert messages[1].time == "10:20 AM"
    title_only, none = split_messages(["Anna Keller", "no header here"], "Marcel")
    assert title_only == "Anna Keller" and none == ()
    assert split_messages([], "") == (None, ())
    assert split_messages(["  "], "Marcel") == (None, ())


def test_parse_tsv() -> None:
    text = tsv(
        [(1, 1, 1, 96, "Hello"), (1, 1, 1, 90, "there"), (2, 1, 1, 80, "Bye"), (2, 1, 2, -1, "x")]
    )
    lines, conf = parse_tsv(text + "5\t1\t3\t1\t1\t1\t0\t0\t1\t1\t50\t \n")
    assert lines == ["Hello there", "Bye"]
    assert conf == pytest.approx((96 + 90 + 80) / 3 / 100)
    assert parse_tsv(TSV_HEAD + "\n") == ([], 0.0)


def test_preprocess_inverts_dark_and_scales_small() -> None:
    dark = preprocess(Image.new("RGB", (100, 50), "black"))
    assert dark.mode == "L" and dark.size == (200, 100) and dark.getpixel((0, 0)) == 255
    big = preprocess(Image.new("RGB", (100, 900), "white"))
    assert big.size == (100, 900)


def fake_runner(code: int, out: str, err: str = ""):  # type: ignore[no-untyped-def]
    seen: list[list[str]] = []

    def run(command: list[str], data: bytes) -> tuple[int, str, str]:
        seen.append(command)
        assert data.startswith(b"\x89PNG")
        return code, out, err

    return run, seen


def test_tesseract_extractor_with_fake_runner(tmp_path: Path) -> None:
    out = tsv(
        [
            (1, 1, 1, 95, "Anna"),
            (1, 1, 1, 95, "Keller"),
            (1, 1, 2, 95, "Anna"),
            (1, 1, 2, 95, "Keller"),
            (1, 1, 2, 95, "9:14"),
            (1, 1, 2, 95, "AM"),
            (1, 1, 3, 95, "Hi Marcel, thanks for accepting my request!"),
        ]
    )
    run, seen = fake_runner(0, out)
    extractor = TesseractExtractor("eng", run, lambda n: "/bin/tesseract", tmp_path)
    result = extractor.extract(Image.new("RGB", (50, 50), "white"), CTX)
    assert result.participant == "Anna Keller" and result.language == "en"
    assert not result.needs_review and result.extractor == "ocr"
    assert "--tessdata-dir" in seen[0]
    no_dir = TesseractExtractor("eng", run, lambda n: "/x", tmp_path / "missing")
    assert "--tessdata-dir" not in no_dir.command()


def test_tesseract_extractor_errors(tmp_path: Path) -> None:
    image = Image.new("RGB", (10, 10))
    with pytest.raises(ExtractionError, match="not installed"):
        TesseractExtractor(which=lambda n: None).extract(image, CTX)
    run, _ = fake_runner(1, "", "Failed loading language 'xx'")
    with pytest.raises(ExtractionError, match="Failed loading"):
        TesseractExtractor("xx", run, lambda n: "/x", tmp_path).extract(image, CTX)
    token = CancelToken()
    token.cancel()
    with pytest.raises(Cancelled):
        TesseractExtractor(which=lambda n: "/x").extract(image, ExtractionContext("M", 1, 1, token))


def test_tesseract_warns_without_header(tmp_path: Path) -> None:
    run, _ = fake_runner(0, tsv([(1, 1, 1, 95, "just some text without any header line")]))
    result = TesseractExtractor("eng", run, lambda n: "/x", tmp_path).extract(
        Image.new("RGB", (9, 9)), CTX
    )
    assert result.needs_review and "no message header" in result.warnings[-1]


def test_parse_object() -> None:
    assert parse_object('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(JsonOutputError, match="no JSON"):
        parse_object("nothing")
    with pytest.raises(JsonOutputError, match="invalid JSON"):
        parse_object("{nope}")


VISION_ANSWER = json.dumps(
    {
        "participant": "Kevin Doyle",
        "messages": [
            {"sender": "Marcel", "time": "1:00 PM", "text": "Hello", "direction": "outgoing"},
            {
                "sender": "Kevin Doyle",
                "time": "1:05 PM",
                "text": "Our platform cuts cloud costs.",
                "direction": "incoming",
            },
            {"sender": "x", "text": " "},
            "junk",
        ],
        "language": "EN",
    }
)


def test_vision_extractor() -> None:
    manager, backend = fake_manager(VISION_ANSWER)
    result = VisionExtractor(manager).extract(Image.new("RGB", (20, 20)), CTX)
    assert result.participant == "Kevin Doyle" and result.language == "en"
    assert [m.direction for m in result.messages] == ["outgoing", "incoming"]
    assert result.detail == "net / eye:1" and not result.needs_review
    request = backend.requests[0]
    assert request.images and "untrusted" in request.system and "Marcel" in request.system


def test_vision_extractor_fallback_fields_and_empty() -> None:
    answer = json.dumps(
        {"messages": [{"sender": "Ann", "text": "Thanks for the great talk yesterday!"}]}
    )
    manager, _ = fake_manager(answer)
    result = VisionExtractor(manager).extract(Image.new("RGB", (5, 5)), CTX)
    assert result.participant == "Ann" and result.language == "en"
    manager, _ = fake_manager("{}")
    empty = VisionExtractor(manager).extract(Image.new("RGB", (5, 5)), CTX)
    assert empty.participant is None and "no messages" in empty.warnings[-1]


@pytest.mark.parametrize("answer", ["not json", BackendError("down", reachable=False)])
def test_vision_extractor_errors(answer: str | BackendError) -> None:
    manager, _ = fake_manager(answer)
    with pytest.raises(ExtractionError, match="vision extraction failed"):
        VisionExtractor(manager).extract(Image.new("RGB", (5, 5)), CTX)


class Fixed:
    name = "fixed"

    def __init__(self, result: ExtractionResult | ExtractionError) -> None:
        self.result = result
        self.calls = 0

    def extract(self, image: Image.Image, context: ExtractionContext) -> ExtractionResult:
        self.calls += 1
        if isinstance(self.result, ExtractionError):
            raise self.result
        return self.result


def result(name: str, warnings: tuple[str, ...]) -> ExtractionResult:
    return ExtractionResult("t", (), None, 0.5, "en", warnings, name)


def test_hybrid_extractor() -> None:
    image = Image.new("RGB", (5, 5))
    good_ocr, vision = Fixed(result("ocr", ())), Fixed(result("vision", ()))
    assert HybridExtractor(good_ocr, vision).extract(image, CTX).extractor == "ocr"
    assert vision.calls == 0
    bad_ocr = Fixed(result("ocr", ("a", "b")))
    assert HybridExtractor(bad_ocr, vision).extract(image, CTX).extractor == "vision"
    worse = Fixed(result("vision", ("a", "b", "c")))
    assert HybridExtractor(bad_ocr, worse).extract(image, CTX).extractor == "ocr"
    failing = Fixed(ExtractionError("down"))
    kept = HybridExtractor(bad_ocr, failing).extract(image, CTX)
    assert kept.extractor == "ocr" and "vision fallback failed: down" in kept.warnings[-1]


def test_build_extractor() -> None:
    manager, _ = fake_manager("{}")
    ocr = Fixed(result("ocr", ()))
    assert build_extractor("ocr", ocr, manager) is ocr
    assert isinstance(build_extractor("vision", ocr, manager), VisionExtractor)
    assert isinstance(build_extractor("hybrid", ocr, manager), HybridExtractor)


def test_fix_pipes() -> None:
    from linkedin_reply_assistant.extraction.ocr import fix_pipes

    assert fix_pipes("this week? | can show you") == "this week? I can show you"
    assert fix_pipes("| think so") == "I think so"
    assert fix_pipes("a||b and x | y") == "a||b and x I y"
