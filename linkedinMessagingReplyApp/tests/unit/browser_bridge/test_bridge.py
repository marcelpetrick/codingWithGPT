# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import io
import json
import os
import socket
import stat
import struct
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from linkedin_reply_assistant.browser_bridge import protocol
from linkedin_reply_assistant.browser_bridge.fingerprint import Identity, compare, normalize_name
from linkedin_reply_assistant.browser_bridge.inserter import (
    CONVERSATION_CHANGED,
    INSERTED,
    NOT_VERIFIED,
    Inserter,
)
from linkedin_reply_assistant.browser_bridge.native_host import Relay
from linkedin_reply_assistant.browser_bridge.server import BridgeError, BridgeServer


def frame(message: dict[str, Any]) -> bytes:
    body = json.dumps(message).encode()
    return struct.pack("=I", len(body)) + body


def wait(condition: Any, seconds: float = 3) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, "condition not reached"
        time.sleep(0.01)


# --- protocol ---------------------------------------------------------------------------------


def test_native_framing_round_trip() -> None:
    out = io.BytesIO()
    protocol.write_native(out, {"type": "x", "text": "Grüße"})
    assert protocol.read_native(io.BytesIO(out.getvalue())) == {"type": "x", "text": "Grüße"}
    assert protocol.read_native(io.BytesIO(b"")) is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"\x01\x00", "truncated length"),
        (struct.pack("=I", 10) + b"{}", "truncated message"),
        (struct.pack("=I", protocol.MAX_MESSAGE + 1), "too large"),
        (frame([1, 2]), "not a JSON object"),  # type: ignore[arg-type]
    ],
)
def test_native_framing_errors(data: bytes, message: str) -> None:
    with pytest.raises(protocol.ProtocolError, match=message):
        protocol.read_native(io.BytesIO(data))


def test_write_too_large() -> None:
    with pytest.raises(protocol.ProtocolError, match="too large"):
        protocol.write_native(io.BytesIO(), {"text": "x" * protocol.MAX_MESSAGE})


def test_lines_and_socket_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert protocol.decode_line(protocol.encode_line({"a": 1})) == {"a": 1}
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_line(b"[1]\n")
    monkeypatch.setenv("LRA_BRIDGE_SOCKET", str(tmp_path / "s"))
    assert protocol.socket_path() == tmp_path / "s"
    monkeypatch.delenv("LRA_BRIDGE_SOCKET")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert protocol.socket_path() == tmp_path / "linkedin-reply-assistant" / "bridge.sock"


# --- fingerprint ------------------------------------------------------------------------------


def test_fingerprint() -> None:
    assert normalize_name("Zoë  Müller-Lüdenscheidt!") == "zoe  mullerludenscheidt"
    page = Identity("Anna Keller", "https://www.linkedin.com/messaging/thread/2-abc/?x=1")
    assert page.thread_id == "2-abc"
    assert Identity("x", "https://www.linkedin.com/feed/").thread_id is None
    assert compare("Anna Keller", page) == "match"
    assert compare("Anna", page) == "match"
    assert compare("Anna Kel1er", page) == "match"
    assert compare("Tom Brandt", page) == "mismatch"
    assert compare(None, page) == "unknown"
    assert compare("Anna", None) == "unknown"
    assert compare("Anna", Identity(" ", "u")) == "unknown"
    assert compare("123", page) == "unknown"


# --- inserter with a scripted transport --------------------------------------------------------


class Scripted:
    def __init__(self, *answers: dict[str, object]) -> None:
        self.answers = list(answers)
        self.sent: list[dict[str, object]] = []

    def request(self, message: dict[str, object], timeout: float = 5.0) -> dict[str, object]:
        self.sent.append(message)
        return self.answers.pop(0)


IDENT = {"ok": True, "title": "Anna Keller", "url": "https://www.linkedin.com/messaging/thread/1/"}


def test_inserter_paths() -> None:
    ok = Scripted(IDENT, {"ok": True, "readback": "Hi  Anna\n"})
    assert Inserter(ok).insert("Hi Anna", "Anna Keller").message == INSERTED
    assert ok.sent[1] == {"type": "insert", "text": "Hi Anna", "url": IDENT["url"]}
    assert (
        Inserter(Scripted({"ok": False})).insert("x", "Anna").message.startswith("the active tab")
    )
    assert Inserter(Scripted(IDENT)).insert("x", "Tom").message == CONVERSATION_CHANGED
    unknown = Inserter(Scripted(IDENT)).insert("x", None)
    assert unknown.needs_confirmation and "unknown participant" in unknown.message
    failed = Inserter(Scripted(IDENT, {"ok": False, "error": "composer missing"})).insert(
        "x", "Anna"
    )
    assert failed.message == "composer missing"
    bare = Inserter(Scripted(IDENT, {"ok": False})).insert("x", "Anna")
    assert bare.message == "insertion failed"
    wrong = Inserter(Scripted(IDENT, {"ok": True, "readback": "other"})).insert("x y", "Anna")
    assert wrong.message == NOT_VERIFIED


# --- server + relay over a real Unix socket ----------------------------------------------------


@pytest.fixture
def server(tmp_path: Path) -> Any:
    statuses: list[str] = []
    path = tmp_path / "run" / "bridge.sock"
    path.parent.mkdir()
    path.write_text("stale")
    bridge = BridgeServer(path, statuses.append)
    bridge.start()
    yield bridge, statuses
    bridge.stop()


class Pipe:
    """A blocking byte stream that the test writes to and the relay reads from."""

    def __init__(self) -> None:
        self.read_fd, self.write_fd = os.pipe()
        self.reader = os.fdopen(self.read_fd, "rb")
        self.writer = os.fdopen(self.write_fd, "wb")


class Collector(io.RawIOBase):
    def __init__(self) -> None:
        self.data = bytearray()
        self.lock = threading.Lock()

    def writable(self) -> bool:
        return True

    def write(self, b: Any) -> int:
        with self.lock:
            self.data += bytes(b)
        return len(b)

    def messages(self) -> list[dict[str, Any]]:
        with self.lock:
            stream = io.BytesIO(bytes(self.data))
        found = []
        while (message := protocol.read_native(stream)) is not None:
            found.append(message)
        return found


def test_socket_is_private_and_stale_file_replaced(server: Any) -> None:
    bridge, statuses = server
    mode = stat.S_IMODE(os.stat(bridge.path).st_mode)
    assert mode == 0o600 and statuses == ["waiting for the browser extension"]
    with pytest.raises(BridgeError, match="not connected"):
        bridge.request({"type": "identify"})


def test_relay_round_trip(server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, statuses = server
    monkeypatch.setenv("LRA_BRIDGE_SOCKET", str(bridge.path))
    stdin, stdout = Pipe(), Collector()
    relay = Relay(stdin.reader, stdout, retry=0.05)  # type: ignore[arg-type]
    thread = threading.Thread(target=relay.run, daemon=True)
    thread.start()
    wait(lambda: bridge.connected)
    stdin.writer.write(frame({"type": "hello", "browser": "chromium"}))
    stdin.writer.flush()
    wait(lambda: bridge.browser == "chromium")

    def browser() -> None:  # answer the first request like the extension would
        wait(lambda: any(m.get("type") == "identify" for m in stdout.messages()))
        request = next(m for m in stdout.messages() if m.get("type") == "identify")
        stdin.writer.write(b"")
        stdin.writer.write(frame({"id": request["id"], "ok": True, "title": "Anna"}))
        stdin.writer.flush()

    threading.Thread(target=browser, daemon=True).start()
    assert bridge.request({"type": "identify"}) == {"id": 1, "ok": True, "title": "Anna"}
    assert {"type": "app_status", "connected": True} in stdout.messages()
    stdin.writer.close()  # browser closes the port
    thread.join(3)
    wait(lambda: not bridge.connected)
    assert statuses[-1] == "waiting for the browser extension"


def test_relay_without_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LRA_BRIDGE_SOCKET", str(tmp_path / "missing.sock"))
    stdin = io.BytesIO(frame({"type": "identify", "id": 7}))
    stdout = Collector()
    relay = Relay(stdin, stdout, retry=0.05)  # type: ignore[arg-type]
    time.sleep(0)
    assert relay.run() == 0
    messages = stdout.messages()
    assert {"type": "error", "id": 7, "error": "app not running"} in messages


def test_relay_bad_frame_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LRA_BRIDGE_SOCKET", str(tmp_path / "missing.sock"))
    assert Relay(io.BytesIO(b"\x01"), Collector(), retry=0.05).run() == 1  # type: ignore[arg-type]


def test_server_timeout_disconnect_and_reconnect(server: Any) -> None:
    bridge, _ = server
    first = socket.socket(socket.AF_UNIX)
    first.connect(str(bridge.path))
    wait(lambda: bridge.connected)
    with pytest.raises(BridgeError, match="did not answer"):
        bridge.request({"type": "identify"}, timeout=0.1)
    first.sendall(
        b"not json\n" + protocol.encode_line({"id": 999}) + protocol.encode_line({"type": "x"})
    )
    second = socket.socket(socket.AF_UNIX)
    second.connect(str(bridge.path))  # the newest connection wins
    wait(lambda: bridge.connected)
    result: list[Any] = []

    def ask() -> None:
        try:
            bridge.request({"type": "identify"}, timeout=3)
        except BridgeError as exc:
            result.append(exc)

    asker = threading.Thread(target=ask)
    asker.start()
    time.sleep(0.2)
    second.close()
    asker.join(3)
    assert result and "disconnected" in str(result[0])
    first.close()


def test_request_send_failure(server: Any) -> None:
    bridge, _ = server
    client = socket.socket(socket.AF_UNIX)
    client.connect(str(bridge.path))
    wait(lambda: bridge.connected)

    class Broken:
        def sendall(self, data: bytes) -> None:
            raise OSError("broken pipe")

    bridge._client = Broken()
    with pytest.raises(BridgeError, match="cannot reach"):
        bridge.request({"type": "identify"})
    bridge._client = None
    client.close()
