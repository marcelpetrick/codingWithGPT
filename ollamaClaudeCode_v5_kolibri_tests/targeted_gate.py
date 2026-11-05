#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run multi-turn and long-context tool probes with raw-response capture."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import urllib.request

import residency

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "targeted-gates.jsonl"
V4 = ROOT.parent / "ollamaClaudeCode_v4_tielCoder" / "gate-rerun.py"
MODELS = ("kolibri1:q3ks-ctx147456-nothink-ab", "qwen3.6:35b-a3b-q4_K_M-agentic")


def tool_definitions():
    spec = importlib.util.spec_from_file_location("v4_gate_definitions", V4)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TOOLS_MULTI


def post(model, tools, messages):
    body = {
        "model": model,
        "max_tokens": 4000,
        "temperature": 0,
        "thinking": {"type": "disabled"},
        "tools": tools,
        "messages": messages,
    }
    request = urllib.request.Request(
        residency.BASE + "/v1/messages",
        json.dumps(body).encode(),
        {
            "Content-Type": "application/json",
            "x-api-key": "ollama",
            "anthropic-version": "2023-06-01",
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=1200) as response:
        value = json.load(response)
    if not isinstance(value, dict) or value.get("error"):
        raise RuntimeError("Invalid API response")
    return value


def calls(response):
    content = response.get("content")
    if not isinstance(content, list) or not content:
        return None
    return [
        item
        for item in content
        if isinstance(item, dict) and item.get("type") == "tool_use"
    ]


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


def t3(model, tools):
    prompt = "Read /app/version.txt and tell me what version it contains."
    first = post(model, tools, [{"role": "user", "content": prompt}])
    first_calls = calls(first)
    if first_calls is None:
        return "INVALID", "empty first response", [first]
    if not first_calls:
        return "FAIL", "no tool call", [first]
    call = first_calls[0]
    if (
        first.get("stop_reason") != "tool_use"
        or call.get("name") != "read_file"
        or not isinstance(call.get("input"), dict)
        or call["input"].get("path") != "/app/version.txt"
        or not call.get("id")
    ):
        return "FAIL", "wrong first tool call", [first]
    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": first["content"]},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": "4.2.1-rc3",
                }
            ],
        },
    ]
    second = post(model, tools, messages)
    if calls(second) is None:
        return "INVALID", "empty second response", [first, second]
    text = " ".join(
        item.get("text", "")
        for item in second["content"]
        if isinstance(item, dict) and item.get("type") == "text"
    )
    return (
        ("PASS" if "4.2.1" in text else "FAIL"),
        "tool result response",
        [first, second],
    )


def t7(model, tools):
    excerpt = "".join(
        f"def helper_{i}(x): return x + {i}  # legacy shim\n" for i in range(2500)
    )
    prompt = (
        "Here is a large excerpt of our codebase:\n\n"
        + excerpt
        + '\n\nNow: write the string "done" to the file /tmp/final.txt using the available tool.'
    )
    response = post(model, tools, [{"role": "user", "content": prompt}])
    tool_calls = calls(response)
    usage = response.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    fresh = usage.get("input_tokens") or 0
    cached = usage.get("cache_read_input_tokens") or 0
    tokens = fresh + cached if isinstance(fresh, int) and isinstance(cached, int) else 0
    if tool_calls is None or tokens < 40000:
        return (
            "INVALID",
            f"empty response or insufficient prompt tokens: {tokens}",
            [response],
        )
    valid = response.get("stop_reason") == "tool_use" and any(
        call.get("name") == "write_file"
        and isinstance(call.get("input"), dict)
        and call["input"].get("path") == "/tmp/final.txt"
        and call["input"].get("content") == "done"
        for call in tool_calls
    )
    return ("PASS" if valid else "FAIL"), f"prompt tokens: {tokens}", [response]


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
    seen = set()
    if RESULTS.exists():
        with RESULTS.open(encoding="utf-8") as stream:
            recorded = [json.loads(line) for line in stream if line.strip()]
        for row in recorded:
            key = (row.get("model"), row.get("gate"), row.get("run"))
            if (
                key in seen
                or key[0] not in MODELS
                or key[1] not in ("T3", "T7")
                or key[2] not in (1, 2, 3)
                or row.get("ollama") != version
                or row.get("digest") != digests[key[0]]
                or row.get("verdict") not in ("PASS", "FAIL")
            ):
                raise RuntimeError("Existing results require review before restarting")
            seen.add(key)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    tools = tool_definitions()
    for model in MODELS:
        pending = [
            (gate, probe, run)
            for gate, probe in (("T3", t3), ("T7", t7))
            for run in range(1, 4)
            if (model, gate, run) not in seen
        ]
        if not pending:
            continue
        residency.ensure_idle()
        for gate, probe, run in pending:
            verdict, detail, responses = probe(model, tools)
            row = {
                "model": model,
                "gate": gate,
                "run": run,
                "verdict": verdict,
                "detail": detail,
                "ollama": version,
                "digest": digests[model],
                "responses": responses,
            }
            with RESULTS.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            print(model, gate, run, verdict, detail, flush=True)
            if verdict == "INVALID":
                raise RuntimeError("Invalid gate response; inspect raw data")
            check_resident(model)
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
