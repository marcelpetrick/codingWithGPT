# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from datetime import date
from pathlib import Path

import pytest

from conftest import BERLIN, NOW, claude_line, codex_meta, codex_tokens, codex_turn
from tokenusage2.discover import BackendMap
from tokenusage2.model import Tool, Usage
from tokenusage2.parsers import (
    ClaudeParser,
    CodexParser,
    claude_route,
    codex_usage,
    count,
    parse_claude_quota,
    parse_opencode_message,
    parse_stats_cache,
    parse_ts,
    thread_from_filename,
)


def encode(record: dict | str) -> bytes:
    return (record if isinstance(record, str) else json.dumps(record)).encode() + b"\n"


def test_claude_record_becomes_an_event() -> None:
    parser = ClaudeParser("acct")
    event = parser.feed(encode(claude_line("msg_a", "2026-09-10T08:00:00Z")))
    assert event is not None
    assert event.key == "claude:msg_a:req_1"
    assert event.usage == Usage(input=10, cache_read=1000, cache_write=100, output=50)
    assert event.route == "anthropic"
    assert event.project == "/work/alpha"
    assert event.ts == parse_ts("2026-09-10T08:00:00Z")


def test_claude_ignores_non_usage_synthetic_and_junk() -> None:
    parser = ClaudeParser("acct")
    assert parser.feed(b'{"type": "user"}\n') is None
    assert parser.feed(encode({"type": "user", "message": {"usage": {}}})) is None
    assert (
        parser.feed(encode(claude_line("m", "2026-09-10T08:00:00Z", model="<synthetic>"))) is None
    )
    assert parser.feed(encode(claude_line("m", "not-a-time"))) is None
    zero = claude_line("m", "2026-09-10T08:00:00Z", inp=0, cache_read=0, cache_write=0, out=0)
    assert parser.feed(encode(zero)) is None
    assert parser.feed(b'{"usage": broken\n') is None
    assert parser.feed(b'["usage"]\n') is None
    assert parser.errors == 2


@pytest.mark.parametrize(
    ("model", "route", "expected"),
    [
        ("claude-opus-5", "anthropic", "anthropic"),
        ("north", "", "ollama@gpu"),
        ("claude-x", "", "anthropic-compatible"),
        ("qwen:7b", "", "ollama"),
        ("qwen/coder", "", "gateway"),
        ("mystery", "", "local"),
    ],
)
def test_claude_backend_labels(model: str, route: str, expected: str) -> None:
    assert BackendMap({"north": "ollama@gpu"}).label(Tool.CLAUDE, model, route) == expected


def test_config_globs_beat_the_logged_route() -> None:
    backends = BackendMap({}, (("claude-*", "bedrock"),))
    assert backends.label(Tool.CLAUDE, "claude-opus-5", "anthropic") == "bedrock"
    assert backends.label(Tool.CLAUDE, "claude-opus-5", "anthropic") == "bedrock"
    assert BackendMap().label(Tool.CODEX, "gpt", "openai") == "openai"
    assert BackendMap().label(Tool.OPENCODE, "m", "") == "unknown"
    assert (claude_route("req_1"), claude_route("")) == ("anthropic", "")


def test_codex_usage_splits_cached_input() -> None:
    usage = codex_usage(
        {
            "input_tokens": 1000,
            "cached_input_tokens": 600,
            "output_tokens": 100,
            "reasoning_output_tokens": 30,
        }
    )
    assert usage == Usage(input=400, cache_read=600, output=100, reasoning=30)
    assert usage.total == 1100
    clamped = codex_usage(
        {"input_tokens": 10, "cached_input_tokens": 50, "cache_write_input_tokens": 5}
    )
    assert (clamped.input, clamped.cache_read, clamped.cache_write) == (0, 10, 0)


def test_codex_parser_carries_context_and_collapses_repeats() -> None:
    parser = CodexParser("acct", {}, "fallback")
    assert parser.feed(encode(codex_meta("thread-1"))) is None
    assert parser.feed(encode(codex_meta("thread-2"))) is None
    assert parser.feed(encode(codex_turn("gpt-5.6-sol"))) is None
    assert parser.feed(encode(codex_tokens("2026-09-10T10:00:00Z", None, primary=20.0))) is None
    first = parser.feed(
        encode(codex_tokens("2026-09-10T10:00:05Z", 1100, inp=1000, cached=600, out=100))
    )
    repeat = parser.feed(
        encode(
            codex_tokens("2026-09-10T10:00:06Z", 1100, inp=1000, cached=600, out=100, primary=22.0)
        )
    )
    assert first is not None
    assert repeat is not None
    assert first.key == repeat.key == "codex:acct:thread-1:1100"
    assert (first.model, first.project, first.session) == ("gpt-5.6-sol", "/work/beta", "thread-1")
    assert [(q.window, q.used_percent, q.plan) for q in parser.quotas] == [
        ("5h", 20.0, "plus"),
        ("week", 60.0, "plus"),
        ("5h", 22.0, "plus"),
        ("week", 60.0, "plus"),
    ]
    resumed = CodexParser("acct", parser.ctx, "fallback")
    later = resumed.feed(
        encode(codex_tokens("2026-09-10T10:05:00Z", 3300, inp=2000, cached=1500, out=200))
    )
    assert later is not None
    assert later.session == "thread-1"
    assert later.model == "gpt-5.6-sol"


def test_codex_parser_ignores_model_limits_and_junk() -> None:
    parser = CodexParser("acct", {}, "fallback")
    parser.feed(
        encode(codex_tokens("2026-09-10T10:00:00Z", None, primary=5.0, limit_id="codex_other"))
    )
    assert parser.quotas == []
    assert parser.feed(b'{"token_count": oops\n') is None
    assert parser.feed(b'{"turn_context": oops\n') is None
    assert parser.errors == 2
    assert (
        parser.feed(
            encode(
                {
                    "type": "response_item",
                    "payload": {"type": "token_count"},
                    "timestamp": "2026-09-10T10:00:00Z",
                }
            )
        )
        is None
    )
    assert (
        parser.feed(
            encode(
                {
                    "type": "event_msg",
                    "timestamp": "2026-09-10T10:00:00Z",
                    "payload": {"type": "agent_message", "text": "token_count"},
                }
            )
        )
        is None
    )
    empty = codex_tokens("2026-09-10T10:00:00Z", 0)
    assert parser.feed(encode(empty)) is None
    no_meta = parser.feed(encode(codex_tokens("2026-09-10T10:00:01Z", 10, inp=10)))
    assert no_meta is not None
    assert no_meta.session == "fallback"
    assert no_meta.model == "unknown"


def test_thread_from_filename() -> None:
    uuid = "0199aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee"
    assert thread_from_filename(Path(f"rollout-2026-09-10T10-00-00-{uuid}.jsonl")) == uuid
    assert thread_from_filename(Path("short.jsonl")) == "short"


def test_opencode_message() -> None:
    data = {
        "role": "assistant",
        "modelID": "m",
        "providerID": "p",
        "path": {"cwd": "/w"},
        "time": {"created": 1_000_000},
        "tokens": {"input": 100, "output": 20, "reasoning": 5, "cache": {"read": 7, "write": 3}},
    }
    event = parse_opencode_message("acct", "row", json.dumps(data))
    assert event is not None
    assert event.usage == Usage(input=100, cache_read=7, cache_write=3, output=25, reasoning=5)
    assert event.ts == 1000.0
    data["tokens"]["total"] = 130
    included = parse_opencode_message("acct", "row", json.dumps(data))
    assert included is not None
    assert included.usage.output == 20
    assert parse_opencode_message("acct", "row", '{"role": "user"}') is None
    assert parse_opencode_message("acct", "row", '{"role": "assistant", "tokens": {}}') is None
    assert parse_opencode_message("acct", "row", "junk") is None
    zero = {"role": "assistant", "time": {"created": 1}, "tokens": {}}
    assert parse_opencode_message("acct", "row", json.dumps(zero)) is None


def test_stats_cache_backfill_only_before_the_first_transcript() -> None:
    data = {
        "dailyModelTokens": [
            {"date": "2026-09-01", "tokensByModel": {"claude-opus-4-7": 5000, "qwen:7b": 7}},
            {"date": "2026-09-10", "tokensByModel": {"claude-opus-5": 9999}},
            {"date": "bad", "tokensByModel": {}},
            {"date": "2026-09-02", "tokensByModel": {"zero": 0}},
            "junk",
        ]
    }
    events = parse_stats_cache("acct", data, date(2026, 9, 10), BERLIN)
    assert [(e.model, e.route, e.usage.unsplit) for e in events] == [
        ("claude-opus-4-7", "anthropic", 5000),
        ("qwen:7b", "", 7),
    ]
    assert events[0].key == "claude-daily:acct:2026-09-01:claude-opus-4-7"
    assert len(parse_stats_cache("acct", data, None, BERLIN)) == 3
    assert parse_stats_cache("acct", {"dailyModelTokens": 3}, None, BERLIN) == []


def test_claude_quota_snapshot() -> None:
    quotas = parse_claude_quota(
        "acct",
        {
            "updated_at": NOW,
            "five_hour": {"used_percentage": 38, "resets_at": NOW + 60},
            "seven_day": {"used_percent": 49},
        },
        1.0,
        "file",
    )
    assert [(q.window, q.used_percent, q.resets_at, q.observed_at) for q in quotas] == [
        ("5h", 38.0, NOW + 60, NOW),
        ("week", 49.0, None, NOW),
    ]
    fallback = parse_claude_quota("acct", {"five_hour": {"used_percentage": True}}, 5.0, "f")
    assert fallback == []


def test_parse_ts_and_count() -> None:
    assert parse_ts("2026-09-10T08:00:00") == parse_ts("2026-09-10T08:00:00Z")
    assert parse_ts("nope") is None
    assert parse_ts(5) is None
    assert (count(True), count(-3), count(2.9), count("5")) == (0, 0, 2, 0)
