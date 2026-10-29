# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Streaming chat client that times one request on the client side.

Two wire protocols are supported, so each engine uses its own native settings path:

- ``openai``: ``POST {base}/chat/completions`` with server-sent events (Magnitude).
- ``ollama``: ``POST {base}/api/chat`` with JSON lines (Ollama; it accepts ``num_ctx`` and ``think``).

The verdict uses the client-side numbers only. Engine counters are kept as extra fields.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

Clock = Callable[[], float]


class EngineError(RuntimeError):
    """The engine answered with an error, an empty answer, or no token counts."""


class EngineUnreachable(EngineError):
    """The engine did not accept the connection. A job must stop on this, never book it."""


@dataclass(frozen=True)
class Engine:
    """One engine endpoint and the request settings that make it comparable."""

    name: str
    protocol: str  # "openai" or "ollama"
    base_url: str
    model: str
    api_key: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Timing:
    """Client-side timing and token counts of one streamed request."""

    prompt_tokens: int
    completion_tokens: int
    ttft_s: float
    decode_s: float
    total_s: float
    text: str
    reasoning_chars: int
    engine_counters: dict[str, Any]

    @property
    def prefill_tps(self) -> float:
        """Prompt tokens per second up to the first visible token (includes HTTP overhead)."""
        return self.prompt_tokens / self.ttft_s if self.ttft_s > 0 else 0.0

    @property
    def decode_tps(self) -> float:
        """Generated tokens after the first one, per second of streaming."""
        if self.completion_tokens < 2 or self.decode_s <= 0:
            return 0.0
        return (self.completion_tokens - 1) / self.decode_s


def build_request(
    engine: Engine, messages: list[dict[str, str]], max_tokens: int, num_ctx: int
) -> urllib.request.Request:
    """Build the HTTP request: greedy sampler, no penalties, thinking off, fixed seed."""
    if engine.protocol == "ollama":
        body: dict[str, Any] = {
            "model": engine.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {
                "temperature": 0,
                "top_k": 1,
                "top_p": 1,
                "presence_penalty": 0,
                "repeat_penalty": 1,
                "seed": 0,
                "num_predict": max_tokens,
                "num_ctx": num_ctx,
            },
        }
        url = engine.base_url.rstrip("/") + "/api/chat"
    elif engine.protocol == "openai":
        body = {
            "model": engine.model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": 0,
            "top_p": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "seed": 0,
            "max_tokens": max_tokens,
        }
        url = engine.base_url.rstrip("/") + "/chat/completions"
    else:
        raise ValueError(f"unknown protocol: {engine.protocol}")
    body.update(engine.extra)
    headers = {"Content-Type": "application/json"}
    if engine.api_key:
        headers["Authorization"] = f"Bearer {engine.api_key}"
    return urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)


def _events(protocol: str, lines: Iterator[bytes]) -> Iterator[dict[str, Any]]:
    """Yield the JSON objects of the stream. SSE lines start with ``data:``."""
    for raw in lines:
        line = raw.decode("utf-8").strip()
        if not line:
            continue
        if protocol == "openai":
            if not line.startswith("data:"):
                continue
            line = line[5:].strip()
            if line == "[DONE]":
                return
        yield json.loads(line)


def stream_chat(
    engine: Engine,
    messages: list[dict[str, str]],
    max_tokens: int,
    num_ctx: int,
    timeout_s: float = 600.0,
    clock: Clock = time.perf_counter,
) -> Timing:
    """Send one streamed request and time it. Raise EngineError on any defect."""
    request = build_request(engine, messages, max_tokens, num_ctx)
    start = clock()
    try:
        response = urllib.request.urlopen(request, timeout=timeout_s)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise EngineError(f"HTTP {error.code}: {detail}") from error
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        raise EngineUnreachable(f"{engine.name}: {error}") from error

    first: float | None = None
    last = start
    parts: list[str] = []
    reasoning = 0
    prompt_tokens = completion_tokens = -1
    counters: dict[str, Any] = {}
    with response:
        for event in _events(engine.protocol, iter(response.readline, b"")):
            if "error" in event:
                raise EngineError(f"stream error: {event['error']}")
            if engine.protocol == "ollama":
                message = event.get("message") or {}
                content = message.get("content") or ""
                reasoning += len(message.get("thinking") or "")
                if event.get("done"):
                    prompt_tokens = int(event.get("prompt_eval_count", -1))
                    completion_tokens = int(event.get("eval_count", -1))
                    counters = {
                        k: event[k] for k in ("prompt_eval_duration", "eval_duration", "load_duration") if k in event
                    }
            else:
                content = ""
                for choice in event.get("choices") or []:
                    delta = choice.get("delta") or {}
                    content += delta.get("content") or ""
                    reasoning += len(delta.get("reasoning_content") or delta.get("reasoning") or "")
                usage = event.get("usage")
                if usage:
                    prompt_tokens = int(usage.get("prompt_tokens", -1))
                    completion_tokens = int(usage.get("completion_tokens", -1))
                    counters = {k: v for k, v in usage.items() if k not in ("prompt_tokens",)}
                    for key in ("timings", "metrics"):
                        if key in event:
                            counters[key] = event[key]
            if content:
                now = clock()
                if first is None:
                    first = now
                last = now
                parts.append(content)
    end = clock()
    if first is None:
        raise EngineError("empty answer: no content tokens")
    if prompt_tokens < 0 or completion_tokens < 0:
        raise EngineError("no token counts in the stream (usage missing)")
    return Timing(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        ttft_s=first - start,
        decode_s=last - first,
        total_s=end - start,
        text="".join(parts),
        reasoning_chars=reasoning,
        engine_counters=counters,
    )


def unload_ollama(base_url: str, model: str, timeout_s: float = 60.0) -> None:
    """Unload an Ollama model now (``keep_alive: 0``), so the other engine gets the VRAM."""
    body = json.dumps({"model": model, "keep_alive": 0}).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        response.read()
