# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Low-overhead GStreamer stream that keeps only the latest frame (§6.3). No recording, no files."""

import threading
from typing import Any, cast

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
from PIL import Image  # noqa: E402

from linkedin_reply_assistant.capture.source import CaptureError  # noqa: E402

SINK = (
    "videoconvert ! video/x-raw,format=RGBx ! "
    "appsink name=sink emit-signals=true max-buffers=1 drop=true sync=false"
)


def pipewire_pipeline(fd: int, node: int) -> str:
    """Pipeline for a portal stream: the fd from OpenPipeWireRemote and the stream node id."""
    return f"pipewiresrc fd={fd} path={node} always-copy=true do-timestamp=true ! {SINK}"


class LatestFrameGrabber:
    """Run a pipeline that ends in SINK and keep the newest frame in memory."""

    def __init__(self, source_description: str, name: str) -> None:
        Gst.init(None)
        self._name = name
        self._lock = threading.Lock()
        self._latest: Image.Image | None = None
        self._first = threading.Event()
        self._error: str | None = None
        try:
            self._pipeline = cast(Any, Gst.parse_launch(source_description))  # a Gst.Pipeline
        except gi.repository.GLib.Error as exc:
            raise CaptureError(f"cannot build capture pipeline: {exc.message}") from exc
        sink: Any = self._pipeline.get_by_name("sink")
        if sink is None:
            raise CaptureError("capture pipeline has no appsink named 'sink'")
        sink.connect("new-sample", self._on_sample)
        self._pipeline.set_state(Gst.State.PLAYING)

    @property
    def name(self) -> str:
        return self._name

    def _on_sample(self, sink: Any) -> Gst.FlowReturn:
        sample = sink.emit("pull-sample")
        structure = sample.get_caps().get_structure(0)
        width = structure.get_value("width")
        height = structure.get_value("height")
        buffer = sample.get_buffer()
        ok, info = buffer.map(Gst.MapFlags.READ)
        if not ok:  # pragma: no cover - mapping a system-memory buffer does not fail
            return Gst.FlowReturn.OK
        try:
            stride = info.size // height
            data = bytes(info.data)
            image = Image.frombytes("RGB", (width, height), data, "raw", "RGBX", stride, 1)
        finally:
            buffer.unmap(info)
        with self._lock:
            self._latest = image
        self._first.set()
        return Gst.FlowReturn.OK

    def poll_bus(self) -> None:
        """Read pending bus messages (errors, end of stream). Needs no GLib main loop."""
        bus = self._pipeline.get_bus()
        while (message := bus.pop()) is not None:
            if message.type == Gst.MessageType.ERROR:
                error, _ = message.parse_error()
                self._error = f"stream error: {error.message}"
            elif message.type == Gst.MessageType.EOS:
                self._error = "stream ended (window closed or sharing stopped)"

    def is_ready(self) -> bool:
        self.poll_bus()
        return self._error is None

    def grab(self, timeout: float = 2.0) -> Image.Image:
        """Return the latest frame. Waits up to `timeout` for the first frame."""
        self.poll_bus()
        if not self._first.wait(timeout):
            self.poll_bus()
            raise CaptureError(self._error or "no frame received from the capture stream")
        if self._error is not None:
            raise CaptureError(self._error)
        with self._lock:
            assert self._latest is not None
            return self._latest.copy()

    def close(self) -> None:
        self._pipeline.set_state(Gst.State.NULL)
