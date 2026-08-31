#!/usr/bin/env python3
"""Reproducible Ollama vision/OCR benchmark for qwen3-vl:32b."""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = [
    {
        "name": "ocr-invoice",
        "image": ROOT / "fixtures/ocr-invoice.png",
        "prompt": (
            "Perform OCR on this invoice. Transcribe every visible line exactly, preserving "
            "numbers, punctuation, and item order. Return only the transcription."
        ),
        "must_include": [
            "R-2026-0831", "31 August 2026", "Ada Lovelace Labs",
            "Vision benchmark", "EUR 1,278.50", "EUR 242.92",
            "EUR 1,521.42", "VISION-7Q4K-92", "14 days",
        ],
    },
    {
        "name": "embedded-ui",
        "image": ROOT / "fixtures/embedded-ui.png",
        "prompt": (
            "Describe the visible application UI precisely. Include the window title, main "
            "heading, all three button labels and colors, status text, and slider position."
        ),
        "must_include": [
            "LVGL Simulator", "LVGL - Embedded UI Demo", "Accept", "Cancel", "Config",
            "total clicks: 8",
        ],
    },
    {
        "name": "expenses-treemap",
        "image": ROOT / "fixtures/expenses-treemap.png",
        "prompt": (
            "Describe this chart and transcribe every category and euro value. State which "
            "category is largest and explain what rectangle area represents."
        ),
        "must_include": ["Rent", "1200", "Food", "1000", "Kids", "900", "Car", "200", "Clothes", "100"],
    },
]


def post_json(url: str, payload: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def get_json(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("OLLAMA_VISION_HOST", "http://127.0.0.1:11434"))
    parser.add_argument("--model", default="qwen3-vl:32b")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--num-predict", type=int, default=1024)
    parser.add_argument(
        "--case",
        action="append",
        choices=[case["name"] for case in CASES],
        help="run only this case; repeat for multiple cases",
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="allow Qwen thinking; by default /no_think is added because Ollama 0.32.15 ignores think:false for this tag",
    )
    args = parser.parse_args()
    host = args.host.rstrip("/")

    missing = [str(case["image"]) for case in CASES if not case["image"].is_file()]
    if missing:
        raise SystemExit("missing fixture(s): " + ", ".join(missing))

    version = get_json(host + "/api/version", 15).get("version", "unknown")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    out_dir = ROOT / "results" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "timestamp_utc": stamp,
        "host": host,
        "ollama_version": version,
        "model": args.model,
        "settings": {
            "think": args.thinking,
            "no_think_directive": not args.thinking,
            "temperature": 0,
            "seed": 42,
            "num_predict": args.num_predict,
        },
        "cases": [],
    }

    print(f"Ollama {version} at {host}; model={args.model}")
    selected_cases = [case for case in CASES if not args.case or case["name"] in args.case]
    for case in selected_cases:
        image_b64 = base64.b64encode(case["image"].read_bytes()).decode()
        payload = {
            "model": args.model,
            "stream": False,
            "think": args.thinking,
            "keep_alive": "30m",
            "options": {"temperature": 0, "seed": 42, "num_predict": args.num_predict},
            "messages": [{
                "role": "user",
                "content": case["prompt"] if args.thinking else "/no_think\n" + case["prompt"],
                "images": [image_b64],
            }],
        }
        started = time.monotonic()
        response = post_json(host + "/api/chat", payload, args.timeout)
        wall_s = time.monotonic() - started
        if response.get("error"):
            raise RuntimeError(f"{case['name']}: {response['error']}")
        answer = (response.get("message") or {}).get("content", "")
        folded = answer.casefold()
        checks = {needle: needle.casefold() in folded for needle in case["must_include"]}
        matched = sum(checks.values())
        eval_count = response.get("eval_count", 0)
        eval_duration = response.get("eval_duration", 0)
        prompt_count = response.get("prompt_eval_count", 0)
        prompt_duration = response.get("prompt_eval_duration", 0)
        result = {
            "name": case["name"],
            "image": str(case["image"].relative_to(ROOT)),
            "prompt": case["prompt"],
            "answer": answer,
            "checks": checks,
            "matched": matched,
            "possible": len(checks),
            "wall_s": round(wall_s, 3),
            "load_s": round(response.get("load_duration", 0) / 1e9, 3),
            "prompt_tokens": prompt_count,
            "prefill_tps": round(prompt_count / (prompt_duration / 1e9), 2) if prompt_duration else None,
            "generated_tokens": eval_count,
            "generation_tps": round(eval_count / (eval_duration / 1e9), 2) if eval_duration else None,
            "done_reason": response.get("done_reason"),
        }
        summary["cases"].append(result)
        (out_dir / f"{case['name']}.json").write_text(json.dumps(response, indent=2) + "\n")
        (out_dir / f"{case['name']}.txt").write_text(answer.rstrip() + "\n")
        print(
            f"{case['name']:18} checks={matched}/{len(checks)} wall={wall_s:.1f}s "
            f"prompt={prompt_count} gen={eval_count} gen_tps={result['generation_tps']}"
        )

    ps = get_json(host + "/api/ps", 15).get("models", [])
    resident = next((m for m in ps if m.get("name") == args.model), None)
    summary["resident"] = resident
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"results: {out_dir}")
    if resident:
        print(f"resident VRAM: {resident.get('size_vram', 0) / 1e9:.2f} GB / {resident.get('size', 0) / 1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
