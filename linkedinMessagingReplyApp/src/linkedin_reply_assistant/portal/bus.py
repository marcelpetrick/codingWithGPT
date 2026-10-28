# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Portal constants and small D-Bus helpers shared by all portal clients."""

from typing import Any

from dbus_fast import Message, MessageType
from dbus_fast.aio import MessageBus

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST = "org.freedesktop.portal.ScreenCast"
GLOBAL_SHORTCUTS = "org.freedesktop.portal.GlobalShortcuts"
REQUEST = "org.freedesktop.portal.Request"
SESSION = "org.freedesktop.portal.Session"
PROPERTIES = "org.freedesktop.DBus.Properties"


class PortalError(Exception):
    """A portal call failed or the user cancelled the portal dialog."""


async def connect(address: str | None = None, *, unix_fds: bool = False) -> MessageBus:
    """Connect to the session bus (or to `address`, used by tests with a private bus)."""
    return await MessageBus(bus_address=address, negotiate_unix_fd=unix_fds).connect()


async def get_property(bus: MessageBus, interface: str, name: str) -> Any:
    """Read one portal property. Returns None if the interface or property does not exist."""
    reply = await bus.call(
        Message(
            destination=PORTAL_BUS,
            path=PORTAL_PATH,
            interface=PROPERTIES,
            member="Get",
            signature="ss",
            body=[interface, name],
        )
    )
    if reply is None or reply.message_type != MessageType.METHOD_RETURN:
        return None
    return reply.body[0].value


async def portal_versions(address: str | None = None) -> dict[str, int | None]:
    """Return the version of the ScreenCast and GlobalShortcuts portals (None = missing)."""
    bus = await connect(address)
    try:
        return {
            iface: await get_property(bus, iface, "version")
            for iface in (SCREENCAST, GLOBAL_SHORTCUTS)
        }
    finally:
        bus.disconnect()
