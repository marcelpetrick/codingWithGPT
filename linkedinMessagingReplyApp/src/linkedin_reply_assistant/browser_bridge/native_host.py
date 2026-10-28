# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""`lra-native-host`: started by the browser for the extension. Relays to the running app.

Stdlib only. It forwards frames between stdin/stdout (browser) and the app's Unix socket, and tells
the extension when the app is not running. It has no logic of its own: it cannot insert or send.
"""

import contextlib
import socket
import sys
import threading
from typing import BinaryIO

from linkedin_reply_assistant.browser_bridge.protocol import (
    ProtocolError,
    decode_line,
    encode_line,
    read_native,
    socket_path,
    write_native,
)

RETRY_SECONDS = 2.0


class Relay:
    def __init__(self, stdin: BinaryIO, stdout: BinaryIO, retry: float = RETRY_SECONDS) -> None:
        self._in = stdin
        self._out = stdout
        self._retry = retry
        self._lock = threading.Lock()
        self._sock: socket.socket | None = None
        self._closed = threading.Event()

    def send_to_browser(self, message: dict[str, object]) -> None:
        with self._lock:
            write_native(self._out, message)

    def _connect_loop(self) -> None:
        announced = False
        while not self._closed.is_set():
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(str(socket_path()))
            except OSError:
                sock.close()
                if not announced:
                    self.send_to_browser({"type": "app_status", "connected": False})
                    announced = True
                self._closed.wait(self._retry)
                continue
            self._sock = sock
            announced = False
            self.send_to_browser({"type": "app_status", "connected": True})
            self._read_app(sock)
            self._sock = None
            if not self._closed.is_set():
                self.send_to_browser({"type": "app_status", "connected": False})
                announced = True

    def _read_app(self, sock: socket.socket) -> None:
        with sock, sock.makefile("rb") as lines:
            for line in lines:
                try:
                    self.send_to_browser(decode_line(line))
                except ValueError, ProtocolError:
                    continue

    def run(self) -> int:
        threading.Thread(target=self._connect_loop, daemon=True).start()
        try:
            while (message := read_native(self._in)) is not None:
                sock = self._sock
                if sock is None:
                    self.send_to_browser(
                        {"type": "error", "id": message.get("id"), "error": "app not running"}
                    )
                    continue
                try:
                    sock.sendall(encode_line(message))
                except OSError:
                    continue
        except ProtocolError, ValueError:
            return 1
        finally:
            self._closed.set()
            sock = self._sock
            if sock is not None:
                with contextlib.suppress(OSError):  # wakes the reader thread, tells the app
                    sock.shutdown(socket.SHUT_RDWR)
        return 0


def main() -> int:
    # Chrome passes the caller origin as an argument; Firefox passes the manifest path. Not needed.
    return Relay(sys.stdin.buffer, sys.stdout.buffer).run()


if __name__ == "__main__":  # pragma: no cover - the e2e test starts it as a process
    sys.exit(main())
