"""Persistent state, so a restart cannot repeat an action.

The hazard is narrow and specific (vision DANGER 13): the supervisor sends
Enter, crashes before it records that, restarts, sees the same prompt and sends
Enter again. Recording the action *before* it is sent closes that window - if
the crash happens in between, the restart finds a PLANNED record for that exact
prompt fingerprint and refuses rather than repeating it.

Writes are atomic: a temporary file in the same directory, then ``os.replace``.
A half-written state file is worse than none, because it would be read back as
"nothing has been done yet".
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from agent_watch.states import ActionState

STATE_FILENAME = "state.json"
STATE_VERSION = 1

#: Records older than this are dropped on load. A prompt fingerprint from last
#: week cannot be the prompt on screen now, and unbounded growth in a file that
#: is rewritten on every action is its own problem.
RECORD_TTL_SECONDS = 24 * 3600.0


@dataclass(slots=True)
class ActionRecord:
    """One resume attempt, through its whole lifecycle."""

    key: str
    provider: str
    session: str
    process: str
    state: ActionState
    attempts: int = 0
    planned_at: str = ""
    updated_at: str = ""
    result: str = ""

    @property
    def is_settled(self) -> bool:
        return self.state in {ActionState.VERIFIED, ActionState.FAILED}


def _now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(slots=True)
class StateStore:
    """A small, atomically written JSON file of action records."""

    path: Path
    records: dict[str, ActionRecord] = field(default_factory=dict)

    @classmethod
    def in_directory(cls, directory: Path) -> StateStore:
        return cls(path=directory / STATE_FILENAME)

    # -- persistence -------------------------------------------------------

    def load(self, *, now: datetime | None = None) -> StateStore:
        """Read the state file. A missing or corrupt file starts empty.

        Corruption is deliberately not fatal: refusing to start because of a
        damaged cache would be a worse failure than losing the cache, and the
        only consequence is that one prompt could be actioned again.
        """
        moment = now or datetime.now(UTC)
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.records = {}
            return self
        if not isinstance(document, dict) or document.get("version") != STATE_VERSION:
            self.records = {}
            return self
        records: dict[str, ActionRecord] = {}
        for raw in document.get("actions", []):
            try:
                record = ActionRecord(**{**raw, "state": ActionState(raw["state"])})
            except (TypeError, ValueError, KeyError):
                continue
            if not _expired(record, moment):
                records[record.key] = record
        self.records = records
        return self

    def save(self) -> None:
        """Write the state file atomically, owner-only."""
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        document = {
            "version": STATE_VERSION,
            "actions": [asdict(record) for record in self.records.values()],
        }
        descriptor, name = tempfile.mkstemp(dir=self.path.parent, prefix=f".{self.path.name}.")
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(document, handle, indent=2, sort_keys=True, default=str)
                handle.flush()
                # fsync before the rename: an atomic rename of unflushed data
                # would still leave a truncated file after a power loss.
                os.fsync(handle.fileno())
            temporary.chmod(0o600)
            temporary.replace(self.path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    # -- lifecycle ---------------------------------------------------------

    def plan(self, key: str, *, provider: str, session: str, process: str) -> ActionRecord:
        """Record an action as PLANNED and persist it *before* sending."""
        existing = self.records.get(key)
        attempts = existing.attempts if existing else 0
        record = ActionRecord(
            key=key,
            provider=provider,
            session=session,
            process=process,
            state=ActionState.PLANNED,
            attempts=attempts,
            planned_at=existing.planned_at if existing else _now_text(),
            updated_at=_now_text(),
        )
        self.records[key] = record
        self.save()
        return record

    def mark(self, key: str, state: ActionState, *, result: str = "") -> ActionRecord | None:
        record = self.records.get(key)
        if record is None:
            return None
        if state is ActionState.SENT:
            record.attempts += 1
        record.state = state
        record.result = result
        record.updated_at = _now_text()
        self.save()
        return record

    # -- queries -----------------------------------------------------------

    def attempts_for(self, key: str) -> int:
        record = self.records.get(key)
        return record.attempts if record else 0

    def already_actioned(self) -> frozenset[str]:
        """Keys that must not be actioned again.

        PLANNED counts. A PLANNED record that was never marked SENT is the
        crash-in-between case, and the safe reading of it is "it may already
        have been typed".
        """
        return frozenset(
            key
            for key, record in self.records.items()
            if record.state in {ActionState.PLANNED, ActionState.SENT, ActionState.VERIFIED}
        )

    def forget(self, key: str) -> None:
        if self.records.pop(key, None) is not None:
            self.save()


def _expired(record: ActionRecord, now: datetime) -> bool:
    try:
        updated = datetime.fromisoformat(record.updated_at)
    except ValueError:
        return True
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=UTC)
    return (now - updated).total_seconds() > RECORD_TTL_SECONDS
