# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests: the real HTTP client and runner against the fake engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fake_engine import FakeEngine

from mvo.client import Engine, EngineError, EngineUnreachable, Timing, stream_chat, unload_ollama
from mvo.runner import EXCLUSIONS, Arm, done_keys, load_exclusions, run_arm, warm_up
from mvo.workloads import build

MSG = [{"role": "user", "content": "hi"}]


def engines(url: str) -> list[Engine]:
    return [Engine("ollama", "ollama", url, "m"), Engine("magnitude", "openai", url + "/v1", "m")]


@pytest.mark.parametrize("index", [0, 1])
def test_stream_ok(fake: FakeEngine, index: int) -> None:
    timing = stream_chat(engines(fake.url)[index], MSG, 30, 4096)
    assert timing.text == fake.answer
    assert timing.prompt_tokens == 120 and timing.completion_tokens == 30
    assert timing.ttft_s >= 0 and timing.total_s >= timing.ttft_s
    assert timing.reasoning_chars == 0
    assert timing.engine_counters


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize(
    "mode,message",
    [("empty", "empty answer"), ("http500", "HTTP 500"), ("nousage", "no token counts"), ("error", "stream error")],
)
def test_stream_defects(fake: FakeEngine, index: int, mode: str, message: str) -> None:
    fake.mode = mode
    with pytest.raises(EngineError, match=message):
        stream_chat(engines(fake.url)[index], MSG, 30, 4096)


def test_openai_without_done_marker(fake: FakeEngine) -> None:
    fake.mode = "nodone"
    assert stream_chat(engines(fake.url)[1], MSG, 30, 4096).completion_tokens == 30


@pytest.mark.parametrize("index", [0, 1])
def test_thinking_is_counted(fake: FakeEngine, index: int) -> None:
    fake.mode = "thinking"
    assert stream_chat(engines(fake.url)[index], MSG, 30, 4096).reasoning_chars == 3


def test_unreachable() -> None:
    with pytest.raises(EngineUnreachable):
        stream_chat(Engine("x", "ollama", "http://127.0.0.1:9", "m"), MSG, 1, 1, timeout_s=2)


def test_unload(fake: FakeEngine) -> None:
    unload_ollama(fake.url, "m")
    assert fake.requests[-1]["body"] == {"model": "m", "keep_alive": 0}


def arm(url: str, label: str = "ollama-x") -> Arm:
    return Arm(label, Engine("ollama", "ollama", url, "m"), "9.9.9", "none", "Q4", "test")


def test_run_arm_writes_rows_and_resumes(fake: FakeEngine, tmp_path: Path) -> None:
    out = tmp_path / "r.jsonl"
    logs: list[str] = []
    failed = run_arm(arm(fake.url), [("C", 4096)], 1, out, facts_fn=lambda: {"gpu": "g"}, log=logs.append)
    assert failed == 0
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == 20 and all(r["ok"] for r in rows)
    by_id = {r["prompt_id"]: r for r in rows}
    assert by_id["C-is-palindrome"]["passed"] is True
    assert by_id["C-roman"]["passed"] is False
    assert rows[0]["gpu"] == "g" and rows[0]["engine_version"] == "9.9.9"
    assert len(done_keys(out)) == 20
    sent = len(fake.requests)
    run_arm(arm(fake.url), [("C", 4096)], 1, out, facts_fn=dict, log=logs.append)
    assert len(fake.requests) == sent  # nothing re-run, not even the warm-up
    assert logs[-1].startswith("skip")


def test_run_arm_failed_rows_and_retry(fake: FakeEngine, tmp_path: Path) -> None:
    out = tmp_path / "r.jsonl"
    fake.mode = "thinking"
    failed = run_arm(arm(fake.url), [("A", 4096)], 2, out, facts_fn=dict, log=lambda _: None)
    assert failed == 2
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(not r["ok"] and "thinking" in r["error"] for r in rows)
    fake.mode = "empty"
    # The warm-up uses the same stream; an empty warm-up is a defect and stops the cell.
    with pytest.raises(EngineError):
        run_arm(arm(fake.url), [("A", 4096)], 2, out, facts_fn=dict, log=lambda _: None)
    fake.mode = "ok"
    assert run_arm(arm(fake.url), [("A", 4096)], 2, out, facts_fn=dict, log=lambda _: None) == 0
    assert done_keys(out) == {"ollama-x|A-moby-4096|0", "ollama-x|A-moby-4096|1"}


def test_run_arm_http_error_row(fake: FakeEngine, tmp_path: Path) -> None:
    out = tmp_path / "r.jsonl"
    stream_calls = {"n": 0}

    def flaky(engine: Engine, messages: list[dict[str, Any]], max_tokens: int, ctx: int):  # type: ignore[no-untyped-def]
        stream_calls["n"] += 1
        if "warmup" in messages[0]["content"]:
            return stream_chat(engine, messages, max_tokens, ctx)
        raise EngineError("HTTP 500: refused")

    assert run_arm(arm(fake.url), [("A", 4096)], 1, out, stream=flaky, facts_fn=dict, log=lambda _: None) == 1
    assert done_keys(out) == set()


def test_run_arm_vision_rows(fake: FakeEngine, tmp_path: Path) -> None:
    out = tmp_path / "r.jsonl"
    fake.answer = "The square is red and on the right is a circle."
    assert run_arm(arm(fake.url), [("V", 4096)], 1, out, facts_fn=dict, log=lambda _: None) == 0
    rows = {json.loads(line)["prompt_id"]: json.loads(line) for line in out.read_text().splitlines()}
    assert rows["V-shapes"]["passed"] is True and rows["V-count"]["passed"] is False
    assert fake.requests[-1]["body"]["messages"][-1]["images"]


def test_run_arm_unreachable_stops(tmp_path: Path) -> None:
    with pytest.raises(EngineUnreachable):
        run_arm(arm("http://127.0.0.1:9"), [("A", 4096)], 1, tmp_path / "r.jsonl", facts_fn=dict)
    assert not (tmp_path / "r.jsonl").exists()


def test_measure_reraises_unreachable(fake: FakeEngine, tmp_path: Path) -> None:
    calls = {"n": 0}

    def dies(engine: Engine, messages: list[dict[str, Any]], max_tokens: int, ctx: int):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if "warmup" in messages[0]["content"]:
            return stream_chat(engine, messages, max_tokens, ctx)
        raise EngineUnreachable("gone")

    out = tmp_path / "r.jsonl"
    with pytest.raises(EngineUnreachable):
        run_arm(arm(fake.url), [("A", 4096)], 1, out, stream=dies, facts_fn=dict, log=lambda _: None)
    assert not out.exists() or out.read_text() == ""


def fixed_rates(rates: list[float]):  # type: ignore[no-untyped-def]
    calls: list[int] = []

    def stream(engine: Engine, messages: list[dict[str, Any]], max_tokens: int, ctx: int) -> Timing:
        rate = rates[min(len(calls), len(rates) - 1)]
        calls.append(max_tokens)
        return Timing(10, 101, 0.1, 100 / rate, 1.0, "x", 0, {})

    return stream, calls


def test_warm_up_until_stable() -> None:
    prompt = build("A", 4096)[0]
    stream, calls = fixed_rates([25.0, 80.0, 83.0, 83.0])
    assert warm_up(arm("http://unused"), prompt, stream) == (3, True)
    assert calls == [128, 128, 128]
    stream, calls = fixed_rates([10.0, 20.0, 40.0, 80.0, 160.0, 320.0])
    assert warm_up(arm("http://unused"), prompt, stream) == (5, False)


def test_exclusions_make_rows_run_again(fake: FakeEngine, tmp_path: Path) -> None:
    out = tmp_path / "laptop_ollama-x.jsonl"
    assert run_arm(arm(fake.url), [("A", 4096)], 2, out, facts_fn=dict, log=lambda _: None) == 0
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert rows[0]["warmup_runs"] >= 1 and "warmup_stable" in rows[0]
    first = rows[0]
    entry = {"file": out.name, "key": first["key"], "time": first["time"], "reason": "tuning"}
    (tmp_path / EXCLUSIONS).write_text(json.dumps(entry) + "\n")
    assert load_exclusions(tmp_path) == {(out.name, first["key"], first["time"]): "tuning"}
    assert done_keys(out) == {rows[1]["key"]}
    assert run_arm(arm(fake.url), [("A", 4096)], 2, out, facts_fn=dict, log=lambda _: None) == 0
    assert len(out.read_text().splitlines()) == 3
