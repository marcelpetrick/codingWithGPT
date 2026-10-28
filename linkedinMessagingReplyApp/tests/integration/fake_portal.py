# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A private D-Bus session bus with a fake org.freedesktop.portal.Desktop service.

The fake runs in its own thread and event loop, so the code under test talks to it over a real bus.
"""

import asyncio
import shutil
import subprocess
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from dbus_fast.aio import MessageBus
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property

from linkedin_reply_assistant.portal.bus import PORTAL_BUS, PORTAL_PATH


class VersionOnly(ServiceInterface):
    def __init__(self, name: str, version: int) -> None:
        super().__init__(name)
        self._version = version

    @dbus_property(access=PropertyAccess.READ)
    def version(self) -> "u":  # type: ignore[name-defined]
        return self._version


@contextmanager
def private_bus() -> Iterator[str]:
    """Start dbus-daemon on a private address and yield the address."""
    daemon = shutil.which("dbus-daemon")
    assert daemon, "dbus-daemon is required for portal integration tests"
    proc = subprocess.Popen(
        [daemon, "--session", "--nofork", "--print-address=1"],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    address = proc.stdout.readline().strip()
    try:
        yield address
    finally:
        proc.terminate()
        proc.wait(timeout=5)


class FakePortal:
    """Serve the given interfaces at the portal path on a private bus, in a thread."""

    def __init__(self, address: str, interfaces: Callable[[MessageBus], list[ServiceInterface]]):
        self.address = address
        self._factory = interfaces
        self.loop = asyncio.new_event_loop()
        self.bus: MessageBus | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start())
        self._ready.set()
        self.loop.run_forever()

    async def _start(self) -> None:
        self.bus = await MessageBus(bus_address=self.address).connect()
        for interface in self._factory(self.bus):
            self.bus.export(PORTAL_PATH, interface)
        await self.bus.request_name(PORTAL_BUS)

    def __enter__(self) -> FakePortal:
        self._thread.start()
        assert self._ready.wait(5), "fake portal did not start"
        return self

    def __exit__(self, *exc: object) -> None:
        if self.bus is not None:
            self.loop.call_soon_threadsafe(self.bus.disconnect)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(5)
