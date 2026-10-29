# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run one arm over workload cells and append one JSON row per request.

The runner is idempotent: a row key that is already in the result file is skipped, so a
re-run resumes. A failed request is written as a failed row. An unreachable engine stops
the run (exit code 2) and writes nothing for that request.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mvo import tasks
from mvo.client import Engine, EngineError, EngineUnreachable, Timing, stream_chat
from mvo.sysinfo import gpu_facts
from mvo.workloads import Prompt, build

StreamFn = Callable[[Engine, list[dict[str, str]], int, int], Timing]


@dataclass(frozen=True)
class Arm:
    """One labelled configuration. Arms never pool in the report."""

    label: str
    engine: Engine
    engine_version: str
    drafter: str
    quant: str
    site: str


def row_key(arm: str, prompt_id: str, rep: int) -> str:
    """Return the unique key of one measured request."""
    return f"{arm}|{prompt_id}|{rep}"


def done_keys(path: Path) -> set[str]:
    """Return the keys of all rows in the file that are not failed rows."""
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("ok"):
                keys.add(row["key"])
    return keys


def measure(
    arm: Arm,
    prompt: Prompt,
    rep: int,
    stream: StreamFn,
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Run one request and return its result row (ok or failed)."""
    nonce = f"{arm.label}-{prompt.prompt_id}-{rep}"
    row: dict[str, Any] = {
        "key": row_key(arm.label, prompt.prompt_id, rep),
        "arm": arm.label,
        "engine": arm.engine.name,
        "engine_version": arm.engine_version,
        "model": arm.engine.model,
        "quant": arm.quant,
        "drafter": arm.drafter,
        "site": arm.site,
        "workload": prompt.workload,
        "prompt_id": prompt.prompt_id,
        "ctx": prompt.ctx,
        "max_tokens": prompt.max_tokens,
        "rep": rep,
        "time": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        **facts,
    }
    try:
        timing = stream(arm.engine, prompt.as_messages(nonce), prompt.max_tokens, prompt.ctx)
    except EngineUnreachable:
        raise
    except EngineError as error:
        return {**row, "ok": False, "error": str(error)[:500]}
    row.update(
        ok=True,
        prompt_tokens=timing.prompt_tokens,
        completion_tokens=timing.completion_tokens,
        ttft_s=round(timing.ttft_s, 4),
        decode_s=round(timing.decode_s, 4),
        total_s=round(timing.total_s, 4),
        prefill_tps=round(timing.prefill_tps, 2),
        decode_tps=round(timing.decode_tps, 2),
        reasoning_chars=timing.reasoning_chars,
        engine_counters=timing.engine_counters,
        answer=timing.text,
    )
    if prompt.workload == "C":
        row["passed"] = tasks.check(prompt.prompt_id.removeprefix("C-"), timing.text)
    if timing.reasoning_chars:
        row.update(ok=False, error="thinking was not off (reasoning tokens in the stream)")
    return row


def run_arm(
    arm: Arm,
    cells: Iterable[tuple[str, int]],
    reps: int,
    out: Path,
    stream: StreamFn = stream_chat,
    facts_fn: Callable[[], dict[str, Any]] = gpu_facts,
    commit: str = "",
    log: Callable[[str], None] = print,
) -> int:
    """Measure every (workload, ctx) cell: one warm-up, then ``reps`` rows. Return failed rows."""
    out.parent.mkdir(parents=True, exist_ok=True)
    done = done_keys(out)
    failed = 0
    for workload, ctx in cells:
        prompts = build(workload, ctx)
        todo = [(p, r) for p in prompts for r in range(reps) if row_key(arm.label, p.prompt_id, r) not in done]
        if not todo:
            log(f"skip {arm.label} {workload}/{ctx}: all rows present")
            continue
        warm = prompts[0]
        stream(arm.engine, warm.as_messages(f"warmup-{arm.label}-{warm.prompt_id}"), 16, warm.ctx)
        for prompt, rep in todo:
            row = measure(arm, prompt, rep, stream, {**facts_fn(), "commit": commit})
            with out.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            if not row["ok"]:
                failed += 1
            status = f"{row.get('decode_tps', '-')} tok/s" if row["ok"] else f"FAILED {row['error']}"
            log(f"{arm.label} {prompt.prompt_id} rep {rep}: {status}")
    return failed
