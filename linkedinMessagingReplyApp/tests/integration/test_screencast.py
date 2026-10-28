# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""ScreenCast portal flow against a fake portal on a private D-Bus."""

from collections.abc import Iterator

import pytest

from linkedin_reply_assistant.capture.pipewire import SINK
from linkedin_reply_assistant.capture.portal_source import PortalCaptureSource
from linkedin_reply_assistant.capture.source import CaptureError
from linkedin_reply_assistant.portal.bus import PortalError
from linkedin_reply_assistant.portal.request import PortalCancelled
from linkedin_reply_assistant.portal.runner import AsyncRunner
from tests.integration.fake_portal import FakePortal, FakeScreenCast, private_bus

PIPELINES: list[tuple[int, int]] = []


def test_pipeline(fd: int, target: int) -> str:
    PIPELINES.append((fd, target))
    return f"videotestsrc is-live=true ! video/x-raw,width=64,height=48 ! {SINK}"


test_pipeline.__test__ = False  # type: ignore[attr-defined]


@pytest.fixture
def portal() -> Iterator[tuple[str, FakeScreenCast, AsyncRunner]]:
    fakes: list[FakeScreenCast] = []

    def factory(bus: object) -> list[FakeScreenCast]:
        fakes.append(FakeScreenCast(bus))  # type: ignore[arg-type]
        return fakes

    runner = AsyncRunner()
    with private_bus() as address, FakePortal(address, factory):  # type: ignore[arg-type]
        yield address, fakes[0], runner
    runner.stop()


def test_select_grab_close_and_token_rotation(
    portal: tuple[str, FakeScreenCast, AsyncRunner],
) -> None:
    address, fake, runner = portal
    PIPELINES.clear()
    source = PortalCaptureSource(runner, address, test_pipeline)
    assert not source.is_ready() and source.name == "no source"
    with pytest.raises(CaptureError, match="no capture source"):
        source.grab()
    token = source.select(None)
    assert token == "token-1"
    assert source.name == "window 640x480" and source.is_ready()
    assert source.grab().size == (64, 48)
    assert PIPELINES[0][1] == 4242  # pipewire-serial preferred over node id
    members = [m for m, _ in fake.calls]
    assert members == ["CreateSession", "SelectSources", "Start"]
    select_options = fake.calls[1][1]
    assert select_options["persist_mode"] == 2 and select_options["cursor_mode"] == 1
    assert "restore_token" not in select_options
    source.close()
    assert len(fake.closed) == 1
    source.close()  # idempotent

    again = PortalCaptureSource(runner, address, test_pipeline)
    assert again.select(token) == "token-2"  # single-use: a new token replaces the old one
    assert fake.calls[-2][1]["restore_token"] == "token-1"
    again.close()


def test_node_id_used_without_serial(portal: tuple[str, FakeScreenCast, AsyncRunner]) -> None:
    address, fake, runner = portal
    fake.serial = False
    PIPELINES.clear()
    source = PortalCaptureSource(runner, address, test_pipeline)
    source.select(None)
    assert PIPELINES[0][1] == 77
    source.close()


def test_user_cancels_picker(portal: tuple[str, FakeScreenCast, AsyncRunner]) -> None:
    address, fake, runner = portal
    fake.response_code = 1
    with pytest.raises(PortalCancelled):
        PortalCaptureSource(runner, address, test_pipeline).select(None)


def test_portal_refuses(portal: tuple[str, FakeScreenCast, AsyncRunner]) -> None:
    address, fake, runner = portal
    fake.response_code = 2
    with pytest.raises(PortalError, match="refused"):
        PortalCaptureSource(runner, address, test_pipeline).select(None)


def test_no_streams_and_no_fd(portal: tuple[str, FakeScreenCast, AsyncRunner]) -> None:
    address, fake, runner = portal
    fake.no_streams = True
    with pytest.raises(PortalError, match="no stream"):
        PortalCaptureSource(runner, address, test_pipeline).select(None)
    fake.no_streams = False
    fake.no_fd = True
    with pytest.raises(PortalError, match="OpenPipeWireRemote failed"):
        PortalCaptureSource(runner, address, test_pipeline).select(None)


def test_bad_pipeline_closes_fd(portal: tuple[str, FakeScreenCast, AsyncRunner]) -> None:
    address, _, runner = portal
    source = PortalCaptureSource(runner, address, lambda fd, target: "nonsense-element")
    with pytest.raises(CaptureError):
        source.select(None)
