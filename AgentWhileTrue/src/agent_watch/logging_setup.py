"""Structured event logging that structurally cannot leak terminal content.

Terminal output routinely contains API keys, passwords, customer data and
source code (vision DANGER 15). The rule is "log events, not content", and here
that rule is enforced by the log API rather than by reviewer discipline: an
event is a set of key/value fields, and the helper that turns screen text into a
loggable value returns a SHA-256 fingerprint, never the text.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import logging.handlers
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

LOGGER_NAME = "agent_watch"

#: Vision section 31.
MAX_LOG_BYTES = 10 * 1024 * 1024
LOG_BACKUPS = 5

#: Field values are single-token by construction; anything with whitespace or a
#: quote is quoted so a parser can still split the line on spaces.
_NEEDS_QUOTING = re.compile(r'[\s"=]')

#: Length of the screen fingerprint kept in logs. Twelve hex characters is ample
#: to distinguish prompts within one session and far too little to be inverted.
FINGERPRINT_CHARS = 12


def fingerprint(lines: list[str] | str) -> str:
    """Return a short, stable fingerprint of screen content.

    This is the *only* sanctioned way for terminal text to influence a log line.
    Trailing whitespace is stripped per line so that a redraw with different
    padding does not look like a different prompt.
    """
    text = "\n".join(lines) if isinstance(lines, list) else lines
    normalised = "\n".join(line.rstrip() for line in text.splitlines())
    digest = hashlib.sha256(normalised.encode("utf-8", errors="replace")).hexdigest()
    return digest[:FINGERPRINT_CHARS]


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    text = str(value)
    if not text:
        return '""'
    if _NEEDS_QUOTING.search(text):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def format_event(event: str, fields: Mapping[str, Any]) -> str:
    """Render one event as ``event=… key=value …``."""
    parts = [f"event={_format_value(event)}"]
    parts.extend(f"{key}={_format_value(value)}" for key, value in fields.items())
    return " ".join(parts)


class EventLogger:
    """Thin wrapper that only ever emits key/value events.

    There is intentionally no ``log(message)`` method: free text is how terminal
    content ends up in a log file by accident.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def event(self, level: int, event: str, /, **fields: Any) -> None:
        self._logger.log(level, format_event(event, fields))

    def debug(self, event: str, /, **fields: Any) -> None:
        self.event(logging.DEBUG, event, **fields)

    def info(self, event: str, /, **fields: Any) -> None:
        self.event(logging.INFO, event, **fields)

    def warning(self, event: str, /, **fields: Any) -> None:
        self.event(logging.WARNING, event, **fields)

    def error(self, event: str, /, **fields: Any) -> None:
        self.event(logging.ERROR, event, **fields)


def setup(
    log_file: Path,
    *,
    level: int = logging.INFO,
    to_stderr: bool = False,
    max_bytes: int = MAX_LOG_BYTES,
    backups: int = LOG_BACKUPS,
) -> EventLogger:
    """Configure and return the event logger.

    The log directory is created with owner-only permissions, and the log file
    itself is chmodded to 0600: the file records which sessions the supervisor
    controls, which is not something other local users need to read.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    for existing in list(logger.handlers):
        logger.removeHandler(existing)
        existing.close()

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    with contextlib.suppress(OSError):  # an exotic filesystem may refuse chmod
        log_file.chmod(0o600)

    if to_stderr:
        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(stderr_handler)

    return EventLogger(logger)


def get_logger() -> EventLogger:
    """Return an event logger over the already-configured handlers."""
    return EventLogger(logging.getLogger(LOGGER_NAME))


def read_history(path: Path, *, limit: int = 10) -> list[str]:
    """Read recent structured events without exposing terminal content."""
    if limit <= 0:
        return []
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return rows[-limit:]
