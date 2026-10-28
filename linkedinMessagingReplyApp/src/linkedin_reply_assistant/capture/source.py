# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture sources. The application depends on this protocol only."""

from pathlib import Path
from typing import Protocol

from PIL import Image


class CaptureError(Exception):
    """The capture source is unavailable or gave no usable frame."""


class CaptureSource(Protocol):
    @property
    def name(self) -> str: ...

    def is_ready(self) -> bool: ...

    def grab(self) -> Image.Image: ...

    def close(self) -> None: ...


class ImageFileSource:
    """Read a still image from disk on every grab (CLI, Docker self-test, test harness)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def name(self) -> str:
        return f"file {self.path.name}"

    def is_ready(self) -> bool:
        return self.path.is_file()

    def grab(self) -> Image.Image:
        try:
            with Image.open(self.path) as image:
                return image.convert("RGB")
        except OSError as exc:
            raise CaptureError(f"cannot read {self.path}: {exc}") from exc

    def close(self) -> None:
        """Nothing to release."""
