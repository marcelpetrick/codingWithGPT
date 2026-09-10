# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import shutil
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from conftest import (
    BERLIN,
    CODEX_THREAD,
    NOW,
    FakeHome,
    claude_line,
    codex_tokens,
    line,
    write_jsonl,
)
from tokenusage2.config import Config
from tokenusage2.discover import discover
from tokenusage2.ingest import EventIndex, Ingestor
from tokenusage2.model import Event, Tool, Usage
from tokenusage2.store import Store, StoreError

CLAUDE = "claude:~/.claude"
CODEX = "codex:~/.codex"
WORK = "codex:~/.codex-work"
OPENCODE = "opencode:~/.local/share/opencode/opencode.db"


type Factory = Callable[..., Ingestor]


@pytest.fixture
def make(home: FakeHome) -> Iterator[Factory]:
    """Ingestors over the fake home; their archives are closed after the test."""
    opened: list[Store] = []

    def factory(archive: Path | None = None) -> Ingestor:
        store = Store(archive)
        opened.append(store)
        return Ingestor(
            store,
            discover(home.root, home.env, Config()),
            BERLIN,
            home.root,
            home.env,
            clock=lambda: NOW,
        )

    yield factory
    for store in opened:
        store.close()


def totals(ingestor: Ingestor) -> dict[str, int]:
    sums: dict[str, int] = {}
    for event in ingestor.index.events():
        sums[event.account] = sums.get(event.account, 0) + event.usage.total
    return sums


def test_full_scan_normalises_every_tool(home: FakeHome, make: Factory) -> None:
    ingestor = make()
    report = ingestor.scan()
    assert totals(ingestor) == {CLAUDE: 1160 + 700 + 5000, CODEX: 3300, WORK: 5000, OPENCODE: 125}
    assert report.errors == 1
    quotas = {key: quota.used_percent for key, quota in ingestor.quotas.items()}
    assert quotas[CODEX, "5h"] == 22.0
    assert quotas[CLAUDE, "5h"] == 38.0
    backends = {e.model: e.backend for e in ingestor.index.events() if e.tool is Tool.CLAUDE}
    assert backends == {
        "claude-opus-5": "anthropic",
        "north-mini:q4": "ollama@10.0.0.5",
        "claude-opus-4-7": "anthropic",
    }


def test_unchanged_files_are_not_read_again(home: FakeHome, make: Factory) -> None:
    ingestor = make()
    ingestor.scan()
    report = ingestor.scan()
    assert (report.bytes_read, report.events_changed, report.quota_updates) == (0, 0, 0)
    assert report.files_seen == 4
    assert not report.changed


def test_appended_lines_are_read_incrementally(home: FakeHome, make: Factory) -> None:
    ingestor = make()
    ingestor.scan()
    extra = line(codex_tokens("2026-09-10T10:10:00Z", 4300, inp=900, cached=800, out=100))
    with home.codex_rollout.open("a") as handle:
        handle.write(extra)
    report = ingestor.scan()
    assert report.bytes_read == len(extra.encode())
    assert report.events_changed == 1
    event = next(e for e in ingestor.index.events() if e.key.endswith(":4300"))
    assert (event.session, event.model, event.project) == (
        CODEX_THREAD,
        "gpt-5.6-sol",
        "/work/beta",
    )


def test_partial_line_waits_for_its_newline(home: FakeHome, make: Factory) -> None:
    ingestor = make()
    ingestor.scan()
    extra = line(codex_tokens("2026-09-10T10:10:00Z", 4300, inp=900, cached=800, out=100))
    with home.codex_rollout.open("a") as handle:
        handle.write(extra[:25])
    assert ingestor.scan().events_changed == 0
    with home.codex_rollout.open("a") as handle:
        handle.write(extra[25:])
    assert ingestor.scan().events_changed == 1


def test_truncated_file_is_reread_from_the_start(home: FakeHome, make: Factory) -> None:
    ingestor = make()
    ingestor.scan()
    kept = "".join(home.codex_rollout.read_text().splitlines(keepends=True)[:4])
    home.codex_rollout.write_text(kept)
    report = ingestor.scan()
    assert report.bytes_read == len(kept.encode())
    assert report.events_changed == 0


def test_archive_keeps_history_after_transcripts_vanish(
    home: FakeHome, make: Factory, tmp_path: Path
) -> None:
    archive = tmp_path / "archive.sqlite"
    first = make(archive)
    first.scan()
    before = totals(first)
    first.store.close()
    shutil.rmtree(home.root / ".claude" / "projects")
    second = make(archive)
    report = second.scan()
    assert totals(second) == before
    assert report.bytes_read == 0
    assert {account.id for account in second.store.load_accounts()} >= {CLAUDE, CODEX}


def test_backfill_retreats_when_older_transcripts_appear(home: FakeHome, make: Factory) -> None:
    ingestor = make()
    ingestor.scan()
    assert any(e.key.startswith("claude-daily:") for e in ingestor.index.events())
    write_jsonl(
        home.root / ".claude" / "projects" / "-work-alpha" / "old.jsonl",
        [claude_line("msg_old", "2026-08-30T08:00:00Z")],
    )
    ingestor.scan()
    assert not any(e.key.startswith("claude-daily:") for e in ingestor.index.events())
    assert not any(e.key.startswith("claude-daily:") for e in ingestor.store.load_events())


def test_opencode_is_read_past_its_watermark(home: FakeHome, make: Factory) -> None:
    ingestor = make()
    ingestor.scan()
    assert ingestor.scan().events_changed == 0
    created = int(NOW * 1000)
    with closing(sqlite3.connect(home.opencode_db)) as connection, connection:
        connection.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?, ?)",
            (
                "msg_oc2",
                "ses1",
                created,
                created,
                json.dumps(
                    {
                        "role": "assistant",
                        "time": {"created": created},
                        "tokens": {"input": 1, "output": 1},
                    }
                ),
            ),
        )
    assert ingestor.scan().events_changed == 1


def test_broken_sources_are_reported_not_fatal(home: FakeHome, make: Factory) -> None:
    home.opencode_db.write_bytes(b"not a database" * 100)
    (home.root / ".claude" / "stats-cache.json").write_text("{broken")
    (home.root / ".claude" / "abtop-rate-limits.json").write_text("{broken")
    report = make().scan()
    assert any("opencode.db" in problem for problem in report.problems)
    assert any("stats-cache.json" in problem for problem in report.problems)


def test_unbound_statusline_snapshot_belongs_to_the_main_claude_home(
    home: FakeHome, make: Factory
) -> None:
    state = home.root / ".local" / "state" / "agent-watch" / "quota"
    state.mkdir(parents=True)
    (state / "claude.json").write_text(
        json.dumps(
            {
                "source": "claude",
                "updated_at": NOW,
                "five_hour": {"used_percentage": 90, "resets_at": NOW + 60},
            }
        )
    )
    ingestor = make()
    ingestor.scan()
    assert ingestor.quotas[CLAUDE, "5h"].used_percent == 90.0


def test_schema_mismatch_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "archive.sqlite"
    store = Store(path)
    store.set_meta("schema", "99")
    store.commit()
    store.close()
    with pytest.raises(StoreError, match="schema 99"):
        Store(path)


def test_store_and_index_keep_the_larger_copy() -> None:
    small = Event("k", 1.0, Tool.CLAUDE, "a", "m", "b", "p", "s", Usage(input=1))
    large = replace(small, ts=2.0, usage=Usage(input=5))
    store = Store(None)
    assert store.upsert_events([small]) == 1
    assert store.upsert_events([large]) == 1
    assert store.upsert_events([small]) == 0
    assert store.load_events() == [large]
    assert store.event_counts() == {"a": (1, 2.0, 2.0)}
    assert store.delete_events("k", 0.0) == 1
    index = EventIndex([small])
    assert index.upsert(large)
    assert not index.upsert(small)
    assert index.events() == [large]
    assert index.discard("k", 0.0) == 1
    assert len(index) == 0
    store.close()
