# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""HTTP transport with retry, backoff and rate-limit handling (REQ-COL-6).

The transport is an interface, so tests can replace the network.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_AFTER_S = 120.0
_SECRET_PARAMS = frozenset({"private_token", "access_token", "token"})


@dataclass(frozen=True)
class Response:
    """An HTTP response with lower-case header names."""

    status: int
    headers: Mapping[str, str]
    body: bytes


class TransportError(OSError):
    """The server could not be reached (DNS, refused, reset, timeout)."""


class HttpError(RuntimeError):
    """The server answered with a final error status."""

    def __init__(self, status: int, url: str, detail: str = "") -> None:
        super().__init__(f"HTTP {status} for {redact(url)}{': ' + detail if detail else ''}")
        self.status = status


class Transport(Protocol):
    def request(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float
    ) -> Response: ...


def redact(url: str) -> str:
    """Remove secret query parameters from a URL before it is logged."""
    parts = urlsplit(url)
    query = [(k, "REDACTED" if k.lower() in _SECRET_PARAMS else v) for k, v in parse_qsl(parts.query)]
    return urlunsplit(parts._replace(query=urlencode(query)))


class UrllibTransport:
    """The real network transport (standard library)."""

    def request(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float
    ) -> Response:
        if not url.startswith(("http://", "https://")):
            raise ValueError("only http and https URLs are allowed")
        req = urllib.request.Request(url, data=body, method=method, headers=dict(headers))  # noqa: S310
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return Response(
                    resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
                )
        except urllib.error.HTTPError as exc:
            hdrs = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            return Response(exc.code, hdrs, exc.read() or b"")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            raise TransportError(f"{type(exc).__name__}: {reason} ({redact(url)})") from None


def retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """Read Retry-After in seconds. HTTP-date values are not supported and give None."""
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return min(max(float(value), 0.0), MAX_RETRY_AFTER_S)
    except ValueError:
        return None


def request_with_retry(
    transport: Transport,
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None = None,
    *,
    timeout: float,
    max_retries: int,
    backoff_base: float,
    sleep: Callable[[float], None] = time.sleep,
) -> Response:
    """Send a request; retry transport errors, 429 and 5xx with exponential backoff."""
    attempt = 0
    while True:
        try:
            resp = transport.request(method, url, headers, body, timeout)
        except TransportError:
            if attempt >= max_retries:
                raise
            sleep(backoff_base * 2**attempt)
            attempt += 1
            continue
        if resp.status in RETRY_STATUS and attempt < max_retries:
            wait = retry_after_seconds(resp.headers)
            sleep(wait if wait is not None else backoff_base * 2**attempt)
            attempt += 1
            continue
        if resp.status >= 400:
            raise HttpError(resp.status, url)
        return resp
