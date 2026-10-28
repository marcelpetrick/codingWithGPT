# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""GlobalShortcuts portal client (§7.2).

The app only proposes a trigger. The desktop approves, changes or rejects it, and the trigger it
reports back is the truth. The app never edits OS shortcut configuration.
"""

from collections.abc import Callable
from typing import Any

from dbus_fast import Message, MessageType, Variant
from dbus_fast.aio import MessageBus

from linkedin_reply_assistant.portal.bus import (
    GLOBAL_SHORTCUTS,
    PORTAL_BUS,
    PORTAL_PATH,
    PortalError,
    connect,
    get_property,
)
from linkedin_reply_assistant.portal.request import call, new_token, request
from linkedin_reply_assistant.portal.runner import AsyncRunner
from linkedin_reply_assistant.shortcuts.base import UNAVAILABLE, Binding, ShortcutStatus
from linkedin_reply_assistant.shortcuts.guardrails import check_trigger, normalize

APP_ID = "io.github.marcelpetrick.LinkedInReplyAssistant"
REGISTRY = "org.freedesktop.host.portal.Registry"


def parse_bindings(raw: list[Any]) -> list[Binding]:
    bindings = []
    for shortcut_id, props in raw:
        values = {k: v.value for k, v in props.items()}
        bindings.append(
            Binding(
                str(shortcut_id),
                str(values.get("description", "")),
                str(values.get("trigger_description", "")),
            )
        )
    return bindings


class PortalGlobalShortcuts:
    def __init__(self, runner: AsyncRunner, bus_address: str | None = None) -> None:
        self._runner = runner
        self._address = bus_address
        self._bus: MessageBus | None = None
        self._session: str | None = None
        self._on_activated: Callable[[str], None] = lambda shortcut_id: None
        self._bound = False
        self.version = 0

    # --- async parts, run on the portal loop -------------------------------------------------

    async def _start(self) -> list[Binding]:
        bus = await connect(self._address)
        self._bus = bus
        self.version = int(await get_property(bus, GLOBAL_SHORTCUTS, "version") or 0)
        if not self.version:
            raise PortalError("GlobalShortcuts portal missing")
        await self._register_app_id(bus)
        await self._new_session(bus)
        bus.add_message_handler(self._on_message)
        await bus.call(
            Message(
                destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus",
                member="AddMatch",
                signature="s",
                body=[f"type='signal',interface='{GLOBAL_SHORTCUTS}',member='Activated'"],
            )
        )
        body: list[object] = [self._session, {}]
        listed = await request(bus, GLOBAL_SHORTCUTS, "ListShortcuts", "oa{sv}", body)
        return parse_bindings(listed.get("shortcuts") or [])

    async def _new_session(self, bus: MessageBus) -> None:
        options = {"session_handle_token": Variant("s", new_token())}
        results = await request(bus, GLOBAL_SHORTCUTS, "CreateSession", "a{sv}", [options])
        self._session = str(results["session_handle"])
        self._bound = False

    async def _close_session(self, bus: MessageBus) -> None:
        if self._session is not None:
            await bus.call(
                Message(
                    destination=PORTAL_BUS,
                    path=self._session,
                    interface="org.freedesktop.portal.Session",
                    member="Close",
                )
            )
            self._session = None

    @staticmethod
    async def _register_app_id(bus: MessageBus) -> None:
        """Host apps tell the portal their app id (xdg-desktop-portal >= 1.19). Optional."""
        await bus.call(
            Message(
                destination=PORTAL_BUS,
                path=PORTAL_PATH,
                interface=REGISTRY,
                member="Register",
                signature="sa{sv}",
                body=[APP_ID, {}],
            )
        )

    def _on_message(self, message: Message) -> None:
        if (
            message.message_type == MessageType.SIGNAL
            and message.interface == GLOBAL_SHORTCUTS
            and message.member == "Activated"
            and str(message.body[0]) == self._session
        ):
            self._on_activated(str(message.body[1]))

    async def _bind(self, shortcut_id: str, description: str, preferred: str) -> list[Binding]:
        assert self._bus is not None and self._session is not None
        if self._bound:  # a session binds once; a change needs a new session (§7.2 step 7)
            await self._close_session(self._bus)
            await self._new_session(self._bus)
        self._bound = True
        props = {
            "description": Variant("s", description),
            "preferred_trigger": Variant("s", preferred),
        }
        results = await request(
            self._bus,
            GLOBAL_SHORTCUTS,
            "BindShortcuts",
            "oa(sa{sv})sa{sv}",
            [self._session, [[shortcut_id, props]], "", {}],
        )
        return parse_bindings(results.get("shortcuts") or [])

    async def _configure(self) -> None:
        assert self._bus is not None and self._session is not None
        body = [self._session, "", {}]
        await call(self._bus, GLOBAL_SHORTCUTS, "ConfigureShortcuts", "osa{sv}", body)

    async def _close(self) -> None:
        if self._bus is None:
            return
        await self._close_session(self._bus)
        self._bus.disconnect()
        self._bus = None

    # --- blocking API for worker threads ------------------------------------------------------

    def start(self, on_activated: Callable[[str], None]) -> ShortcutStatus:
        """Open a session and report a remembered binding. Never binds by itself."""
        self._on_activated = on_activated
        try:
            existing = self._runner.run(self._start(), timeout=10)
        except (PortalError, TimeoutError, OSError) as exc:
            return ShortcutStatus(False, None, f"{UNAVAILABLE} ({exc})")
        binding = next((b for b in existing if b.trigger), None)
        if binding:
            return ShortcutStatus(True, binding, f"Global hotkey: {binding.trigger}")
        return ShortcutStatus(True, None, "Global hotkey not configured")

    def bind(self, shortcut_id: str, description: str, preferred: str) -> ShortcutStatus:
        """Propose `preferred`. The desktop decides; its answer is shown as is."""
        reason = check_trigger(preferred)
        if reason:
            return ShortcutStatus(True, None, f"Not requested: {reason}")
        try:
            bindings = self._runner.run(self._bind(shortcut_id, description, normalize(preferred)))
        except PortalError as exc:
            return ShortcutStatus(True, None, f"Global hotkey not bound: {exc}")
        binding = next((b for b in bindings if b.shortcut_id == shortcut_id), None)
        if binding is None or not binding.trigger:
            return ShortcutStatus(True, None, "The desktop did not assign a hotkey")
        return ShortcutStatus(True, binding, f"Global hotkey: {binding.trigger}")

    def configure(self) -> bool:
        """Open the desktop's own shortcut settings (portal version 2). False if not supported."""
        if self.version < 2:
            return False
        try:
            self._runner.run(self._configure(), timeout=10)
        except PortalError:
            return False
        return True

    def close(self) -> None:
        self._runner.run(self._close(), timeout=5)
