# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""The sources report: what was found, where, how, and whether it adds up."""

import json
import sqlite3
from collections.abc import Mapping, Sequence
from contextlib import closing
from datetime import datetime, tzinfo
from pathlib import Path

from tokenusage2.config import Config
from tokenusage2.discover import Discovery, display_path
from tokenusage2.ingest import Ingestor
from tokenusage2.model import Account, Event, Tool
from tokenusage2.procscan import AgentProcess
from tokenusage2.render import compact, duration


def retained_total(account: Account) -> tuple[int, str] | None:
    """The tool's own headline total, for comparison with what was parsed."""
    if account.tool is Tool.CODEX:
        databases = sorted(account.home.glob("state_*.sqlite"))
        if not databases:
            return None
        try:
            uri = f"{databases[-1].resolve().as_uri()}?mode=ro"
            with closing(sqlite3.connect(uri, uri=True, timeout=1.0)) as connection:
                value = connection.execute(
                    "SELECT COALESCE(SUM(tokens_used), 0) FROM threads"
                ).fetchone()[0]
        except sqlite3.Error:
            return None
        return int(value), "Codex threads.tokens_used"
    if account.tool is Tool.CLAUDE:
        try:
            data = json.loads((account.home / "stats-cache.json").read_text(encoding="utf-8"))
        except OSError, ValueError:
            return None
        models = data.get("modelUsage") if isinstance(data, dict) else None
        if not isinstance(models, dict):
            return None
        fields = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")
        value = sum(
            int(model.get(name) or 0)
            for model in models.values()
            if isinstance(model, dict)
            for name in fields
        )
        return value, "Claude stats-cache modelUsage"
    return None


def reconcile(account: Account, events: Sequence[Event]) -> str | None:
    retained = retained_total(account)
    if retained is None or not retained[0]:
        return None
    parsed = sum(event.usage.total for event in events if event.account == account.id)
    value, label = retained
    summary = (
        f"parsed {compact(parsed)} vs {label} {compact(value)} ({(parsed - value) / value:+.1%})"
    )
    if account.tool is Tool.CLAUDE and parsed < value:
        summary += " — the cache also counts sessions whose transcripts are gone"
    return summary


def _day(ts: float | None, tz: tzinfo) -> str:
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d") if ts else "—"


def doctor_lines(
    discovery: Discovery,
    ingestor: Ingestor,
    processes: Sequence[AgentProcess],
    running: Mapping[str, int],
    config: Config,
    archive: Path | None,
    home: Path,
    tz: tzinfo,
    now: float,
) -> list[str]:
    events = ingestor.index.events()
    counts = ingestor.store.event_counts()
    files: dict[str, int] = {}
    for state in ingestor.files():
        files[state.account] = files.get(state.account, 0) + 1
    lines = [
        f"archive    {display_path(archive, home) if archive else 'in memory (--no-archive)'}",
        f"config     {display_path(config.source, home) if config.source else 'none (optional)'}",
        f"rc files   {', '.join(path.name for path in discovery.rc_files) or 'none'}",
        f"processes  {len(processes)} running agent processes",
        "",
        "ACCOUNTS",
    ]
    for account in discovery.accounts:
        count, first, last = counts.get(account.id, (0, None, None))
        lines.append(
            f"  {account.tool:<8} {account.label:<16} {display_path(account.home, home)}"
            f"  [found via {account.origin}]"
        )
        who = " · ".join(filter(None, (account.identity, account.plan))) or "identity unknown"
        lines.append(f"           {who} · {running.get(account.id, 0)} running")
        stored = (
            "database" if account.tool is Tool.OPENCODE else f"{files.get(account.id, 0)} files"
        )
        lines.append(
            f"           {stored} · {count:,} events · {_day(first, tz)} → {_day(last, tz)}"
        )
        for (owner, window), quota in sorted(ingestor.quotas.items()):
            if owner == account.id:
                lines.append(
                    f"           quota {window}: {quota.used_percent:.0f}% · observed "
                    f"{duration(now - quota.observed_at)} ago via {quota.source}"
                )
        summary = reconcile(account, events)
        if summary:
            lines.append(f"           {summary}")
    discovered = {account.id for account in discovery.accounts}
    archived = [
        account for account in ingestor.store.load_accounts() if account.id not in discovered
    ]
    if archived:
        lines += ["", "ARCHIVED (no longer on disk, history kept)"]
        for account in archived:
            count = counts.get(account.id, (0, None, None))[0]
            lines.append(f"  {account.tool:<8} {account.label:<16} {count:,} events")
    lines += ["", "BACKENDS (models routed away from Anthropic)"]
    for hint in discovery.hints:
        models = ", ".join(hint.models) or "(no model pinned)"
        lines.append(f"  {hint.launcher:<18} {hint.label:<26} {models}  [{hint.source}]")
    if not discovery.hints:
        lines.append("  none found in shell rc files or running processes")
    if discovery.notes:
        lines += ["", "NOTES"] + [f"  {note}" for note in discovery.notes]
    report = ingestor.last_report
    lines += [
        "",
        f"LAST SCAN  {report.files_seen} files seen · {report.files_read} read · "
        f"{report.bytes_read / 2**20:,.1f} MiB · {report.events_changed:,} events changed · "
        f"{report.errors} unparsable lines · {report.seconds * 1000:.0f} ms",
    ]
    lines += [f"  problem: {problem}" for problem in report.problems[:10]]
    return lines
