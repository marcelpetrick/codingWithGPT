# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The portal Request/Response pattern: call a method, then wait for the Response signal."""

import asyncio
import secrets
from typing import Any

from dbus_fast import Message, MessageType, Variant
from dbus_fast.aio import MessageBus

from linkedin_reply_assistant.portal.bus import PORTAL_BUS, PORTAL_PATH, REQUEST, PortalError

RESPONSE_CANCELLED = 1


class PortalCancelled(PortalError):
    """The user closed or cancelled the portal dialog."""


def new_token() -> str:
    return "lra" + secrets.token_hex(6)


def unpack(results: dict[str, Variant]) -> dict[str, Any]:
    return {key: value.value for key, value in results.items()}


async def call(
    bus: MessageBus, interface: str, member: str, signature: str, body: list[Any]
) -> Message:
    """A plain method call on the portal object. Raises PortalError on a D-Bus error."""
    reply = await bus.call(
        Message(
            destination=PORTAL_BUS,
            path=PORTAL_PATH,
            interface=interface,
            member=member,
            signature=signature,
            body=body,
        )
    )
    if reply is None or reply.message_type == MessageType.ERROR:
        detail = f"{reply.error_name}: {reply.body}" if reply else "no reply"
        raise PortalError(f"{member} failed: {detail}")
    return reply


async def request(
    bus: MessageBus, interface: str, member: str, signature: str, body: list[Any]
) -> dict[str, Any]:
    """Call a portal method whose last argument is the options dict, and wait for its Response.

    A `handle_token` is added to the options. Response signals are collected by request path, so a
    signal that arrives before the method reply is not lost.
    """
    options: dict[str, Variant] = body[-1]
    options["handle_token"] = Variant("s", new_token())
    responses: dict[str, list[Any]] = {}
    arrived = asyncio.Event()

    def on_message(message: Message) -> None:
        if (
            message.message_type == MessageType.SIGNAL
            and message.interface == REQUEST
            and message.member == "Response"
        ):
            responses[str(message.path)] = message.body
            arrived.set()

    bus.add_message_handler(on_message)
    try:
        await _add_match(bus)
        reply = await call(bus, interface, member, signature, body)
        handle = str(reply.body[0])
        while handle not in responses:
            arrived.clear()
            await arrived.wait()
        code, results = responses[handle]
    finally:
        bus.remove_message_handler(on_message)
    if code == RESPONSE_CANCELLED:
        raise PortalCancelled(f"{member}: cancelled by the user")
    if code != 0:
        raise PortalError(f"{member}: the portal refused the request (code {code})")
    return unpack(results)


async def _add_match(bus: MessageBus) -> None:
    reply = await bus.call(
        Message(
            destination="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="AddMatch",
            signature="s",
            body=[f"type='signal',interface='{REQUEST}',member='Response'"],
        )
    )
    if reply is None or reply.message_type == MessageType.ERROR:  # pragma: no cover
        raise PortalError("cannot subscribe to portal responses")
