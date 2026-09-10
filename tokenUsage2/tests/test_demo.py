# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

from conftest import BERLIN, NOW
from tokenusage2.demo import DemoSource


def test_demo_is_deterministic_and_keeps_ticking() -> None:
    moment = [NOW]

    def clock() -> float:
        return moment[0]

    first = DemoSource(BERLIN, clock=clock, days=10)
    second = DemoSource(BERLIN, clock=clock, days=10)
    assert [e.usage for e in first.events()] == [e.usage for e in second.events()]
    assert first.scan().events_changed == 0
    moment[0] += 5
    before = len(first.events())
    report = first.scan()
    assert len(first.events()) == before + report.events_changed
    assert {quota.window for quota in first.quotas()} == {"5h", "week"}
    assert first.running()
    assert not first.archived()
    assert "demo mode" in first.sources()[0]
    first.rediscover()
    assert any(e.usage.unsplit for e in DemoSource(BERLIN, clock=clock, days=80).events())
