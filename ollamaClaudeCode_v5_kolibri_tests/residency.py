#!/usr/bin/env python3
# Copyright (C) 2026 Marcel Petrick
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure a Kolibri context ladder on the existing, idle Ollama server."""

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

BASE = "http://192.168.100.67:11434"
MODEL = "hf.co/Eliasfpv28/Kolibri-1-Q3_K_S-GGUF:Q3_K_S"
CONTEXTS = (4096, 8192, 16384, 32768, 65536, 131072, 262144)
RESULTS = Path(__file__).resolve().parent / "results" / "residency.jsonl"


def request(path, data=None, timeout=30):
    payload = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path, data=payload, headers={"Content-Type": "application/json"}
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as response:
        return json.load(response)


def is_ours(model):
    return model.get("name", "").lower() == MODEL.lower()


def resident():
    data = request("/api/ps")
    if not isinstance(data.get("models"), list):
        raise RuntimeError("Missing resident model list")
    return data["models"]


def ensure_idle():
    if resident():
        raise RuntimeError("Server is busy; no model was unloaded")


def unload_ours():
    models = resident()
    if not models:
        return
    if len(models) != 1 or not is_ours(models[0]):
        raise RuntimeError("Server state changed; refusing to unload")
    request("/api/generate", {"model": MODEL, "keep_alive": 0}, timeout=60)
    ensure_idle()


def run_one(ctx, version, digest):
    ensure_idle()
    start = time.monotonic()
    response = request(
        "/api/generate",
        {
            "model": MODEL,
            "prompt": "What is 17 multiplied by 23? Answer briefly.",
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {
                "num_ctx": ctx,
                "num_predict": 128,
                "temperature": 0,
                "seed": 42,
            },
        },
        timeout=1800,
    )
    elapsed = time.monotonic() - start
    if (
        not response.get("done")
        or not response.get("response", "").strip()
        or not response.get("prompt_eval_count")
    ):
        raise RuntimeError("Incomplete or empty response")
    models = resident()
    if len(models) != 1 or not is_ours(models[0]):
        raise RuntimeError("Unexpected resident model state")
    model = models[0]
    size, vram = model.get("size"), model.get("size_vram")
    if not isinstance(size, int) or not isinstance(vram, int) or size <= 0 or vram <= 0:
        raise RuntimeError("Missing memory accounting")
    actual_context = model.get("context_length")
    if not isinstance(actual_context, int) or actual_context < ctx:
        raise RuntimeError(f"Requested context {ctx}, server reported {actual_context}")
    return {
        "context": ctx,
        "actual_context": actual_context,
        "size": size,
        "size_vram": vram,
        "full_gpu": vram >= size,
        "response": response["response"],
        "prompt_eval_count": response["prompt_eval_count"],
        "eval_count": response.get("eval_count"),
        "eval_duration_ns": response.get("eval_duration"),
        "elapsed_seconds": round(elapsed, 2),
        "ollama": version,
        "digest": digest,
    }


def main():
    version = request("/api/version").get("version")
    if version != "0.40.11":
        raise RuntimeError(f"Unexpected server version: {version}")
    ensure_idle()
    tags = request("/api/tags").get("models")
    if not isinstance(tags, list):
        raise RuntimeError("Missing tag list")
    candidates = [item for item in tags if is_ours(item)]
    if len(candidates) != 1 or not candidates[0].get("digest"):
        raise RuntimeError("Model is missing or has no digest")
    RESULTS.parent.mkdir(exist_ok=True)
    completed = []
    if RESULTS.exists():
        with RESULTS.open(encoding="utf-8") as existing:
            completed = [json.loads(line) for line in existing if line.strip()]
        for index, row in enumerate(completed):
            if (
                index >= len(CONTEXTS)
                or row.get("context") != CONTEXTS[index]
                or row.get("ollama") != version
                or row.get("digest") != candidates[0]["digest"]
                or not isinstance(row.get("full_gpu"), bool)
                or (index < len(completed) - 1 and not row["full_gpu"])
            ):
                raise RuntimeError("Existing results do not match this run")
        if completed and not completed[-1]["full_gpu"]:
            return
    for ctx in CONTEXTS[len(completed) :]:
        try:
            result = run_one(ctx, version, candidates[0]["digest"])
            with RESULTS.open("a", encoding="utf-8") as output:
                output.write(json.dumps(result, ensure_ascii=False) + "\n")
                output.flush()
                os.fsync(output.fileno())
            print(json.dumps(result, ensure_ascii=False), flush=True)
            unload_ours()
            if not result["full_gpu"]:
                break
        except Exception:
            # Leave the model alone if state is ambiguous. No failed run is a result.
            raise


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        sys.exit(1)
