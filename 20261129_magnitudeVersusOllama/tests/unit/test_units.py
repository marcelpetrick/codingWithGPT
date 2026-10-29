# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests: decision rule, workloads, tasks checker, sysinfo, request building."""

from __future__ import annotations

import json
from collections.abc import Sequence

import pytest

from mvo import stats, tasks, workloads
from mvo.client import Engine, Timing, build_request
from mvo.sysinfo import git_commit, gpu_facts, run_text


def s(values: list[float]) -> stats.Summary:
    return stats.summarize(values)


def test_summarize_empty_and_values() -> None:
    assert stats.summarize([]) == stats.Summary(0, 0.0, 0.0, 0.0)
    assert stats.summarize([3, 1, 2]) == stats.Summary(3, 2, 1, 3)


def test_speed_verdict_rule() -> None:
    fast = s([130, 131, 132, 133, 134])
    slow = s([100, 101, 102, 103, 104])
    assert stats.speed_verdict(fast, slow) == "a faster"
    assert stats.speed_verdict(slow, fast) == "b faster"
    # 25% higher median but overlapping ranges -> tie.
    wide = s([90, 130, 131, 132, 133])
    assert stats.speed_verdict(wide, slow) == "tie"
    # Ranges apart but less than 25% -> tie.
    near = s([110, 111, 112, 113, 114])
    assert stats.speed_verdict(near, slow) == "tie"
    assert stats.speed_verdict(s([1, 2]), slow) == "too few runs"


def test_ratio_and_quality() -> None:
    assert stats.ratio(s([2.0]), s([1.0])) == 2.0
    assert stats.ratio(s([2.0]), s([])) == 0.0
    assert stats.quality_verdict(15, 12) == "a better"
    assert stats.quality_verdict(12, 15) == "b better"
    assert stats.quality_verdict(14, 12) == "tie"


def test_passages_and_workload_a() -> None:
    text = workloads.moby_dick_text()
    paras = workloads.passages(text)
    assert len(paras) > 100
    assert all(len(p) >= 200 for p in paras)
    prompt = workloads.workload_a(4096)
    user = prompt.messages[1][1]
    assert "Call me Ishmael" in user
    last = user.rsplit("[Passage ", 1)[1].split("]")[0]
    assert f"Repeat Passage {last} exactly" in user
    assert len(user) < 4096 * workloads.CHARS_PER_TOKEN
    bigger = workloads.workload_a(16384)
    assert len(bigger.messages[1][1]) > 3 * len(user)
    with pytest.raises(ValueError):
        workloads.workload_a(300)


def test_workload_b_and_context() -> None:
    small = workloads.workload_b(1024)
    assert [p.prompt_id for p in small][0] == "B-lru-ttl-1024"
    assert all("existing module" not in p.messages[1][1] for p in small)
    big = workloads.workload_b(8192)
    assert all("existing module" in p.messages[1][1] for p in big)
    assert workloads.synthetic_code(5000) == workloads.synthetic_code(5000)
    assert len(workloads.synthetic_code(5000)) >= 5000


def test_workload_c_and_build() -> None:
    assert len(workloads.workload_c()) == 20
    assert len(workloads.build("A", 4096)) == 1
    assert len(workloads.build("B", 1024)) == 5
    assert len(workloads.build("C", 4096)) == 20
    with pytest.raises(ValueError):
        workloads.build("Z", 1)


def test_nonce_goes_into_first_line() -> None:
    prompt = workloads.workload_c()[0]
    messages = prompt.as_messages("abc")
    assert messages[0]["content"].startswith("Request abc.\n")
    assert messages[1]["role"] == "user"


def test_tasks_count_and_reference_solutions_pass() -> None:
    assert len(tasks.TASKS) == 20
    assert len(tasks.TASK_BY_ID) == 20
    good = "```python\ndef is_palindrome(s):\n    t=[c.lower() for c in s if c.isalnum()]\n    return t==t[::-1]\n```"
    assert tasks.check("is-palindrome", good)
    assert not tasks.check("is-palindrome", "def is_palindrome(s):\n    return False\n")
    assert not tasks.check("is-palindrome", "while True:\n    pass\n", timeout_s=0.5)


def test_extract_code() -> None:
    assert tasks.extract_code("x\n```py\na = 1\n```\n") == "a = 1\n"
    assert tasks.extract_code("a = 1") == "a = 1"


def test_build_request_ollama_and_openai() -> None:
    oll = Engine("ollama", "ollama", "http://h:1/", "m", extra={"keep_alive": "5m"})
    req = build_request(oll, [{"role": "user", "content": "x"}], 10, 4096)
    body = json.loads(req.data)  # type: ignore[arg-type]
    assert req.full_url == "http://h:1/api/chat"
    assert body["think"] is False and body["options"]["num_ctx"] == 4096
    assert body["options"]["presence_penalty"] == 0 and body["keep_alive"] == "5m"
    oai = Engine("magnitude", "openai", "http://h:2/v1", "m", api_key="k")
    req = build_request(oai, [], 10, 4096)
    body = json.loads(req.data)  # type: ignore[arg-type]
    assert req.full_url == "http://h:2/v1/chat/completions"
    assert body["stream_options"] == {"include_usage": True} and body["max_tokens"] == 10
    assert req.get_header("Authorization") == "Bearer k"
    with pytest.raises(ValueError):
        build_request(Engine("x", "grpc", "u", "m"), [], 1, 1)


def test_timing_rates() -> None:
    t = Timing(100, 11, 0.5, 2.0, 2.6, "x", 0, {})
    assert t.prefill_tps == 200 and t.decode_tps == 5
    zero = Timing(100, 1, 0.0, 0.0, 0.0, "x", 0, {})
    assert zero.prefill_tps == 0 and zero.decode_tps == 0


def test_gpu_facts_and_git() -> None:
    def runner(cmd: Sequence[str]) -> str:
        return "NVIDIA A2000, 610.57, 300, 8192"

    facts = gpu_facts(runner)
    assert facts == {"gpu": "NVIDIA A2000", "driver": "610.57", "vram_used_mib": 300, "vram_total_mib": 8192}
    assert gpu_facts(lambda cmd: "")["vram_used_mib"] == -1
    assert git_commit(lambda cmd: "abc" if "rev-parse" in cmd else "") == "abc"
    assert git_commit(lambda cmd: "abc" if "rev-parse" in cmd else " M src/x.py") == "abc+dirty"


def test_run_text() -> None:
    assert run_text(["sh", "-c", "echo hi"]) == "hi"
    assert run_text(["sh", "-c", "exit 3"]) == ""
    assert run_text(["/nonexistent/binary"]) == ""
