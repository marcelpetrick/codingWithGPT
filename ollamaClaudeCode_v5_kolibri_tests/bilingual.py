#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check paired English and German arithmetic instructions on both models."""

import json
import os
from pathlib import Path
import re
import sys

import residency

RESULTS = Path(__file__).resolve().parent / "results" / "bilingual" / "results.jsonl"
MODELS = ("kolibri1:q3ks-ctx147456-nothink-ab", "qwen3.6:35b-a3b-q4_K_M-agentic")
TASKS = (
    (
        "en-multiply",
        "English",
        "What is 17 multiplied by 23? Reply with the number only.",
        "391",
    ),
    (
        "de-multiply",
        "German",
        "Wie viel ist 17 mal 23? Antworte nur mit der Zahl.",
        "391",
    ),
    ("en-add", "English", "What is 24 plus 19? Reply with the number only.", "43"),
    ("de-add", "German", "Wie viel ist 24 plus 19? Antworte nur mit der Zahl.", "43"),
    (
        "en-divide",
        "English",
        "What is 81 divided by 9? Reply with the number only.",
        "9",
    ),
    (
        "de-divide",
        "German",
        "Wie viel ist 81 geteilt durch 9? Antworte nur mit der Zahl.",
        "9",
    ),
)


def check_resident(model):
    models = residency.resident()
    if len(models) != 1 or models[0].get("name", "").lower() != model.lower():
        raise RuntimeError("Unexpected resident model")
    item = models[0]
    if not isinstance(item.get("size"), int) or not isinstance(
        item.get("size_vram"), int
    ):
        raise RuntimeError("Missing memory accounting")
    if item["size"] <= 0 or item["size_vram"] < item["size"]:
        raise RuntimeError("GPU spill")
    expected = 147456 if model.startswith("kolibri1:") else 262144
    if (
        not isinstance(item.get("context_length"), int)
        or item["context_length"] < expected
    ):
        raise RuntimeError("Unexpected context")


def score(answer, expected):
    return bool(re.fullmatch(r"\s*" + re.escape(expected) + r"[.!]?\s*", answer))


def main():
    version = residency.request("/api/version").get("version")
    if version != "0.40.11":
        raise RuntimeError("Server version changed")
    tags = residency.request("/api/tags").get("models")
    if not isinstance(tags, list):
        raise RuntimeError("Missing tag list")
    digests = {item.get("name", ""): item.get("digest") for item in tags}
    if any(not digests.get(model) for model in MODELS):
        raise RuntimeError("Model tag or digest missing")
    recorded = []
    if RESULTS.exists():
        with RESULTS.open(encoding="utf-8") as stream:
            recorded = [json.loads(line) for line in stream if line.strip()]
    valid_tasks = {task[0] for task in TASKS}
    seen = set()
    for row in recorded:
        key = (row.get("model"), row.get("task"))
        if (
            key in seen
            or key[0] not in MODELS
            or key[1] not in valid_tasks
            or row.get("ollama") != version
            or row.get("digest") != digests[key[0]]
            or not isinstance(row.get("pass"), bool)
        ):
            raise RuntimeError("Inconsistent existing bilingual results")
        seen.add(key)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        pending = [task for task in TASKS if (model, task[0]) not in seen]
        if not pending:
            continue
        residency.ensure_idle()
        for task_id, language, prompt, expected in pending:
            response = residency.request(
                "/api/chat",
                {
                    "model": model,
                    "stream": False,
                    "think": False,
                    "messages": [{"role": "user", "content": prompt}],
                    "options": {"temperature": 0, "seed": 42, "num_predict": 256},
                },
                timeout=1800,
            )
            answer = (response.get("message") or {}).get("content") or ""
            if (
                not response.get("done")
                or not answer.strip()
                or not response.get("prompt_eval_count")
            ):
                raise RuntimeError("Incomplete or empty response")
            check_resident(model)
            row = {
                "model": model,
                "task": task_id,
                "language": language,
                "prompt": prompt,
                "expected": expected,
                "answer": answer,
                "pass": score(answer, expected),
                "ollama": version,
                "digest": digests[model],
                "response": response,
            }
            with RESULTS.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            print(
                json.dumps(
                    {key: value for key, value in row.items() if key != "response"},
                    ensure_ascii=False,
                ),
                flush=True,
            )
        check_resident(model)
        residency.request(
            "/api/generate", {"model": model, "keep_alive": 0}, timeout=60
        )
        residency.ensure_idle()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        sys.exit(1)
