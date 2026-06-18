#!/usr/bin/env python3
"""
Ollama Image Generation — text prompt → PNG saved locally.

Uses the OpenAI-compatible /v1/images/generations endpoint exposed by Ollama.
Requires an image-generation model pulled on the Ollama server (e.g. x/flux2-klein).

Usage:
    python generate_image.py "a red cat on a whiteboard"
    python generate_image.py "cyberpunk cityscape at night" --model x/z-image-turbo --size 1024x1024
    python generate_image.py "portrait" --out ./my_images
"""

import argparse
import base64
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests not installed — run: pip install requests")


OLLAMA_HOST = "http://192.168.100.37:11434"
DEFAULT_MODEL = "x/flux2-klein"
DEFAULT_SIZE = "1024x1024"
DEFAULT_OUT = Path(__file__).parent / "output"


def check_model_available(host: str, model: str) -> bool:
    try:
        resp = requests.get(f"{host}/api/tags", timeout=10)
        resp.raise_for_status()
        names = [m["name"] for m in resp.json().get("models", [])]
        # normalize: treat "x/foo" and "x/foo:latest" as the same
        normalized = {n.split(":")[0]: n for n in names}
        return model in names or model in normalized or model.split(":")[0] in normalized
    except Exception:
        return False


def pull_model(host: str, model: str) -> None:
    print(f"Pulling model {model!r} on server (this may take several minutes)…")
    url = f"{host}/api/pull"
    with requests.post(url, json={"name": model, "stream": True}, stream=True, timeout=1800) as resp:
        resp.raise_for_status()
        last_pct = -1
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            status = data.get("status", "")
            total = data.get("total", 0)
            completed = data.get("completed", 0)
            if total and "pulling" in status:
                pct = int(completed / total * 100)
                if pct != last_pct and pct % 5 == 0:
                    bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                    print(f"\r  [{bar}] {pct:3d}%  {completed/1e9:.1f}/{total/1e9:.1f} GB", end="", flush=True)
                    last_pct = pct
            elif status == "success":
                print()
                break
    print(f"Model {model!r} ready.")


def generate_image(
    prompt: str,
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    host: str = OLLAMA_HOST,
    out_dir: Path = DEFAULT_OUT,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    # OpenAI-compatible images/generations endpoint
    url = f"{host}/v1/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }

    print(f"Generating image with {model!r}…")
    print(f"Prompt: {prompt!r}")
    t0 = time.time()

    resp = requests.post(url, json=payload, timeout=300)

    if resp.status_code != 200:
        # Fall back to native /api/generate endpoint
        print(f"  /v1/images/generations returned {resp.status_code}, trying /api/generate…")
        url_fallback = f"{host}/api/generate"
        resp = requests.post(
            url_fallback,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=300,
        )

    resp.raise_for_status()
    elapsed = time.time() - t0
    print(f"  Generation done in {elapsed:.1f}s")

    body = resp.json()

    # Parse response — try OpenAI format first, then Ollama native
    image_bytes: bytes | None = None

    if "data" in body and body["data"]:
        entry = body["data"][0]
        if "b64_json" in entry:
            image_bytes = base64.b64decode(entry["b64_json"])
        elif "url" in entry:
            # url format — fetch it
            img_resp = requests.get(entry["url"], timeout=30)
            img_resp.raise_for_status()
            image_bytes = img_resp.content

    if image_bytes is None and "images" in body:
        image_bytes = base64.b64decode(body["images"][0])

    if image_bytes is None and "response" in body:
        # Some builds encode the image directly in response
        try:
            image_bytes = base64.b64decode(body["response"])
        except Exception:
            pass

    if image_bytes is None:
        print("Raw response keys:", list(body.keys()))
        sys.exit("Could not extract image bytes from server response.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prompt = prompt[:40].replace(" ", "_").replace("/", "-")
    filename = f"{timestamp}_{safe_prompt}.png"
    output_path = out_dir / filename
    output_path.write_bytes(image_bytes)

    print(f"Saved: {output_path}  ({len(image_bytes) / 1024:.0f} KB)")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate images via Ollama image generation API")
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Image size WxH (default: 1024x1024)")
    parser.add_argument("--host", default=OLLAMA_HOST, help=f"Ollama server URL (default: {OLLAMA_HOST})")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory (default: ./output)")
    parser.add_argument("--pull", action="store_true", help="Pull model if not present on server")
    args = parser.parse_args()

    out_dir = Path(args.out)

    # Check connectivity
    try:
        v = requests.get(f"{args.host}/api/version", timeout=5).json()
        print(f"Connected to Ollama {v['version']} at {args.host}")
    except Exception as e:
        sys.exit(f"Cannot reach Ollama server at {args.host}: {e}")

    # Check model
    if not check_model_available(args.host, args.model):
        if args.pull:
            pull_model(args.host, args.model)
        else:
            print(f"Model {args.model!r} not found on server.")
            print(f"Pull it with:  --pull  flag, or manually on the server:")
            print(f"  ollama pull {args.model}")
            sys.exit(1)

    output_path = generate_image(
        prompt=args.prompt,
        model=args.model,
        size=args.size,
        host=args.host,
        out_dir=out_dir,
    )

    print(f"\nDone. Image at: {output_path}")


if __name__ == "__main__":
    main()
