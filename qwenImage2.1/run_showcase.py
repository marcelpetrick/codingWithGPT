#!/usr/bin/env python3
"""Generate the Qwen-Image-2.1 showcase images through a running ComfyUI server.

Records wall-clock time and peak VRAM per image, because the point of this
repo is to find out what the model actually costs on an 8 GB card.
"""
import argparse
import json
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMFY = Path("/home/mpetrick/repos/ComfyUI")
SERVER = "http://127.0.0.1:8188"


def request_json(url, data=None):
    body = None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=body)) as r:
        return json.load(r)


def vram_used_mb():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    )
    try:
        return int(out.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1


def wait_for_result(prompt_id, timeout, peak):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        peak[0] = max(peak[0], vram_used_mb())
        history = request_json(f"{SERVER}/history/{prompt_id}")
        if prompt_id in history:
            result = history[prompt_id]
            if result.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"execution failed; see {COMFY}/user/comfyui.log")
            return result
        time.sleep(1.0)
    raise TimeoutError(f"no result within {timeout}s")


def execution_seconds(result):
    """Server-side execution time, excluding any wait in the queue.

    The wall clock around a submit/poll cycle also counts time the prompt spent
    queued behind another job, which is not what a render costs.
    """
    stamps = {}
    for name, payload in result.get("status", {}).get("messages", []):
        if name in ("execution_start", "execution_success", "execution_error"):
            stamps[name] = payload.get("timestamp")
    start = stamps.get("execution_start")
    end = stamps.get("execution_success") or stamps.get("execution_error")
    if start and end:
        return (end - start) / 1000.0
    return None


def save_images(result, out_path):
    images = []
    for node_output in result.get("outputs", {}).values():
        images.extend(node_output.get("images", []))
    if not images:
        raise RuntimeError("workflow produced no image")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    query = urllib.parse.urlencode(images[0])
    with urllib.request.urlopen(f"{SERVER}/view?{query}") as r:
        out_path.write_bytes(r.read())
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--resolution", type=int, default=1024)
    ap.add_argument("--cfg", type=float, default=3.5)
    ap.add_argument("--only", help="run a single prompt by name")
    ap.add_argument("--timeout", type=float, default=3600)
    ap.add_argument("--outdir", type=Path, default=HERE / "images")
    ap.add_argument("--prompts", type=Path, default=HERE / "prompts.json",
                    help="prompt set to run (default: prompts.json)")
    args = ap.parse_args()

    workflow_template = json.loads((HERE / "workflows" / "qwen_image_2.1_t2i_api.json").read_text())
    prompts = json.loads(args.prompts.read_text())
    if args.only:
        prompts = [p for p in prompts if p["name"] == args.only]
        if not prompts:
            raise SystemExit(f"no prompt named {args.only}")

    report = []
    for index, spec in enumerate(prompts, 1):
        wf = json.loads(json.dumps(workflow_template))
        wf["5"]["inputs"]["prompt"] = spec["prompt"]
        wf["5"]["inputs"]["resolution"] = args.resolution
        wf["6"]["inputs"]["seed"] = spec["seed"]
        wf["6"]["inputs"]["steps"] = args.steps
        wf["6"]["inputs"]["cfg"] = args.cfg
        wf["8"]["inputs"]["filename_prefix"] = f"qwen21/{spec['name']}"

        print(f"[{index}/{len(prompts)}] {spec['name']} ... ", end="", flush=True)
        peak = [vram_used_mb()]
        started = time.monotonic()
        prompt_id = request_json(f"{SERVER}/prompt", {"prompt": wf})["prompt_id"]
        result = wait_for_result(prompt_id, args.timeout, peak)
        submitted_to_done = time.monotonic() - started
        elapsed = execution_seconds(result) or submitted_to_done
        queued = max(0.0, submitted_to_done - elapsed)
        path = save_images(result, args.outdir / f"{spec['name']}.png")
        queue_note = f" (+{queued:.0f}s queued)" if queued > 2 else ""
        print(f"{elapsed:6.1f}s{queue_note}  peak {peak[0]} MiB  -> {path.name}")
        report.append({
            "name": spec["name"],
            "seconds": round(elapsed, 1),
            "queued_seconds": round(queued, 1),
            "seconds_per_step": round(elapsed / args.steps, 2),
            "peak_vram_mib": peak[0],
            "steps": args.steps,
            "resolution": args.resolution,
            "cfg": args.cfg,
            "seed": spec["seed"],
        })

    (args.outdir / "timings.json").write_text(json.dumps(report, indent=2) + "\n")
    if report:
        total = sum(r["seconds"] for r in report)
        print(f"\n{len(report)} image(s) in {total/60:.1f} min, "
              f"mean {total/len(report):.1f}s, "
              f"peak VRAM {max(r['peak_vram_mib'] for r in report)} MiB")


if __name__ == "__main__":
    main()
