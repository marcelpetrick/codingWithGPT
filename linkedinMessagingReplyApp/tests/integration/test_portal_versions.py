# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio

from linkedin_reply_assistant.portal.bus import GLOBAL_SHORTCUTS, SCREENCAST, portal_versions
from tests.integration.fake_portal import FakePortal, VersionOnly, private_bus


def test_versions_from_fake_portal() -> None:
    with private_bus() as address, FakePortal(address, lambda bus: [VersionOnly(SCREENCAST, 5)]):
        versions = asyncio.run(portal_versions(address))
    assert versions == {SCREENCAST: 5, GLOBAL_SHORTCUTS: None}
