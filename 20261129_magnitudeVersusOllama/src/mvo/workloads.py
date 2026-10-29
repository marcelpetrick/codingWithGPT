# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""The prompts of workloads A (vendor replication), B (realistic coding) and C (quality).

Every prompt is built deterministically from fixed data, so both engines get the same bytes.
The only per-request change is a nonce in the first line. It makes each request miss the
prefix cache, as in the vendor method ("fresh process, empty prompt cache").
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mvo import vision
from mvo.tasks import TASKS

CHARS_PER_TOKEN = 3.8  # English prose and Python, Qwen tokenizer; checked against prompt_tokens.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Prompt:
    """One prompt of a workload."""

    workload: str
    prompt_id: str
    ctx: int
    max_tokens: int
    messages: tuple[tuple[str, str], ...]
    image_b64: str = ""

    def as_messages(self, nonce: str) -> list[dict[str, Any]]:
        """Return the chat messages with the nonce in the first line of the system message.

        An image goes on the last (user) message as ``images: [base64 PNG]``.
        """
        out: list[dict[str, Any]] = [{"role": role, "content": content} for role, content in self.messages]
        out[0] = {"role": "system", "content": f"Request {nonce}.\n" + out[0]["content"]}
        if self.image_b64:
            out[-1]["images"] = [self.image_b64]
        return out


def moby_dick_text(data_dir: Path = DATA_DIR) -> str:
    """Return the fixed Moby-Dick excerpt (public domain)."""
    return (data_dir / "moby_dick_ch01-19.txt").read_text(encoding="utf-8")


def passages(text: str) -> list[str]:
    """Split the text into paragraphs of 200 characters or more (the 'passages')."""
    body = text.split("\n\n", 2)[-1]
    paras = [" ".join(p.split()) for p in body.split("\n\n")]
    return [p for p in paras if len(p) >= 200]


def workload_a(ctx: int, data_dir: Path = DATA_DIR, max_tokens: int = 256) -> Prompt:
    """Vendor replication: numbered passages, then 'repeat the latest passage'."""
    budget = int((ctx - max_tokens - 200) * CHARS_PER_TOKEN)
    chosen: list[str] = []
    used = 0
    for number, para in enumerate(passages(moby_dick_text(data_dir)), start=1):
        block = f"[Passage {number}]\n{para}"
        if used + len(block) > budget:
            break
        chosen.append(block)
        used += len(block) + 2
    if not chosen:
        raise ValueError(f"context {ctx} is too small for workload A")
    last = len(chosen)
    user = "\n\n".join(chosen) + f"\n\nRepeat Passage {last} exactly, word for word. Output only the passage text."
    system = "You are a careful assistant. Follow the instruction exactly."
    return Prompt("A", f"A-moby-{ctx}", ctx, max_tokens, (("system", system), ("user", user)))


CODING_TASKS: tuple[tuple[str, str], ...] = (
    (
        "lru-ttl",
        "Write a Python class TTLCache with get(key), put(key, value) and a max size. "
        "Entries expire after ttl seconds; the least recently used entry is evicted first. "
        "Use only the standard library. Add type hints and docstrings.",
    ),
    (
        "csv-report",
        "Write a Python command-line script that reads a CSV file of orders "
        "(columns: date, customer, product, quantity, unit_price) and prints, per month, the "
        "revenue, the number of distinct customers and the top three products. Use argparse "
        "and the csv module.",
    ),
    (
        "rate-limiter",
        "Write a thread-safe token-bucket rate limiter in Python with acquire(tokens=1, "
        "timeout=None) -> bool. Explain the design in short comments.",
    ),
    (
        "graph-paths",
        "Write a Python function that returns all shortest paths between two nodes in an "
        "unweighted directed graph given as a dict of adjacency lists. Include three pytest tests.",
    ),
    (
        "log-parser",
        "Write a Python generator that parses nginx access log lines into dataclass records "
        "and skips malformed lines, and a function that returns the ten slowest endpoints.",
    ),
)


def synthetic_code(approx_chars: int, seed: int = 20261029) -> str:
    """Return a deterministic Python module of about ``approx_chars`` characters."""
    rng = random.Random(seed)
    verbs = ["load", "parse", "merge", "score", "filter", "render", "store", "check"]
    nouns = ["order", "invoice", "customer", "ticket", "sensor", "route", "batch", "report"]
    chunks = ['"""Inventory service helpers (fixture for the benchmark context)."""\n']
    index = 0
    while sum(len(c) for c in chunks) < approx_chars:
        verb, noun = rng.choice(verbs), rng.choice(nouns)
        limit = rng.randint(2, 99)
        chunks.append(
            f"\n\ndef {verb}_{noun}_{index}(items: list[dict], limit: int = {limit}) -> list[dict]:\n"
            f'    """{verb.capitalize()} {noun} records and keep at most {limit} of them."""\n'
            f"    result = []\n"
            f"    for item in items:\n"
            f'        if item.get("{noun}_id") is None:\n'
            f"            continue\n"
            f'        item = {{**item, "stage": "{verb}"}}\n'
            f"        result.append(item)\n"
            f"        if len(result) >= limit:\n"
            f"            break\n"
            f"    return result\n"
        )
        index += 1
    return "".join(chunks)


def workload_b(ctx: int, max_tokens: int = 512) -> list[Prompt]:
    """Realistic coding: write new code. ctx <= 2048 means no extra context."""
    system = "You are a senior Python developer. Answer with code first, then a short note."
    context = ""
    if ctx > 2048:
        code = synthetic_code(int((ctx - max_tokens - 600) * CHARS_PER_TOKEN))
        context = f"This is the existing module of the project:\n\n```python\n{code}\n```\n\n"
    prompts = []
    for task_id, task in CODING_TASKS:
        user = context + task
        prompts.append(Prompt("B", f"B-{task_id}-{ctx}", ctx, max_tokens, (("system", system), ("user", user))))
    return prompts


def workload_c(max_tokens: int = 768) -> list[Prompt]:
    """Quality: the 20 small tasks of mvo.tasks, each checked by unit tests."""
    system = (
        "You are a Python expert. Answer with exactly one ```python code block that defines the "
        "requested function. No explanation."
    )
    return [
        Prompt("C", f"C-{task.task_id}", 4096, max_tokens, (("system", system), ("user", task.prompt)))
        for task in TASKS
    ]


def workload_v(max_tokens: int = 96) -> list[Prompt]:
    """Vision: five generated images with known answers (is the capability kept?)."""
    system = "You are a careful assistant. Look at the image and answer briefly."
    return [
        Prompt("V", f"V-{t.task_id}", 4096, max_tokens, (("system", system), ("user", t.question)), t.b64)
        for t in vision.TASKS
    ]


def build(workload: str, ctx: int) -> list[Prompt]:
    """Return the prompts of one workload cell."""
    if workload == "A":
        return [workload_a(ctx)]
    if workload == "B":
        return workload_b(ctx)
    if workload == "C":
        return workload_c()
    if workload == "V":
        return workload_v()
    raise ValueError(f"unknown workload: {workload}")
