# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from linkedin_reply_assistant.backends.base import BackendError, ChatRequest, Health
from linkedin_reply_assistant.backends.manager import BackendManager, NoBackendError
from linkedin_reply_assistant.cancel import Cancelled, CancelToken
from tests.fakes import FakeBackend, make_config


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


UP = Health(True, "0.40", ("small:1", "eye:1"))
DOWN = Health(False, error="timeout after 700 ms")


def setup(
    net: Health, local: Health, net_answer: str | BackendError = "net"
) -> tuple[BackendManager, FakeBackend, FakeBackend, Clock]:
    clock = Clock()
    net_b = FakeBackend(make_config("net", 10), net, net_answer)
    local_b = FakeBackend(make_config("local", 20), local, "local")
    return BackendManager([local_b, net_b], 30, clock), net_b, local_b, clock


def test_network_first_with_installed_model() -> None:
    manager, net, local, _ = setup(UP, UP)
    result = manager.chat("reply", ChatRequest("s", "u"), CancelToken())
    assert (result.backend, result.model, result.text) == ("net", "small:1", "net")
    assert not result.fallback_used and result.label == "net label"
    assert result.endpoint == "http://net:11434"
    assert local.calls == []


def test_fallback_to_local_when_network_down() -> None:
    manager, _, _, _ = setup(DOWN, UP)
    result = manager.chat("vision", ChatRequest("s", "u"), CancelToken())
    assert result.backend == "local"
    assert result.fallback_reasons == ("net: timeout after 700 ms",)


def test_fallback_on_generation_failure_marks_down() -> None:
    manager, net, _, clock = setup(UP, UP, BackendError("unreachable", reachable=False))
    result = manager.chat("reply", ChatRequest("s", "u"), CancelToken())
    assert result.backend == "local" and "net: unreachable" in result.fallback_reasons[0]
    assert not manager.health(net).reachable
    clock.now += 31  # network node becomes eligible again after the cache period
    assert manager.health(net).reachable


def test_model_error_does_not_mark_down() -> None:
    manager, net, _, _ = setup(UP, UP, BackendError("bad answer"))
    manager.chat("reply", ChatRequest("s", "u"), CancelToken())
    assert manager.health(net).reachable


def test_health_is_cached() -> None:
    manager, net, _, clock = setup(UP, UP)
    manager.health(net)
    manager.health(net)
    assert net.probes == 1
    manager.health(net, refresh=True)
    assert net.probes == 2
    clock.now += 31
    manager.health_report()
    assert net.probes == 3


def test_missing_model_and_unconfigured_purpose() -> None:
    manager, net, local, _ = setup(Health(True, "1", ("other:1",)), UP)
    local.config = make_config("local", 20, vision_models=())
    with pytest.raises(NoBackendError) as info:
        manager.chat("vision", ChatRequest("s", "u"), CancelToken())
    assert info.value.reasons == (
        "net: none of ['eye:1'] installed",
        "local: no vision model configured",
    )


def test_no_backends() -> None:
    with pytest.raises(NoBackendError, match="no backend configured"):
        BackendManager([], 30).chat("reply", ChatRequest("s", "u"), CancelToken())


def test_cancel_before_call() -> None:
    manager, _, _, _ = setup(UP, UP)
    token = CancelToken()
    token.cancel()
    with pytest.raises(Cancelled):
        manager.chat("reply", ChatRequest("s", "u"), token)
