# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Deterministic synthetic data: screenshots and demos without real identities."""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from pathlib import Path

from tokenusage2.aggregate import midnight
from tokenusage2.ingest import Progress, ScanReport
from tokenusage2.model import Account, Event, QuotaWindow, Tool, Usage

ACCOUNTS = (
    Account(
        "claude:~/.claude",
        Tool.CLAUDE,
        Path("~/.claude"),
        "claude",
        "you@example.com",
        "max 20x",
        "demo",
    ),
    Account(
        "codex:~/.codex", Tool.CODEX, Path("~/.codex"), "codex", "you@example.com", "plus", "demo"
    ),
    Account(
        "codex:~/.codex-work",
        Tool.CODEX,
        Path("~/.codex-work"),
        "codex-work",
        "you@work.example",
        "team",
        "demo",
    ),
    Account(
        "opencode:~/.local/share/opencode/opencode.db",
        Tool.OPENCODE,
        Path("~/.local/share/opencode/opencode.db"),
        "opencode",
        None,
        None,
        "demo",
    ),
)
PROJECTS = ("tokenUsage2", "AgentWhileTrue", "Cullendula", "abtop", "grocery-list", "dotfiles")
HOUR_WEIGHTS = (1, 0, 0, 0, 0, 0, 1, 2, 5, 9, 10, 9, 5, 7, 9, 10, 9, 7, 4, 3, 4, 5, 4, 2)


@dataclass(frozen=True, slots=True)
class Profile:
    account: Account
    per_day: int
    since_days: int
    models: tuple[tuple[str, str, float], ...]
    active_share: float = 0.92


PROFILES = (
    Profile(
        ACCOUNTS[0],
        240,
        70,
        (
            ("claude-opus-5", "anthropic", 0.55),
            ("claude-sonnet-5", "anthropic", 0.25),
            ("north-mini-code-1.0:q4_K_M", "ollama@gpu-box", 0.15),
            ("claude-haiku-4-5", "anthropic", 0.05),
        ),
    ),
    Profile(
        ACCOUNTS[1], 130, 90, (("gpt-5.6-sol", "openai", 0.8), ("gpt-5.6-sol-mini", "openai", 0.2))
    ),
    Profile(ACCOUNTS[2], 90, 28, (("gpt-6-astra", "openai", 1.0),)),
    Profile(ACCOUNTS[3], 8, 60, (("qwen3.6:35b-a3b", "ollama-local", 1.0),), 0.3),
)


def _usage(tool: Tool, rng: random.Random) -> Usage:
    if tool is Tool.CLAUDE:
        return Usage(
            input=rng.randint(1, 400),
            cache_read=rng.randint(15_000, 160_000),
            cache_write=rng.choice((0, 0, 0, rng.randint(1_000, 12_000))),
            output=rng.randint(40, 2_500),
        )
    if tool is Tool.CODEX:
        output = rng.randint(80, 3_500)
        return Usage(
            input=rng.randint(500, 16_000),
            cache_read=rng.randint(8_000, 140_000),
            output=output,
            reasoning=int(output * rng.uniform(0, 0.5)),
        )
    return Usage(input=rng.randint(2_000, 30_000), output=rng.randint(100, 1_500))


class DemoSource:
    mode = "DEMO"

    def __init__(
        self, tz: tzinfo, clock: Callable[[], float] = time.time, seed: int = 7, days: int = 90
    ) -> None:
        self.tz = tz
        self.clock = clock
        self.rng = random.Random(seed)
        self._counter = 0
        self._last = clock()
        self._events = self._history(self._last, days)
        self._generation = 1

    def _event(self, profile: Profile, ts: float) -> Event:
        self._counter += 1
        model, backend = self.rng.choices(
            [(name, backend) for name, backend, _ in profile.models],
            weights=[weight for _, _, weight in profile.models],
        )[0]
        project = self.rng.choice(PROJECTS)
        return Event(
            f"demo:{self._counter}",
            ts,
            profile.account.tool,
            profile.account.id,
            model,
            backend,
            f"/home/you/repos/{project}",
            f"session-{project}",
            _usage(profile.account.tool, self.rng),
        )

    def _history(self, now: float, days: int) -> list[Event]:
        events = []
        today = datetime.fromtimestamp(now, self.tz).date()
        for days_ago in range(days, -1, -1):
            day = today - timedelta(days=days_ago)
            start = midnight(day, self.tz)
            for profile in PROFILES:
                if days_ago > profile.since_days:
                    if profile.account.tool is Tool.CLAUDE and days_ago <= days:
                        tokens = self.rng.randint(8_000_000, 30_000_000)
                        events.append(
                            Event(
                                f"claude-daily:demo:{day}",
                                start + 12 * 3600,
                                Tool.CLAUDE,
                                profile.account.id,
                                "claude-opus-4-7",
                                "anthropic",
                                "(retained daily total)",
                                "",
                                Usage(unsplit=tokens),
                            )
                        )
                    continue
                if self.rng.random() > profile.active_share:
                    continue
                weekend = 0.35 if day.weekday() >= 5 else 1.0
                growth = 0.55 + 0.45 * (1 - days_ago / max(days, 1))
                count = int(profile.per_day * weekend * growth * self.rng.uniform(0.6, 1.3))
                for _ in range(count):
                    hour = self.rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
                    ts = start + hour * 3600 + self.rng.uniform(0, 3600)
                    if ts <= now:
                        events.append(self._event(profile, ts))
        return sorted(events, key=lambda event: event.ts)

    def scan(self, progress: Progress | None = None) -> ScanReport:
        now = self.clock()
        added = 0
        if now - self._last >= 1.0:
            for _ in range(self.rng.randint(0, 3)):
                profile = self.rng.choice(PROFILES[:3])
                self._events.append(self._event(profile, self.rng.uniform(self._last, now)))
                added += 1
            self._events.sort(key=lambda event: event.ts)
            self._last = now
            self._generation += bool(added)
        if progress is not None:
            progress(1, 1)
        return ScanReport(events_changed=added)

    def rediscover(self) -> None:
        """Nothing to discover in demo mode."""

    def close(self) -> None:
        """Nothing to release in demo mode."""

    def events(self) -> list[Event]:
        return self._events

    def generation(self) -> int:
        return self._generation

    def quotas(self) -> list[QuotaWindow]:
        now = self._last
        values = (
            ("claude:~/.claude", 38, 49, 6000, 3 * 86400 + 4 * 3600),
            ("codex:~/.codex", 81, 13, 4100, 5 * 86400),
            ("codex:~/.codex-work", 27, 4, 9000, 6 * 86400 + 19 * 3600),
        )
        quotas = []
        for account, short, week, short_reset, week_reset in values:
            quotas.append(QuotaWindow(account, "5h", short, now + short_reset, now - 30, "demo"))
            quotas.append(QuotaWindow(account, "week", week, now + week_reset, now - 30, "demo"))
        return quotas

    def accounts(self) -> list[Account]:
        return list(ACCOUNTS)

    def archived(self) -> set[str]:
        return set()

    def running(self) -> dict[str, int]:
        return {"claude:~/.claude": 2, "codex:~/.codex": 1}

    def backend_of(self, event: Event) -> str:
        """Demo events already carry display labels."""
        return event.route

    def lifetimes(self) -> None:
        """Recounted per snapshot; the demo history is small."""

    def sources(self) -> list[str]:
        return [
            "demo mode — synthetic data, no files are read",
            *(f"  {a.tool:<8} {a.label:<12} {a.identity or '—'}" for a in ACCOUNTS),
        ]
