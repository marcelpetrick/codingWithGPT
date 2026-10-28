# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Wire formats.

Browser <-> native host: Native Messaging framing (4-byte native-endian length + UTF-8 JSON).
Native host <-> app: one JSON object per line on a Unix socket in the user's runtime directory.
The socket has mode 0600, so only the same user can connect (§14.4: no TCP port, no token).
"""

import json
import os
import struct
from pathlib import Path
from typing import Any, BinaryIO

from linkedin_reply_assistant.paths import runtime_dir

HOST_NAME = "io.github.marcelpetrick.lra"
MAX_MESSAGE = 1024 * 1024  # Chrome's limit for messages from the host


class ProtocolError(Exception):
    """A frame is malformed or too large."""


def socket_path() -> Path:
    override = os.environ.get("LRA_BRIDGE_SOCKET")
    return Path(override) if override else runtime_dir() / "bridge.sock"


def read_native(stream: BinaryIO) -> dict[str, Any] | None:
    """Read one Native Messaging frame. None at end of stream (browser closed the port)."""
    header = stream.read(4)
    if not header:
        return None
    if len(header) < 4:
        raise ProtocolError("truncated length header")
    (length,) = struct.unpack("=I", header)
    if length > MAX_MESSAGE:
        raise ProtocolError(f"message too large: {length} bytes")
    body = stream.read(length)
    if len(body) < length:
        raise ProtocolError("truncated message")
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise ProtocolError("message is not a JSON object")
    return value


def write_native(stream: BinaryIO, message: dict[str, Any]) -> None:
    body = json.dumps(message).encode("utf-8")
    if len(body) > MAX_MESSAGE:
        raise ProtocolError(f"message too large: {len(body)} bytes")
    stream.write(struct.pack("=I", len(body)) + body)
    stream.flush()


def encode_line(message: dict[str, Any]) -> bytes:
    return (json.dumps(message) + "\n").encode("utf-8")


def decode_line(line: bytes) -> dict[str, Any]:
    value = json.loads(line.decode("utf-8"))
    if not isinstance(value, dict):
        raise ProtocolError("message is not a JSON object")
    return value
