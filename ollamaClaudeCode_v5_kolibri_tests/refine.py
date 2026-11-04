#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Refine the residency boundary in 1,024-token steps after the ladder."""
import json
import os
from pathlib import Path
import sys

import residency

RESULTS = Path(__file__).resolve().parent / "results" / "refinement.jsonl"
STEP = 1024


def read_rows(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main():
    version = residency.request("/api/version").get("version")
    if version != "0.40.11":
        raise RuntimeError("Server version changed")
    residency.ensure_idle()
    tags = residency.request("/api/tags").get("models")
    if not isinstance(tags, list):
        raise RuntimeError("Missing tag list")
    matching = [tag for tag in tags if residency.is_ours(tag)]
    if len(matching) != 1 or not matching[0].get("digest"):
        raise RuntimeError("Model tag or digest missing")
    digest = matching[0]["digest"]
    ladder = read_rows(residency.RESULTS)
    if not ladder:
        raise RuntimeError("The residency ladder has no results")
    for index, row in enumerate(ladder):
        if (index >= len(residency.CONTEXTS) or row.get("context") != residency.CONTEXTS[index]
                or row.get("digest") != digest or row.get("ollama") != version
                or not isinstance(row.get("full_gpu"), bool)
                or (index < len(ladder) - 1 and not row["full_gpu"])):
            raise RuntimeError("The residency ladder is inconsistent")
    if ladder[-1]["full_gpu"]:
        if ladder[-1]["context"] != residency.CONTEXTS[-1]:
            raise RuntimeError("The residency ladder did not finish")
        print("Native context ceiling fits; no refinement needed.")
        return
    extra = read_rows(RESULTS)
    rows = ladder[:]
    for row in extra:
        if (row.get("digest") != digest or row.get("ollama") != version
                or not isinstance(row.get("full_gpu"), bool)
                or row.get("context") != next_context(rows)):
            raise RuntimeError("The refinement results are inconsistent")
        rows.append(row)
    while (ctx := next_context(rows)) is not None:
        result = residency.run_one(ctx, version, digest)
        RESULTS.parent.mkdir(exist_ok=True)
        with RESULTS.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps(result, ensure_ascii=False), flush=True)
        rows.append(result)
        residency.unload_ours()
    print("Refinement complete.", flush=True)


def next_context(rows):
    full = [row["context"] for row in rows if row["full_gpu"]]
    spilled = [row["context"] for row in rows if not row["full_gpu"]]
    if not spilled:
        return None
    if not full:
        return 2048 if all(row["context"] != 2048 for row in rows) else None
    low = max(full)
    high = min((ctx for ctx in spilled if ctx > low), default=None)
    if high is None or high - low <= STEP:
        return None
    return ((low + high) // (2 * STEP)) * STEP


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        sys.exit(1)
