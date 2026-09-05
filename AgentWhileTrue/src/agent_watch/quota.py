"""Provider quota state, kept strictly separate from terminal state.

The vision insists on two sources of truth that must not be conflated: provider
state answers "is usage available, and when does the limit reset", while
terminal state answers "is *this* session waiting, and what input does the
prompt expect". This module is the first of those.

The decisive rule is DANGER 19: if a quota source is missing, stale or broken,
the answer is :data:`Availability.UNKNOWN`. Unknown never means available.

Two passive sources are implemented, both verified against real files:

Codex
    The native Codex process keeps its session rollout ``.jsonl`` open, so the
    exact file for a given PID can be found through ``/proc/<pid>/fd``. Each
    ``token_count`` event in it carries a ``rate_limits`` object with
    ``primary`` (the five-hour window), ``secondary`` (the weekly window) and
    ``credits``. That is machine-readable provider state, which beats parsing
    the rendered TUI.

Claude Code
    Claude Code hands its status-line command a JSON document that includes
    ``five_hour`` and ``seven_day`` usage and reset timestamps. The status-line
    proxy shipped in ``scripts/`` captures that into a small file, which this
    module reads.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_watch.proc import PROC

#: A window at or above this percentage is treated as exhausted.
EXHAUSTED_PERCENT = 100.0

#: Quota data older than this is not trusted. It is generous compared to the
#: 60-second poll interval so that a briefly idle session is not treated as
#: unknown, and short compared to a five-hour window.
DEFAULT_MAX_AGE_SECONDS = 15 * 60.0

#: How much of a rollout file's tail to scan for the newest rate-limit event.
_ROLLOUT_TAIL_BYTES = 256 * 1024

_MINUTES_PER_WEEK = 10080


class Availability(enum.StrEnum):
    """Whether the provider says ordinary usage is allowed."""

    AVAILABLE = "AVAILABLE"
    EXHAUSTED = "EXHAUSTED"
    #: No usable data. Never treated as permission to act.
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class QuotaWindow:
    """One limit window reported by a provider."""

    scope: str
    used_percent: float
    resets_at: datetime | None

    @property
    def exhausted(self) -> bool:
        return self.used_percent >= EXHAUSTED_PERCENT


@dataclass(frozen=True, slots=True)
class QuotaSnapshot:
    """What a source knows about a provider's quota at one instant."""

    provider: str
    availability: Availability
    source: str
    observed_at: datetime | None = None
    windows: tuple[QuotaWindow, ...] = ()
    note: str = ""

    @property
    def exhausted_scopes(self) -> frozenset[str]:
        return frozenset(window.scope for window in self.windows if window.exhausted)

    @property
    def next_reset(self) -> datetime | None:
        """When the *last* currently exhausted window clears.

        Taking the maximum is what stops a five-hour reset from unblocking a
        session whose weekly limit is still spent (vision section 25).
        """
        resets = [
            window.resets_at for window in self.windows if window.exhausted and window.resets_at
        ]
        return max(resets) if resets else None

    def is_stale(self, now: datetime, max_age: float = DEFAULT_MAX_AGE_SECONDS) -> bool:
        if self.observed_at is None:
            return True
        return (now - self.observed_at).total_seconds() > max_age


def unknown(provider: str, source: str, note: str) -> QuotaSnapshot:
    """Build the fail-closed snapshot. Used wherever a source cannot answer."""
    return QuotaSnapshot(
        provider=provider, availability=Availability.UNKNOWN, source=source, note=note
    )


def _availability(windows: Iterable[QuotaWindow]) -> Availability:
    materialised = list(windows)
    if not materialised:
        return Availability.UNKNOWN
    if any(window.exhausted for window in materialised):
        return Availability.EXHAUSTED
    return Availability.AVAILABLE


def _timestamp(value: object) -> datetime | None:
    """Accept a unix timestamp or an ISO-8601 string; reject anything else."""
    if isinstance(value, int | float) and value > 0:
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _percent(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


class QuotaSource:
    """A provider quota source.

    Sources are failure-isolated by contract: :meth:`snapshot` must never raise,
    because a broken Codex source must not stop Claude monitoring (vision
    section 29).
    """

    provider: str = "abstract"
    name: str = "abstract"

    def snapshot(self, *, pid: int | None = None) -> QuotaSnapshot:
        raise NotImplementedError


# -- Codex ----------------------------------------------------------------


def find_codex_rollout(pid: int) -> Path | None:
    """Return the session rollout file the Codex process at ``pid`` has open."""
    fd_dir = PROC / str(pid) / "fd"
    try:
        entries = list(fd_dir.iterdir())
    except OSError:
        return None
    for entry in entries:
        try:
            target = entry.readlink()
        except OSError:
            continue
        text = str(target)
        if "/sessions/" in text and text.endswith(".jsonl") and "rollout-" in text:
            return Path(text)
    return None


def _last_rate_limits(path: Path) -> tuple[dict, datetime | None] | None:
    """Return the newest ``rate_limits`` object in a rollout file."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - _ROLLOUT_TAIL_BYTES))
            tail = handle.read()
    except OSError:
        return None
    # A partial first line is expected after seeking; it simply fails to parse.
    for raw in reversed(tail.split(b"\n")):
        if b"rate_limits" not in raw:
            continue
        try:
            event = json.loads(raw.decode("utf-8", errors="replace"))
        except (ValueError, UnicodeDecodeError):
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        limits = payload.get("rate_limits")
        if isinstance(limits, dict):
            return limits, _timestamp(event.get("timestamp"))
    return None


def _codex_windows(limits: dict) -> list[QuotaWindow]:
    windows: list[QuotaWindow] = []
    for key, default_scope in (("primary", "session"), ("secondary", "weekly")):
        entry = limits.get(key)
        if not isinstance(entry, dict):
            continue
        used = _percent(entry.get("used_percent"))
        if used is None:
            continue
        minutes = entry.get("window_minutes")
        scope = default_scope
        if isinstance(minutes, int | float):
            scope = "weekly" if minutes >= _MINUTES_PER_WEEK else "session"
        windows.append(
            QuotaWindow(
                scope=scope,
                used_percent=used,
                resets_at=_timestamp(entry.get("resets_at")),
            )
        )
    return windows


@dataclass(slots=True)
class CodexRolloutSource(QuotaSource):
    """Read Codex's own rate-limit reporting out of its session rollout."""

    provider: str = "codex"
    name: str = "codex-rollout"

    def snapshot(self, *, pid: int | None = None) -> QuotaSnapshot:
        if pid is None:
            return unknown(self.provider, self.name, "no-pid")
        try:
            path = find_codex_rollout(pid)
            if path is None:
                return unknown(self.provider, self.name, "no-rollout-file")
            found = _last_rate_limits(path)
            if found is None:
                return unknown(self.provider, self.name, "no-rate-limit-event")
            limits, observed_at = found
            windows = _codex_windows(limits)
            if not windows:
                return unknown(self.provider, self.name, "unrecognised-rate-limit-shape")
            reached = limits.get("rate_limit_reached_type")
            availability = _availability(windows)
            if reached:
                availability = Availability.EXHAUSTED
            return QuotaSnapshot(
                provider=self.provider,
                availability=availability,
                source=self.name,
                observed_at=observed_at,
                windows=tuple(windows),
                note=str(reached) if reached else "",
            )
        except Exception as exc:  # a source must never break the supervision loop
            return unknown(self.provider, self.name, f"error:{type(exc).__name__}")


# -- Claude Code ----------------------------------------------------------

#: Keys the status-line proxy writes, mapped to the scope names used here.
_CLAUDE_SCOPES = {
    "five_hour": "session",
    "seven_day": "weekly",
    "seven_day_opus": "opus",
    "seven_day_sonnet": "sonnet",
}


@dataclass(slots=True)
class ClaudeStatuslineSource(QuotaSource):
    """Read the file written by the status-line proxy in ``scripts/``."""

    path: Path
    provider: str = "claude"
    name: str = "claude-statusline"

    def snapshot(self, *, pid: int | None = None) -> QuotaSnapshot:
        del pid  # The status-line file is per-account, not per-process.
        try:
            if not self.path.is_file():
                return unknown(self.provider, self.name, "no-statusline-file")
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                return unknown(self.provider, self.name, "unrecognised-statusline-shape")
            windows = []
            for key, scope in _CLAUDE_SCOPES.items():
                entry = document.get(key)
                if not isinstance(entry, dict):
                    continue
                used = _percent(entry.get("used_percentage"))
                if used is None:
                    used = _percent(entry.get("utilization"))
                if used is None:
                    continue
                windows.append(
                    QuotaWindow(
                        scope=scope,
                        used_percent=used,
                        resets_at=_timestamp(entry.get("resets_at")),
                    )
                )
            if not windows:
                return unknown(self.provider, self.name, "no-usable-windows")
            return QuotaSnapshot(
                provider=self.provider,
                availability=_availability(windows),
                source=self.name,
                observed_at=_timestamp(document.get("updated_at")),
                windows=tuple(windows),
            )
        except Exception as exc:  # a source must never break the supervision loop
            return unknown(self.provider, self.name, f"error:{type(exc).__name__}")


@dataclass(slots=True)
class NullSource(QuotaSource):
    """A source that always answers UNKNOWN.

    Used when a provider integration is disabled, so the rest of the system
    exercises the same fail-closed path as a broken source would.
    """

    provider: str = "unknown"
    name: str = "null"

    def snapshot(self, *, pid: int | None = None) -> QuotaSnapshot:
        del pid
        return unknown(self.provider, self.name, "disabled")


def default_sources(state_dir: Path) -> dict[str, QuotaSource]:
    """Build the standard source per provider."""
    return {
        "codex": CodexRolloutSource(),
        "claude": ClaudeStatuslineSource(path=state_dir / "quota" / "claude.json"),
    }
