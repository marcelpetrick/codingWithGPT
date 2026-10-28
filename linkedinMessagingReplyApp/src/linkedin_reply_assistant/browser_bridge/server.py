# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The app side of the bridge: a Unix socket server for the native host (one connection)."""

import contextlib
import itertools
import os
import socket
import threading
from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import Any

from linkedin_reply_assistant.browser_bridge.protocol import (
    ProtocolError,
    decode_line,
    encode_line,
)


class BridgeError(Exception):
    """The extension is not connected or did not answer."""


class BridgeServer:
    def __init__(self, path: Path, on_status: Callable[[str], None] = lambda status: None) -> None:
        self.path = path
        self._on_status = on_status
        self._listener: socket.socket | None = None
        self._client: socket.socket | None = None
        self._pending: dict[int, Future[dict[str, Any]]] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self.status = "not running"
        self.browser = ""

    def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.exists():
            if _alive(self.path):
                raise OSError(f"another instance of the app owns {self.path}")
            self.path.unlink()  # a stale socket from a crashed run
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        old_umask = os.umask(0o177)
        try:
            listener.bind(str(self.path))
        finally:
            os.umask(old_umask)
        listener.listen(1)
        self._listener = listener
        self._set_status("waiting for the browser extension")
        threading.Thread(target=self._accept_loop, name="bridge", daemon=True).start()

    def _set_status(self, status: str) -> None:
        self.status = status
        self._on_status(status)

    @property
    def connected(self) -> bool:
        return self.status == "connected"

    def _accept_loop(self) -> None:
        listener = self._listener  # stop() sets the attribute to None; keep our own reference
        assert listener is not None
        while True:
            try:
                client, _ = listener.accept()
            except OSError:
                return
            with self._lock:
                old, self._client = self._client, client
            if old is not None:
                _shutdown(old)  # newest native host wins (browser restarted)
            self._set_status("connected")
            threading.Thread(target=self._serve, args=(client,), daemon=True).start()

    def _serve(self, client: socket.socket) -> None:
        self._read(client)
        client.close()
        with self._lock:
            current = self._client is client
            if current:
                self._client = None
                self._fail_pending("the browser extension disconnected")
        if current:
            self._set_status("waiting for the browser extension")

    def _read(self, client: socket.socket) -> None:
        try:
            with client.makefile("rb") as lines:
                for line in lines:
                    try:
                        self._dispatch(decode_line(line))
                    except ValueError, ProtocolError:
                        continue
        except OSError:
            return

    def _dispatch(self, message: dict[str, Any]) -> None:
        if message.get("type") == "hello":
            self.browser = str(message.get("browser", ""))
            return
        request_id = message.get("id")
        with self._lock:
            future = self._pending.pop(request_id, None) if isinstance(request_id, int) else None
        if future is not None:
            future.set_result(message)

    def _fail_pending(self, reason: str) -> None:
        for future in self._pending.values():
            future.set_exception(BridgeError(reason))
        self._pending.clear()

    def request(self, message: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
        """Send a request to the extension and wait for the answer with the same id."""
        future: Future[dict[str, Any]] = Future()
        with self._lock:
            client = self._client
            if client is None:
                raise BridgeError("The browser extension is not connected.")
            request_id = next(self._ids)
            self._pending[request_id] = future
            try:
                client.sendall(encode_line({**message, "id": request_id}))
            except OSError as exc:
                self._pending.pop(request_id, None)
                raise BridgeError(f"cannot reach the browser extension: {exc}") from exc
        try:
            return future.result(timeout)
        except TimeoutError as exc:
            with self._lock:
                self._pending.pop(request_id, None)
            raise BridgeError("The browser extension did not answer.") from exc

    def stop(self) -> None:
        with self._lock:
            if self._listener is not None:
                self._listener.close()
                self._listener = None
            if self._client is not None:
                _shutdown(self._client)
                self._client = None
            self._fail_pending("the bridge stopped")
        if self.path.exists():
            self.path.unlink()
        self.status = "not running"


def _shutdown(sock: socket.socket) -> None:
    """Wake a reader blocked on this socket (close() alone does not)."""
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)


def _alive(path: Path) -> bool:
    """True if a running app answers on the socket (a crashed run leaves a dead file)."""
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        probe.connect(str(path))
    except OSError:
        return False
    finally:
        probe.close()
    return True
