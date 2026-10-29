# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests: vision images, keyword checker, image messages for both protocols."""

from __future__ import annotations

import base64
import json
import struct
import zlib

from mvo import vision, workloads
from mvo.client import Engine, build_request, openai_messages


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", data[16:24])
    idat_len = struct.unpack(">I", data[33:37])[0]
    raw = zlib.decompress(data[41 : 41 + idat_len])
    return width, height, raw


def test_png_is_valid_and_drawn() -> None:
    width, height, raw = decode_png(vision.TASKS[0].png)
    assert (width, height) == (320, 200)
    assert len(raw) == height * (1 + 3 * width)
    row = raw[100 * (1 + 3 * width) : 101 * (1 + 3 * width)]
    assert row[1 + 3 * 80 : 1 + 3 * 81] == bytes(vision.RED)  # inside the square
    assert row[1 + 3 * 230 : 1 + 3 * 231] == bytes(vision.BLUE)  # circle centre
    assert row[1 + 3 * 5 : 1 + 3 * 6] == bytes(vision.WHITE)


def test_five_tasks_with_stable_images() -> None:
    assert [t.task_id for t in vision.TASKS] == ["shapes", "count", "bars", "flag", "position"]
    assert base64.b64decode(vision.TASKS[1].b64) == vision.TASKS[1].png
    assert vision.TASKS[2].png == vision._bars()


def test_check_keywords() -> None:
    assert vision.check("shapes", "The square is red; on the right is a blue circle.")
    assert not vision.check("shapes", "The square is blue.")
    assert vision.check("count", "There are 3 green circles.")
    assert vision.check("count", "Three.")
    assert not vision.check("count", "13")
    assert vision.check("bars", "The third bar is the tallest, it is orange.")
    assert vision.check("flag", "Blue, white, red.")
    assert vision.check("position", "Top-right corner.")
    assert not vision.check("position", "top left")


def test_workload_v_messages() -> None:
    prompts = workloads.build("V", 4096)
    assert len(prompts) == 5 and prompts[0].prompt_id == "V-shapes"
    messages = prompts[0].as_messages("n1")
    assert messages[-1]["images"] == [vision.TASKS[0].b64]
    assert "images" not in messages[0]
    assert "images" not in workloads.workload_c()[0].as_messages("n")[-1]


def test_image_request_bodies() -> None:
    messages = workloads.workload_v()[1].as_messages("n")
    ollama = json.loads(build_request(Engine("o", "ollama", "http://h", "m"), messages, 8, 4096).data)  # type: ignore[arg-type]
    assert ollama["messages"][-1]["images"] == [vision.TASKS[1].b64]
    oai = json.loads(build_request(Engine("m", "openai", "http://h/v1", "m"), messages, 8, 4096).data)  # type: ignore[arg-type]
    parts = oai["messages"][-1]["content"]
    assert parts[0] == {"type": "text", "text": vision.TASKS[1].question}
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,iVBOR")
    assert oai["messages"][0]["content"].startswith("Request n.")
    assert openai_messages([{"role": "user", "content": "x"}]) == [{"role": "user", "content": "x"}]
