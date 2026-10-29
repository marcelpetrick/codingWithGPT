# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Workload V: is the vision capability kept? Five generated images with known answers.

The images are drawn with the standard library (zlib PNG), so every engine gets the same bytes.
A task passes when every expected keyword group has a match in the answer (case-insensitive).
"""

from __future__ import annotations

import base64
import re
import struct
import zlib
from dataclasses import dataclass

RGB = tuple[int, int, int]
WHITE: RGB = (255, 255, 255)
RED: RGB = (220, 30, 30)
BLUE: RGB = (30, 60, 220)
GREEN: RGB = (20, 160, 40)
ORANGE: RGB = (245, 140, 20)
GRAY: RGB = (150, 150, 150)
BLACK: RGB = (0, 0, 0)


class Canvas:
    """A small RGB raster with rectangles and filled circles."""

    def __init__(self, width: int, height: int, background: RGB = WHITE) -> None:
        self.width, self.height = width, height
        self.pixels = [[background] * width for _ in range(height)]

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: RGB) -> None:
        for y in range(max(0, y0), min(self.height, y1)):
            for x in range(max(0, x0), min(self.width, x1)):
                self.pixels[y][x] = color

    def circle(self, cx: int, cy: int, r: int, color: RGB) -> None:
        for y in range(max(0, cy - r), min(self.height, cy + r + 1)):
            for x in range(max(0, cx - r), min(self.width, cx + r + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.pixels[y][x] = color

    def png(self) -> bytes:
        """Encode as a PNG (8-bit RGB, no filter)."""
        raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in self.pixels)

        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
        )


@dataclass(frozen=True)
class VisionTask:
    """One image, one question, and keyword groups that must all match (any word of a group)."""

    task_id: str
    question: str
    expect: tuple[tuple[str, ...], ...]
    png: bytes

    @property
    def b64(self) -> str:
        return base64.b64encode(self.png).decode()


def _shapes() -> bytes:
    c = Canvas(320, 200)
    c.rect(30, 50, 130, 150, RED)
    c.circle(230, 100, 50, BLUE)
    return c.png()


def _count() -> bytes:
    c = Canvas(320, 200)
    for x in (60, 160, 260):
        c.circle(x, 100, 28, GREEN)
    return c.png()


def _bars() -> bytes:
    c = Canvas(320, 220)
    c.rect(20, 200, 300, 203, BLACK)
    for i, (h, color) in enumerate([(60, GRAY), (100, GRAY), (170, ORANGE), (80, GRAY)]):
        x = 40 + i * 65
        c.rect(x, 200 - h, x + 45, 200, color)
    return c.png()


def _flag() -> bytes:
    c = Canvas(300, 180)
    c.rect(0, 0, 100, 180, BLUE)
    c.rect(100, 0, 200, 180, WHITE)
    c.rect(200, 0, 300, 180, RED)
    return c.png()


def _position() -> bytes:
    c = Canvas(300, 300)
    c.rect(200, 20, 280, 100, GREEN)
    return c.png()


TASKS: tuple[VisionTask, ...] = (
    VisionTask(
        "shapes", "What color is the square, and what shape is on the right?", (("red",), ("circle",)), _shapes()
    ),
    VisionTask("count", "How many green circles are in the image? Answer with a number.", (("3", "three"),), _count()),
    VisionTask(
        "bars",
        "Which bar is the tallest (first, second, third or fourth), and what color is it?",
        (("third", "3rd", "3"), ("orange",)),
        _bars(),
    ),
    VisionTask(
        "flag",
        "List the three colors of the vertical stripes from left to right.",
        (("blue",), ("white",), ("red",)),
        _flag(),
    ),
    VisionTask(
        "position",
        "In which corner of the image is the green square? Answer like 'top left'.",
        (("top right", "upper right", "top-right", "upper-right"),),
        _position(),
    ),
)
TASK_BY_ID = {t.task_id: t for t in TASKS}


def check(task_id: str, answer: str) -> bool:
    """Return True when every keyword group of the task matches the answer."""
    text = answer.lower()
    return all(
        any(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text) for word in group)
        for group in TASK_BY_ID[task_id].expect
    )
