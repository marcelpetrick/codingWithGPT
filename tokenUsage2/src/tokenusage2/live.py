# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Data sources for the dashboard: the real machine, or synthetic demo data."""

import time
from collections.abc import Callable, Mapping
from datetime import tzinfo
from pathlib import Path
from typing import Protocol

from tokenusage2.config import Config
from tokenusage2.discover import discover
from tokenusage2.doctor import doctor_lines
from tokenusage2.ingest import Ingestor, Progress, ScanReport
from tokenusage2.model import Account, Event, QuotaWindow
from tokenusage2.procscan import running_by_account, scan_processes
from tokenusage2.store import Store

REDISCOVER_SECONDS = 30.0


class Source(Protocol):
    mode: str

    def scan(self, progress: Progress | None = None) -> ScanReport: ...
    def rediscover(self) -> None: ...
    def events(self) -> list[Event]: ...
    def generation(self) -> int: ...
    def quotas(self) -> list[QuotaWindow]: ...
    def accounts(self) -> list[Account]: ...
    def archived(self) -> set[str]: ...
    def running(self) -> dict[str, int]: ...
    def sources(self) -> list[str]: ...
    def backend_of(self, event: Event) -> str: ...
    def close(self) -> None: ...


class LiveSource:
    """Discovery + ingestion + process scan against the real home directory."""

    mode = "LIVE"

    def __init__(
        self,
        store: Store,
        home: Path,
        env: Mapping[str, str],
        config: Config,
        tz: tzinfo,
        proc: Path = Path("/proc"),
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.store = store
        self.home = home
        self.env = env
        self.config = config
        self.tz = tz
        self.proc = proc
        self.clock = clock
        self.processes = scan_processes(proc)
        self.discovery = discover(home, env, config, self.processes)
        self.ingestor = Ingestor(store, self.discovery, tz, home, env, clock)
        self._discovered_at = clock()
        self._accounts = self._merge_accounts()

    def _merge_accounts(self) -> list[Account]:
        known = {account.id for account in self.discovery.accounts}
        return list(self.discovery.accounts) + [
            account for account in self.store.load_accounts() if account.id not in known
        ]

    def rediscover(self) -> None:
        self.processes = scan_processes(self.proc)
        self.discovery = discover(self.home, self.env, self.config, self.processes)
        self.ingestor.set_discovery(self.discovery)
        self._discovered_at = self.clock()
        self._accounts = self._merge_accounts()

    def scan(self, progress: Progress | None = None) -> ScanReport:
        if self.clock() - self._discovered_at >= REDISCOVER_SECONDS:
            self.rediscover()
        else:
            self.processes = scan_processes(self.proc)
        return self.ingestor.scan(progress)

    def events(self) -> list[Event]:
        return self.ingestor.index.events()

    def generation(self) -> int:
        return self.ingestor.index.generation

    def quotas(self) -> list[QuotaWindow]:
        return list(self.ingestor.quotas.values())

    def accounts(self) -> list[Account]:
        return self._accounts

    def archived(self) -> set[str]:
        known = {account.id for account in self.discovery.accounts}
        return {account.id for account in self._accounts if account.id not in known}

    def running(self) -> dict[str, int]:
        return running_by_account(self.processes, self.discovery.accounts, self.home, self.env)

    def sources(self) -> list[str]:
        return doctor_lines(
            self.discovery,
            self.ingestor,
            self.processes,
            self.running(),
            self.config,
            self.store.path,
            self.home,
            self.tz,
            self.clock(),
        )

    def backend_of(self, event: Event) -> str:
        return self.discovery.backends.label(event.tool, event.model, event.route)

    def close(self) -> None:
        self.store.close()
