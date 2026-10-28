# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture source: ScreenCast portal session + PipeWire stream + latest-frame grabber."""

import os
from collections.abc import Callable

from dbus_fast.aio import MessageBus
from PIL import Image

from linkedin_reply_assistant.capture.pipewire import LatestFrameGrabber, pipewire_pipeline
from linkedin_reply_assistant.capture.source import CaptureError
from linkedin_reply_assistant.portal import screencast
from linkedin_reply_assistant.portal.bus import SCREENCAST, connect, get_property
from linkedin_reply_assistant.portal.runner import AsyncRunner

PipelineFactory = Callable[[int, int], str]


class PortalCaptureSource:
    """Created by `select()`. Must not be used from the GUI thread (portal dialogs block)."""

    def __init__(
        self,
        runner: AsyncRunner,
        bus_address: str | None = None,
        pipeline: PipelineFactory = pipewire_pipeline,
    ) -> None:
        self._runner = runner
        self._address = bus_address
        self._pipeline = pipeline
        self._bus: MessageBus | None = None
        self._session: str | None = None
        self._grabber: LatestFrameGrabber | None = None
        self._name = "no source"

    @property
    def name(self) -> str:
        return self._name

    async def _open(self, restore_token: str | None) -> tuple[screencast.StreamInfo, int]:
        bus = await connect(self._address, unix_fds=True)
        self._bus = bus
        version = await get_property(bus, SCREENCAST, "version") or 1
        self._session = await screencast.create_session(bus)
        await screencast.select_sources(bus, self._session, restore_token, int(version))
        info = await screencast.start(bus, self._session)
        fd = await screencast.open_pipewire_remote(bus, self._session)
        return info, fd

    def select(self, restore_token: str | None) -> str | None:
        """Open the portal (picker dialog unless the token restores it). Returns the new token."""
        info, fd = self._runner.run(self._open(restore_token))
        target = info.serial if info.serial is not None else info.node_id
        size = f" {info.size[0]}x{info.size[1]}" if info.size else ""
        kind = {1: "screen", 2: "window"}.get(info.source_type or 0, "source")
        try:
            self._grabber = LatestFrameGrabber(self._pipeline(fd, target), f"{kind}{size}")
        except CaptureError:
            os.close(fd)
            raise
        self._name = self._grabber.name
        return info.restore_token

    def is_ready(self) -> bool:
        return self._grabber is not None and self._grabber.is_ready()

    def grab(self) -> Image.Image:
        if self._grabber is None:
            raise CaptureError("no capture source selected")
        return self._grabber.grab()

    def close(self) -> None:
        if self._grabber is not None:
            self._grabber.close()
            self._grabber = None
        bus, session = self._bus, self._session
        self._bus = self._session = None
        if bus is not None:
            self._runner.run(self._close(bus, session), timeout=5)

    @staticmethod
    async def _close(bus: MessageBus, session: str | None) -> None:
        if session is not None:
            await screencast.close_session(bus, session)
        bus.disconnect()
