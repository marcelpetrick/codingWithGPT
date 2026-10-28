# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""GlobalShortcuts portal flow against a fake portal on a private D-Bus."""

import threading
from collections.abc import Iterator

import pytest
from dbus_fast import Variant

from linkedin_reply_assistant.portal.runner import AsyncRunner
from linkedin_reply_assistant.shortcuts.portal_global_shortcuts import (
    APP_ID,
    PortalGlobalShortcuts,
)
from tests.integration.fake_portal import (
    FakeGlobalShortcuts,
    FakePortal,
    FakeRegistry,
    VersionOnly,
    private_bus,
)

Env = tuple[str, FakeGlobalShortcuts, FakeRegistry, FakePortal, AsyncRunner]


@pytest.fixture
def env() -> Iterator[Env]:
    made: dict[str, object] = {}

    def factory(bus: object) -> list[object]:
        made["gs"] = FakeGlobalShortcuts(bus)  # type: ignore[arg-type]
        made["reg"] = FakeRegistry()
        return [made["gs"], made["reg"]]

    runner = AsyncRunner()
    with private_bus() as address, FakePortal(address, factory) as portal:  # type: ignore[arg-type]
        yield address, made["gs"], made["reg"], portal, runner  # type: ignore[misc]
    runner.stop()


def test_start_bind_activate_rebind_close(env: Env) -> None:
    address, fake, registry, portal, runner = env
    hits: list[str] = []
    activated = threading.Event()

    def on_activated(shortcut_id: str) -> None:
        hits.append(shortcut_id)
        activated.set()

    service = PortalGlobalShortcuts(runner, address)
    status = service.start(on_activated)
    assert status.available and not status.active
    assert status.message == "Global hotkey not configured"
    assert registry.app_ids == [APP_ID]

    bound = service.bind("capture-and-draft", "Capture & Draft", "ctrl+alt+l")
    assert bound.active and bound.binding is not None
    assert bound.binding.trigger == "Ctrl+Alt+L"  # what the desktop reports is shown
    args = [c for c in fake.calls if c[0] == "BindShortcuts-args"][0][1]
    shortcuts = args["shortcuts"]
    assert isinstance(shortcuts, list)
    assert shortcuts[0][1]["preferred_trigger"].value == "CTRL+ALT+L"

    session = str(args["session"])
    portal.loop.call_soon_threadsafe(fake.Activated, session, "capture-and-draft", 1, {})
    portal.loop.call_soon_threadsafe(fake.Activated, "/other/session", "capture-and-draft", 1, {})
    assert activated.wait(3)
    assert hits == ["capture-and-draft"]

    fake.assign = None
    refused = service.bind("capture-and-draft", "Capture & Draft", "CTRL+ALT+K")
    assert not refused.active and "did not assign" in refused.message
    assert len(fake.closed) == 1  # rebind used a new session

    assert service.configure() is True and fake.configured == 1
    service.close()
    assert len(fake.closed) == 2


def test_remembered_binding_is_reported(env: Env) -> None:
    address, fake, _, _, runner = env
    fake.remembered = [
        [
            "capture-and-draft",
            {"description": Variant("s", "x"), "trigger_description": Variant("s", "Meta+L")},
        ]
    ]
    status = PortalGlobalShortcuts(runner, address).start(lambda s: None)
    assert status.active and status.message == "Global hotkey: Meta+L"


def test_guardrail_blocks_request(env: Env) -> None:
    address, fake, _, _, runner = env
    service = PortalGlobalShortcuts(runner, address)
    service.start(lambda s: None)
    status = service.bind("capture-and-draft", "Capture & Draft", "ALT+F4")
    assert "Not requested" in status.message
    assert not [c for c in fake.calls if c[0] == "BindShortcuts"]


def test_user_rejects_binding(env: Env) -> None:
    address, fake, _, _, runner = env
    service = PortalGlobalShortcuts(runner, address)
    service.start(lambda s: None)
    fake.response_code = 1
    status = service.bind("capture-and-draft", "Capture & Draft", "CTRL+ALT+L")
    assert not status.active and "cancelled" in status.message


def test_old_portal_without_configure(env: Env) -> None:
    address, _, _, _, runner = env
    service = PortalGlobalShortcuts(runner, address)
    service.start(lambda s: None)
    service.version = 1
    assert service.configure() is False


def test_configure_failure(env: Env) -> None:
    address, fake, _, _, runner = env
    service = PortalGlobalShortcuts(runner, address)
    service.start(lambda s: None)
    fake.fail_configure = True
    assert service.configure() is False
    service.close()


def test_portal_missing() -> None:
    runner = AsyncRunner()
    with private_bus() as address, FakePortal(address, lambda bus: [VersionOnly("x.y", 1)]):
        status = PortalGlobalShortcuts(runner, address).start(lambda s: None)
    runner.stop()
    assert not status.available and "unavailable" in status.message


def test_close_without_start() -> None:
    runner = AsyncRunner()
    PortalGlobalShortcuts(runner, "unix:path=/nonexistent").close()
    runner.stop()
