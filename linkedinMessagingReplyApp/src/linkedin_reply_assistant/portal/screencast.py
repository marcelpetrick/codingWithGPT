# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""ScreenCast portal client (§6): the user picks the browser window, we get a PipeWire stream.

Restore tokens are single-use: every successful Start returns a new token that replaces the old one.
"""

from dataclasses import dataclass
from typing import Any

from dbus_fast import Message, Variant
from dbus_fast.aio import MessageBus

from linkedin_reply_assistant.portal.bus import PORTAL_BUS, SCREENCAST, SESSION, PortalError
from linkedin_reply_assistant.portal.request import call, new_token, request

SOURCE_MONITOR = 1
SOURCE_WINDOW = 2
CURSOR_HIDDEN = 1
PERSIST_UNTIL_REVOKED = 2


@dataclass(frozen=True)
class StreamInfo:
    node_id: int
    serial: int | None
    source_type: int | None
    size: tuple[int, int] | None
    restore_token: str | None


async def create_session(bus: MessageBus) -> str:
    options = {"session_handle_token": Variant("s", new_token())}
    results = await request(bus, SCREENCAST, "CreateSession", "a{sv}", [options])
    return str(results["session_handle"])


async def select_sources(
    bus: MessageBus, session: str, restore_token: str | None, version: int
) -> None:
    options: dict[str, Variant] = {
        "types": Variant("u", SOURCE_WINDOW | SOURCE_MONITOR),
        "multiple": Variant("b", False),
    }
    if version >= 2:
        options["cursor_mode"] = Variant("u", CURSOR_HIDDEN)
    if version >= 4:
        options["persist_mode"] = Variant("u", PERSIST_UNTIL_REVOKED)
        if restore_token:
            options["restore_token"] = Variant("s", restore_token)
    await request(bus, SCREENCAST, "SelectSources", "oa{sv}", [session, options])


async def start(bus: MessageBus, session: str) -> StreamInfo:
    results = await request(bus, SCREENCAST, "Start", "osa{sv}", [session, "", {}])
    streams: list[Any] = results.get("streams") or []
    if not streams:
        raise PortalError("the portal returned no stream")
    node_id, props = streams[0]
    values = {key: value.value for key, value in props.items()}
    size = values.get("size")
    return StreamInfo(
        node_id=int(node_id),
        serial=int(values["pipewire-serial"]) if "pipewire-serial" in values else None,
        source_type=values.get("source_type"),
        size=(int(size[0]), int(size[1])) if size else None,
        restore_token=results.get("restore_token"),
    )


async def open_pipewire_remote(bus: MessageBus, session: str) -> int:
    reply = await call(bus, SCREENCAST, "OpenPipeWireRemote", "oa{sv}", [session, {}])
    if not reply.unix_fds:
        raise PortalError("the portal returned no PipeWire file descriptor")
    return int(reply.unix_fds[reply.body[0]])


async def close_session(bus: MessageBus, session: str) -> None:
    await bus.call(Message(destination=PORTAL_BUS, path=session, interface=SESSION, member="Close"))
