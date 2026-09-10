# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Incremental ingestion: tail append-only logs into the archive and memory.

A file is skipped while its inode, size and mtime are unchanged. When it grows,
only the new complete lines are read; when it is replaced or truncated it is
re-read from the start. Keys make every re-read idempotent.
"""

import json
import os
import sqlite3
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from datetime import time as clock_time
from pathlib import Path

from tokenusage2.discover import Discovery, display_path
from tokenusage2.model import Account, Event, QuotaWindow, Tool
from tokenusage2.parsers import (
    BACKFILL_PREFIX,
    make_parser,
    parse_claude_quota,
    parse_opencode_message,
    parse_stats_cache,
)
from tokenusage2.store import FileState, Store

type Progress = Callable[[int, int], None]


class EventIndex:
    """In-memory events by key, applying the archive's keep-the-larger rule."""

    def __init__(self, events: Iterable[Event] = ()) -> None:
        self._by_key: dict[str, Event] = {event.key: event for event in events}
        self._sorted: list[Event] | None = None
        self.generation = 0

    def __len__(self) -> int:
        return len(self._by_key)

    def upsert(self, event: Event) -> bool:
        old = self._by_key.get(event.key)
        if old is not None and event.usage.total <= old.usage.total:
            return False
        self._by_key[event.key] = event
        self._sorted = None
        self.generation += 1
        return True

    def discard(self, prefix: str, min_ts: float) -> int:
        doomed = [
            key
            for key, event in self._by_key.items()
            if key.startswith(prefix) and event.ts >= min_ts
        ]
        for key in doomed:
            del self._by_key[key]
        if doomed:
            self._sorted = None
            self.generation += 1
        return len(doomed)

    def events(self) -> list[Event]:
        if self._sorted is None:
            self._sorted = sorted(self._by_key.values(), key=lambda event: event.ts)
        return self._sorted

    def earliest(self, account: str, skip_prefix: str) -> float | None:
        return min(
            (
                event.ts
                for key, event in self._by_key.items()
                if event.account == account and not key.startswith(skip_prefix)
            ),
            default=None,
        )


@dataclass(slots=True)
class ScanReport:
    files_seen: int = 0
    files_read: int = 0
    bytes_read: int = 0
    events_changed: int = 0
    quota_updates: int = 0
    errors: int = 0
    seconds: float = 0.0
    problems: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.events_changed or self.quota_updates)


def walk_jsonl(root: Path) -> Iterator[Path]:
    for directory, _subdirectories, names in os.walk(root):
        for name in names:
            if name.endswith(".jsonl"):
                yield Path(directory, name)


class Ingestor:
    def __init__(
        self,
        store: Store,
        discovery: Discovery,
        tz: tzinfo,
        home: Path,
        env: Mapping[str, str],
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.store = store
        self.tz = tz
        self.home = home
        self.env = env
        self.clock = clock
        self.index = EventIndex(store.load_events())
        self.quotas = {(q.account, q.window): q for q in store.load_quotas()}
        self._files = store.load_file_states()
        self.last_report = ScanReport()
        self.discovery = discovery
        self.set_discovery(discovery)

    def set_discovery(self, discovery: Discovery) -> None:
        self.discovery = discovery
        self.store.upsert_accounts(discovery.accounts, self.clock())
        self.store.commit()

    def files(self) -> list[FileState]:
        return list(self._files.values())

    def files_for(self, account: Account) -> list[Path]:
        if account.tool is Tool.CLAUDE:
            return list(walk_jsonl(account.home / "projects"))
        if account.tool is Tool.CODEX:
            return [
                path
                for root in ("sessions", "archived_sessions")
                for path in walk_jsonl(account.home / root)
                if path.name.startswith("rollout-")
            ]
        return []

    def scan(self, progress: Progress | None = None) -> ScanReport:
        started = time.perf_counter()
        report = ScanReport()
        jobs = [
            (account, path)
            for account in self.discovery.accounts
            for path in self.files_for(account)
        ]
        for number, (account, path) in enumerate(jobs, 1):
            self._ingest_file(account, path, report)
            if progress is not None and (number % 16 == 0 or number == len(jobs)):
                progress(number, len(jobs))
        for account in self.discovery.accounts:
            if account.tool is Tool.OPENCODE:
                self._ingest_opencode(account, report)
            elif account.tool is Tool.CLAUDE:
                self._backfill(account, report)
                self._claude_quotas(account, report)
        self.store.commit()
        report.seconds = time.perf_counter() - started
        self.last_report = report
        return report

    def _apply(self, events: Iterable[Event]) -> int:
        accepted = [event for event in events if self.index.upsert(event)]
        if accepted:
            self.store.upsert_events(accepted)
        return len(accepted)

    def _apply_quotas(self, quotas: Iterable[QuotaWindow]) -> int:
        changed = []
        for quota in quotas:
            old = self.quotas.get((quota.account, quota.window))
            if old is None or quota.observed_at > old.observed_at:
                self.quotas[quota.account, quota.window] = quota
                changed.append(quota)
        if changed:
            self.store.upsert_quotas(changed)
        return len(changed)

    def _ingest_file(self, account: Account, path: Path, report: ScanReport) -> None:
        key = str(path)
        try:
            stat = path.stat()
        except OSError:
            return
        report.files_seen += 1
        state = self._files.get(key)
        if (
            state is not None
            and state.inode == stat.st_ino
            and state.size == stat.st_size
            and state.mtime_ns == stat.st_mtime_ns
        ):
            return
        resume = (
            state is not None
            and state.inode == stat.st_ino
            and stat.st_size >= state.offset
            and state.account == account.id
        )
        start = state.offset if resume and state is not None else 0
        ctx = state.ctx if resume and state is not None else {}
        parser = make_parser(account, ctx, path, self.discovery.backends)
        events: list[Event] = []
        offset = start
        try:
            with path.open("rb") as handle:
                handle.seek(start)
                for line in handle:
                    if not line.endswith(b"\n"):
                        break
                    offset += len(line)
                    event = parser.feed(line)
                    if event is not None:
                        events.append(event)
        except OSError as error:
            report.problems.append(f"{display_path(path, self.home)}: {error.strerror}")
            return
        report.files_read += 1
        report.bytes_read += offset - start
        report.errors += parser.errors
        report.events_changed += self._apply(events)
        report.quota_updates += self._apply_quotas(parser.quotas)
        state = FileState(
            key, account.id, stat.st_ino, stat.st_size, stat.st_mtime_ns, offset, parser.ctx
        )
        self._files[key] = state
        self.store.save_file_state(state)

    def _ingest_opencode(self, account: Account, report: ScanReport) -> None:
        mark = f"opencode-watermark:{account.id}"
        since = int(self.store.get_meta(mark) or 0)
        try:
            uri = f"{account.home.resolve().as_uri()}?mode=ro"
            with closing(sqlite3.connect(uri, uri=True, timeout=1.0)) as connection:
                rows = connection.execute(
                    "SELECT id, time_updated, data FROM message WHERE time_updated >= ? "
                    "ORDER BY time_updated",
                    (since,),
                ).fetchall()
        except sqlite3.Error as error:
            report.problems.append(f"{display_path(account.home, self.home)}: {error}")
            return
        report.files_seen += 1
        if not rows:
            return
        report.files_read += 1
        events = [
            event
            for row in rows
            if (event := parse_opencode_message(account.id, str(row[0]), row[2]))
        ]
        report.events_changed += self._apply(events)
        self.store.set_meta(mark, str(max(int(row[1]) for row in rows)))

    def _backfill(self, account: Account, report: ScanReport) -> None:
        """Claude's retained daily totals for days no surviving transcript covers."""
        path = account.home / "stats-cache.json"
        try:
            stat = path.stat()
        except OSError:
            return
        first = self.index.earliest(account.id, BACKFILL_PREFIX)
        before = datetime.fromtimestamp(first, self.tz).date() if first is not None else None
        signature = f"{stat.st_size}:{stat.st_mtime_ns}:{before}"
        mark = f"statscache:{account.id}"
        if self.store.get_meta(mark) == signature:
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            report.problems.append(f"{display_path(path, self.home)}: {error}")
            return
        prefix = f"{BACKFILL_PREFIX}{account.id}:"
        if before is not None:
            cutoff = datetime.combine(before, clock_time(0), tzinfo=self.tz).timestamp()
            self.index.discard(prefix, cutoff)
            self.store.delete_events(prefix, cutoff)
        events = parse_stats_cache(
            account.id,
            data if isinstance(data, dict) else {},
            before,
            self.tz,
            self.discovery.backends,
        )
        report.events_changed += self._apply(events)
        self.store.set_meta(mark, signature)

    def quota_files(self, account: Account) -> list[Path]:
        """Statusline snapshots: the account's own, plus unbound ones for the main home."""
        files = sorted(account.home.glob("*rate-limit*.json"))
        claude_homes = [a.home for a in self.discovery.accounts if a.tool is Tool.CLAUDE]
        if account.home == self.home / ".claude" or len(claude_homes) == 1:
            state_home = Path(self.env.get("XDG_STATE_HOME") or self.home / ".local" / "state")
            files += sorted(state_home.glob("*/quota/claude.json"))
        return files

    def _claude_quotas(self, account: Account, report: ScanReport) -> None:
        quotas: list[QuotaWindow] = []
        for path in self.quota_files(account):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                modified = path.stat().st_mtime
            except OSError, ValueError:
                continue
            if isinstance(data, dict) and data.get("source", "claude") == "claude":
                quotas += parse_claude_quota(
                    account.id, data, modified, display_path(path, self.home)
                )
        report.quota_updates += self._apply_quotas(quotas)
