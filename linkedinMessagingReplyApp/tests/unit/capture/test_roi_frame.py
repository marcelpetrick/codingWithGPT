# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

import pytest
from PIL import Image

from linkedin_reply_assistant.capture.frame import Capture, png_bytes
from linkedin_reply_assistant.capture.roi import Roi
from linkedin_reply_assistant.capture.source import CaptureError, ImageFileSource


def test_roi_round_trip_and_resize_tolerance() -> None:
    roi = Roi.from_pixels(300, 50, 100, 250, (400, 300))  # corners in any order
    assert roi == Roi(0.25, 50 / 300, 0.5, 200 / 300)
    assert roi.to_pixels((400, 300)) == (100, 50, 300, 250)
    assert roi.to_pixels((800, 600)) == (200, 100, 600, 500)  # resized window
    assert Roi.from_dict(roi.to_dict()) == roi


def test_roi_clamps_pixels() -> None:
    assert Roi.from_pixels(-10, -10, 500, 500, (100, 100)) == Roi(0, 0, 1, 1)


@pytest.mark.parametrize(
    "values",
    [
        (-0.1, 0, 0.5, 0.5),
        (0, 0, 1.2, 0.5),
        (0, 0, 0.01, 0.5),
        (0.8, 0, 0.5, 0.5),
        (0, 0.9, 0.5, 0.5),
    ],
)
def test_roi_rejects_invalid(values: tuple[float, float, float, float]) -> None:
    with pytest.raises(ValueError):
        Roi(*values)


@pytest.mark.parametrize("data", [None, "x", {"x": 0}, {"x": "a", "y": 0, "width": 1, "height": 1}])
def test_roi_from_bad_dict(data: object) -> None:
    assert Roi.from_dict(data) is None


def test_roi_minimum_one_pixel() -> None:
    assert Roi(0.5, 0.5, 0.02, 0.02).to_pixels((10, 10)) == (5, 5, 6, 6)


def test_capture_crop_and_metadata() -> None:
    image = Image.new("RGB", (200, 100), "white")
    full = Capture(1, image, "test", None)
    assert full.cropped().size == (200, 100) and full.metadata()["crop"] is None
    cropped = Capture(2, image, "test", Roi(0.5, 0, 0.5, 1), timestamp=5.0)
    assert cropped.cropped().size == (100, 100)
    assert cropped.metadata() == {
        "sequence_id": 2,
        "timestamp": 5.0,
        "source": "test",
        "size": "200x100",
        "crop": {"x": 0.5, "y": 0, "width": 0.5, "height": 1},
    }
    assert png_bytes(image).startswith(b"\x89PNG")


def test_image_file_source(tmp_path: Path) -> None:
    path = tmp_path / "shot.png"
    source = ImageFileSource(path)
    assert not source.is_ready() and source.name == "file shot.png"
    with pytest.raises(CaptureError):
        source.grab()
    Image.new("L", (10, 10)).save(path)
    assert source.is_ready() and source.grab().mode == "RGB"
    source.close()
