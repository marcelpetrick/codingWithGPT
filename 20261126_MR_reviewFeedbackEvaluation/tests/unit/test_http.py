# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for retry, backoff and redaction (REQ-COL-6)."""

from collections.abc import Mapping

import pytest

from mrreview import http
from mrreview.http import HttpError, Response, TransportError


class Scripted:
    def __init__(self, items: list[Response | Exception]) -> None:
        self.items = items
        self.calls = 0

    def request(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float
    ) -> Response:
        item = self.items[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def run(items: list[Response | Exception], retries: int = 3) -> tuple[Response, list[float]]:
    waits: list[float] = []
    resp = http.request_with_retry(
        Scripted(items), "GET", "http://x/y?private_token=abc", {}, timeout=1,
        max_retries=retries, backoff_base=0.5, sleep=waits.append,
    )
    return resp, waits


def test_success_first_time() -> None:
    resp, waits = run([Response(200, {}, b"ok")])
    assert resp.body == b"ok"
    assert waits == []


def test_backoff_on_5xx_and_transport_error() -> None:
    resp, waits = run([Response(502, {}, b""), TransportError("reset"), Response(200, {}, b"ok")])
    assert resp.status == 200
    assert waits == [0.5, 1.0]


def test_retry_after_is_obeyed_and_capped() -> None:
    _, waits = run([Response(429, {"retry-after": "7"}, b""), Response(200, {}, b"")])
    assert waits == [7.0]
    _, waits = run([Response(429, {"retry-after": "9999"}, b""), Response(200, {}, b"")])
    assert waits == [http.MAX_RETRY_AFTER_S]
    _, waits = run([Response(429, {"retry-after": "Wed, 21 Oct"}, b""), Response(200, {}, b"")])
    assert waits == [0.5]


def test_gives_up_after_max_retries() -> None:
    with pytest.raises(HttpError) as info:
        run([Response(503, {}, b"")] * 3, retries=2)
    assert info.value.status == 503
    assert "abc" not in str(info.value)
    with pytest.raises(TransportError):
        run([TransportError("down")] * 2, retries=1)


def test_client_errors_are_not_retried() -> None:
    with pytest.raises(HttpError, match="404"):
        run([Response(404, {}, b"")])


def test_redact() -> None:
    assert http.redact("https://h/p?private_token=s&page=2") == "https://h/p?private_token=REDACTED&page=2"
    assert http.redact("https://h/p") == "https://h/p"


def test_urllib_transport_rejects_other_schemes() -> None:
    with pytest.raises(ValueError, match="http"):
        http.UrllibTransport().request("GET", "file:///etc/passwd", {}, None, 1)


def test_urllib_transport_unreachable() -> None:
    with pytest.raises(TransportError):
        http.UrllibTransport().request("GET", "http://127.0.0.1:9/", {}, None, 1)
