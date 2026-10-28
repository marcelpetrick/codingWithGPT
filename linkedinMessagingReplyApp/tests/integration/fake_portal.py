# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A private D-Bus session bus with a fake org.freedesktop.portal.Desktop service.

The fake runs in its own thread and event loop, so the code under test talks to it over a real bus.
"""

import asyncio
import os
import shutil
import subprocess
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from dbus_fast import DBusError, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property, method, signal

from linkedin_reply_assistant.portal.bus import PORTAL_BUS, PORTAL_PATH


class VersionOnly(ServiceInterface):
    def __init__(self, name: str, version: int) -> None:
        super().__init__(name)
        self._version = version

    @dbus_property(access=PropertyAccess.READ)
    def version(self) -> "u":
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
        self.bus = await MessageBus(bus_address=self.address, negotiate_unix_fd=True).connect()
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


class FakeRequest(ServiceInterface):
    def __init__(self) -> None:
        super().__init__("org.freedesktop.portal.Request")

    @signal()
    def Response(self, code: int, results: dict[str, Variant]) -> "ua{sv}":
        return [code, results]


class FakeSession(ServiceInterface):
    def __init__(self, on_close: Callable[[], None]) -> None:
        super().__init__("org.freedesktop.portal.Session")
        self._on_close = on_close

    @method()
    def Close(self) -> None:
        self._on_close()


class PortalBase(ServiceInterface):
    """Shared Request/Response machinery for fake portal interfaces."""

    def __init__(self, name: str, bus: MessageBus, version: int) -> None:
        super().__init__(name)
        self.bus = bus
        self._version = version
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.response_code = 0
        self.closed: list[str] = []
        self._counter = 0

    @dbus_property(access=PropertyAccess.READ)
    def version(self) -> "u":
        return self._version

    def respond(self, member: str, options: dict[str, Variant], results: dict[str, Variant]) -> str:
        self.calls.append((member, {k: v.value for k, v in options.items()}))
        token = options["handle_token"].value
        path = f"/org/freedesktop/portal/desktop/request/fake/{token}"
        req = FakeRequest()
        self.bus.export(path, req)
        code = self.response_code
        asyncio.get_running_loop().call_soon(req.Response, code, results)
        return path

    def new_session(self, options: dict[str, Variant]) -> str:
        self._counter += 1
        token = options.get("session_handle_token", Variant("s", f"s{self._counter}")).value
        path = f"/org/freedesktop/portal/desktop/session/fake/{token}"
        self.bus.export(path, FakeSession(lambda: self.closed.append(path)))
        return path


class FakeScreenCast(PortalBase):
    def __init__(self, bus: MessageBus, version: int = 5, serial: bool = True) -> None:
        super().__init__("org.freedesktop.portal.ScreenCast", bus, version)
        self.serial = serial
        self.restore_counter = 0
        self.no_streams = False
        self.no_fd = False

    @method()
    def CreateSession(self, options: "a{sv}") -> "o":
        session = self.new_session(options)
        return self.respond("CreateSession", options, {"session_handle": Variant("s", session)})

    @method()
    def SelectSources(self, session: "o", options: "a{sv}") -> "o":
        return self.respond("SelectSources", options, {})

    @method()
    def Start(self, session: "o", parent: "s", options: "a{sv}") -> "o":
        self.restore_counter += 1
        props = {"source_type": Variant("u", 2), "size": Variant("(ii)", [640, 480])}
        if self.serial:
            props["pipewire-serial"] = Variant("t", 4242)
        streams = [] if self.no_streams else [[77, props]]
        results = {
            "streams": Variant("a(ua{sv})", streams),
            "restore_token": Variant("s", f"token-{self.restore_counter}"),
        }
        return self.respond("Start", options, results)

    @method()
    def OpenPipeWireRemote(self, session: "o", options: "a{sv}") -> "h":
        if self.no_fd:
            raise DBusError("org.freedesktop.portal.Error.Failed", "no remote")
        read_end, write_end = os.pipe()
        os.close(write_end)
        return read_end


class FakeGlobalShortcuts(PortalBase):
    def __init__(self, bus: MessageBus, version: int = 2) -> None:
        super().__init__("org.freedesktop.portal.GlobalShortcuts", bus, version)
        self.remembered: list[list[object]] = []
        self.assign: str | None = "Ctrl+Alt+L"  # None = desktop refuses to assign
        self.configured = 0
        self.fail_configure = False

    def _shortcuts(self, entries: list[list[object]]) -> Variant:
        return Variant("a(sa{sv})", entries)

    @method()
    def CreateSession(self, options: "a{sv}") -> "o":
        session = self.new_session(options)
        return self.respond("CreateSession", options, {"session_handle": Variant("s", session)})

    @method()
    def ListShortcuts(self, session: "o", options: "a{sv}") -> "o":
        return self.respond(
            "ListShortcuts", options, {"shortcuts": self._shortcuts(self.remembered)}
        )

    @method()
    def BindShortcuts(
        self, session: "o", shortcuts: "a(sa{sv})", parent: "s", options: "a{sv}"
    ) -> "o":
        self.calls.append(("BindShortcuts-args", {"session": session, "shortcuts": shortcuts}))
        result = []
        for shortcut_id, props in shortcuts:
            out = {"description": props["description"]}
            if self.assign is not None:
                out["trigger_description"] = Variant("s", self.assign)
            result.append([shortcut_id, out])
        self.remembered = result
        return self.respond("BindShortcuts", options, {"shortcuts": self._shortcuts(result)})

    @method()
    def ConfigureShortcuts(self, session: "o", parent: "s", options: "a{sv}") -> None:
        if self.fail_configure:
            raise DBusError("org.freedesktop.portal.Error.Failed", "no settings")
        self.configured += 1

    @signal()
    def Activated(
        self, session: "o", shortcut_id: "s", timestamp: "t", options: "a{sv}"
    ) -> "osta{sv}":
        return [session, shortcut_id, timestamp, options]


class FakeRegistry(ServiceInterface):
    def __init__(self) -> None:
        super().__init__("org.freedesktop.host.portal.Registry")
        self.app_ids: list[str] = []

    @method()
    def Register(self, app_id: "s", options: "a{sv}") -> None:
        self.app_ids.append(app_id)
