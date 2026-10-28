# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Region of interest in normalized coordinates (0..1), tolerant to window resizing (§6.4)."""

from dataclasses import dataclass

from PIL import Image

MIN_SIZE = 0.02


@dataclass(frozen=True)
class Roi:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if any(v < 0 or v > 1 for v in values):
            raise ValueError("ROI values must be between 0 and 1")
        if self.width < MIN_SIZE or self.height < MIN_SIZE:
            raise ValueError("ROI is too small")
        if self.x + self.width > 1.0001 or self.y + self.height > 1.0001:
            raise ValueError("ROI exceeds the image")

    @classmethod
    def from_pixels(
        cls, left: int, top: int, right: int, bottom: int, size: tuple[int, int]
    ) -> Roi:
        """Build a ROI from a pixel rectangle (any corner order) on an image of `size`."""
        width, height = size
        x0, x1 = sorted((max(0, min(left, width)), max(0, min(right, width))))
        y0, y1 = sorted((max(0, min(top, height)), max(0, min(bottom, height))))
        return cls(x0 / width, y0 / height, (x1 - x0) / width, (y1 - y0) / height)

    def to_pixels(self, size: tuple[int, int]) -> tuple[int, int, int, int]:
        width, height = size
        left = round(self.x * width)
        top = round(self.y * height)
        right = min(width, max(left + 1, round((self.x + self.width) * width)))
        bottom = min(height, max(top + 1, round((self.y + self.height) * height)))
        return left, top, right, bottom

    def crop(self, image: Image.Image) -> Image.Image:
        return image.crop(self.to_pixels(image.size))

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, data: object) -> Roi | None:
        """Parse a stored ROI. Invalid data gives None (the user selects the region again)."""
        if not isinstance(data, dict):
            return None
        try:
            return cls(*(float(data[k]) for k in ("x", "y", "width", "height")))
        except KeyError, TypeError, ValueError:
            return None
