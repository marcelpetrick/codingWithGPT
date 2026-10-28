# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The grabber with GStreamer test sources instead of PipeWire (same sink, same code path)."""

import time

import pytest

from linkedin_reply_assistant.capture.pipewire import SINK, LatestFrameGrabber, pipewire_pipeline
from linkedin_reply_assistant.capture.source import CaptureError

LIVE = (
    "videotestsrc is-live=true pattern=red ! "
    f"video/x-raw,width=321,height=99,framerate=30/1 ! {SINK}"
)


def test_pipeline_string() -> None:
    assert pipewire_pipeline(5, 77).startswith("pipewiresrc fd=5 path=77 ")


def test_grabs_latest_frame_with_odd_width() -> None:
    grabber = LatestFrameGrabber(LIVE, "test")
    try:
        assert grabber.name == "test"
        image = grabber.grab()
        assert image.size == (321, 99)
        red = image.getpixel((10, 10))
        assert isinstance(red, tuple) and red[0] > 200
        assert grabber.is_ready()
    finally:
        grabber.close()


def test_end_of_stream_is_reported() -> None:
    grabber = LatestFrameGrabber(f"videotestsrc num-buffers=1 ! {SINK}", "eos")
    try:
        grabber.grab()
        deadline = time.monotonic() + 3
        while grabber.is_ready() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not grabber.is_ready()
        with pytest.raises(CaptureError, match="stream ended"):
            grabber.grab()
    finally:
        grabber.close()


def test_no_frame_times_out() -> None:
    grabber = LatestFrameGrabber(f"videotestsrc is-live=true ! valve drop=true ! {SINK}", "x")
    try:
        with pytest.raises(CaptureError, match="no frame"):
            grabber.grab(timeout=0.2)
    finally:
        grabber.close()


def test_stream_error_is_reported() -> None:
    grabber = LatestFrameGrabber(f"filesrc location=/nonexistent/x ! {SINK}", "err")
    try:
        with pytest.raises(CaptureError, match="stream error"):
            grabber.grab(timeout=1)
    finally:
        grabber.close()


def test_bad_pipelines() -> None:
    with pytest.raises(CaptureError, match="cannot build"):
        LatestFrameGrabber("no-such-element ! fakesink", "x")
    with pytest.raises(CaptureError, match="no appsink"):
        LatestFrameGrabber("videotestsrc ! fakesink", "x")
