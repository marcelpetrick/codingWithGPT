# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration: the real urllib transport against a local server (REQ-SEC-1, REQ-COL-6)."""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from mrreview.http import HttpError, UrllibTransport, request_with_retry

SEEN: list[dict[str, str]] = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        SEEN.append({k.lower(): v for k, v in self.headers.items()})
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/target")
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: Any) -> None:
        return


@pytest.fixture
def url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_redirect_is_refused_and_token_not_forwarded(url: str) -> None:
    SEEN.clear()
    with pytest.raises(HttpError, match="redirects are refused"):
        request_with_retry(
            UrllibTransport(),
            "GET",
            url + "/redirect",
            {"PRIVATE-TOKEN": "t"},
            timeout=5,
            max_retries=0,
            backoff_base=0,
        )
    assert len(SEEN) == 1


def test_plain_get(url: str) -> None:
    resp = UrllibTransport().request("GET", url + "/x", {}, None, 5)
    assert resp.status == 200
    assert resp.body == b"ok"
