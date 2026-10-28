# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import base64
import json
from collections.abc import Callable

import httpx
import pytest

from linkedin_reply_assistant.backends.base import BackendError, ChatRequest
from linkedin_reply_assistant.backends.ollama import OllamaBackend
from linkedin_reply_assistant.cancel import Cancelled, CancelToken
from linkedin_reply_assistant.config.loader import BackendConfig

Handler = Callable[[httpx.Request], httpx.Response]


def backend(config: BackendConfig, handler: Handler) -> OllamaBackend:
    return OllamaBackend(config, transport=httpx.MockTransport(handler))


def stream(*chunks: dict[str, object]) -> bytes:
    return b"\n".join(json.dumps(c).encode() for c in chunks) + b"\n"


def test_health_ok(config: BackendConfig) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.11"})
        return httpx.Response(200, json={"models": [{"name": "big:1"}, {"name": "eye:1"}]})

    health = backend(config, handler).health()
    assert health.reachable and health.version == "0.40.11"
    assert health.models == ("big:1", "eye:1")


@pytest.mark.parametrize(
    ("exc", "message"),
    [
        (httpx.ConnectTimeout("t"), "timeout after 100 ms"),
        (httpx.ConnectError("c"), "unreachable: ConnectError"),
    ],
)
def test_health_down(config: BackendConfig, exc: Exception, message: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    health = backend(config, handler).health()
    assert not health.reachable and health.error == message


def test_health_bad_status_and_bad_json(config: BackendConfig) -> None:
    assert not backend(config, lambda r: httpx.Response(500)).health().reachable
    bad = backend(config, lambda r: httpx.Response(200, content=b"not json")).health()
    assert bad.error == "invalid answer from endpoint"


def test_chat_streams_and_sends_images(config: BackendConfig) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        body = stream(
            {"message": {"content": '{"reply":'}},
            {},
            {"message": {"content": ' "hi"}'}, "done": True},
            {"message": {"content": "ignored"}},
        )
        return httpx.Response(200, content=body)

    client = backend(config, handler)
    text = client.chat("big:1", ChatRequest("sys", "user", images=(b"png",)), CancelToken())
    assert text == '{"reply": "hi"}'
    assert seen["model"] == "big:1" and seen["format"] == "json" and seen["think"] is False
    messages = seen["messages"]
    assert isinstance(messages, list)
    assert messages[1]["images"] == [base64.b64encode(b"png").decode()]
    client.close()


def test_chat_without_json_format(config: BackendConfig) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, content=stream({"message": {"content": "x"}, "done": True}))

    backend(config, handler).chat("m", ChatRequest("s", "u", json_output=False), CancelToken())
    assert "format" not in seen


def test_chat_cancel(config: BackendConfig) -> None:
    token = CancelToken()
    token.cancel()
    body = stream({"message": {"content": "x"}, "done": True})
    client = backend(config, lambda r: httpx.Response(200, content=body))
    with pytest.raises(Cancelled):
        client.chat("m", ChatRequest("s", "u"), token)


@pytest.mark.parametrize(
    ("response", "message", "reachable"),
    [
        (httpx.Response(404, text="model not found"), "HTTP 404: model not found", True),
        (httpx.Response(200, content=stream({"error": "boom"})), "boom", True),
        (httpx.Response(200, content=b"{bad\n"), "invalid stream", True),
        (
            httpx.Response(200, content=stream({"message": {"content": " "}, "done": True})),
            "empty",
            True,
        ),
    ],
)
def test_chat_errors(
    config: BackendConfig, response: httpx.Response, message: str, reachable: bool
) -> None:
    with pytest.raises(BackendError, match=message) as info:
        backend(config, lambda r: response).chat("m", ChatRequest("s", "u"), CancelToken())
    assert info.value.reachable is reachable


@pytest.mark.parametrize(
    ("exc", "message", "reachable"),
    [
        (httpx.ConnectError("x"), "unreachable", False),
        (httpx.ReadTimeout("x"), "generation timeout", True),
        (httpx.RemoteProtocolError("x"), "transport error", False),
    ],
)
def test_chat_transport_errors(
    config: BackendConfig, exc: Exception, message: str, reachable: bool
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    with pytest.raises(BackendError, match=message) as info:
        backend(config, handler).chat("m", ChatRequest("s", "u"), CancelToken())
    assert info.value.reachable is reachable


def test_chat_skips_blank_lines_and_ends_without_done(config: BackendConfig) -> None:
    body = b'\n{"message": {"content": "a"}}\n\n{"message": {"content": "b"}}\n'
    client = backend(config, lambda r: httpx.Response(200, content=body))
    assert client.chat("m", ChatRequest("s", "u"), CancelToken()) == "ab"
