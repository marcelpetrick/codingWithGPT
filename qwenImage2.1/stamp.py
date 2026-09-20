#!/usr/bin/env python3
"""Stamp the rendering setup into the bottom-left corner of an image.

The caption is composited rather than prompted: the model renders text well,
but a technical caption has to be exactly right, and compositing guarantees it.
"""
import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COMFY = Path("/home/mpetrick/repos/ComfyUI")


def comfy_version():
    try:
        return (COMFY / "comfyui_version.py").read_text().split('"')[1]
    except (OSError, IndexError):
        return "unknown"


def gpu_name_and_vram():
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True,
    ).stdout.strip()
    name, vram = (p.strip() for p in out.split(","))
    return name.replace(" Laptop GPU", ""), f"{int(vram.split()[0]) / 1024:.0f} GB"


def total_ram_gb():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            return f"{int(line.split()[1]) / 1024 / 1024:.0f} GB"
    return "?"


def load_font(size):
    for candidate in (
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def caption_lines(title, meta):
    gpu, vram = gpu_name_and_vram()
    return [
        title,
        f"Qwen-Image-2.1  7B DiT int8 + Qwen3-VL-8B w4a8 + RGBA VAE bf16",
        f"ComfyUI {comfy_version()}  --lowvram   euler/simple  "
        f"{meta['steps']} steps  cfg {meta['cfg']}  {meta['resolution']}x{meta['resolution']}",
        f"{gpu}  {vram} VRAM   host RAM {total_ram_gb()}   {meta['seconds']:.0f}s/image",
    ]


def stamp(path, out, title, meta):
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")

    size = max(11, image.width // 68)
    font_bold = load_font(int(size * 1.35))
    font = load_font(size)
    lines = caption_lines(title, meta)
    fonts = [font_bold] + [font] * (len(lines) - 1)

    pad = image.width // 40
    gap = int(size * 0.55)
    heights = [f.getbbox(t)[3] - f.getbbox(t)[1] + gap for t, f in zip(lines, fonts)]
    widths = [f.getbbox(t)[2] - f.getbbox(t)[0] for t, f in zip(lines, fonts)]
    box_h, box_w = sum(heights) + pad, max(widths) + 2 * pad

    top = image.height - box_h - pad
    draw.rectangle([0, top - pad // 2, box_w, image.height], fill=(0, 0, 0, 150))

    y = top
    for text, f, h in zip(lines, fonts, heights):
        draw.text((pad, y), text, font=f, fill=(255, 255, 255, 235))
        y += h

    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--timings", type=Path, help="timings.json holding this image's entry")
    args = ap.parse_args()

    meta = {"steps": 30, "cfg": 3.5, "resolution": 1024, "seconds": 0.0}
    if args.timings and args.timings.exists():
        for entry in json.loads(args.timings.read_text()):
            if entry["name"] == args.image.stem:
                meta.update(entry)
                break
    print(stamp(args.image, args.out, args.title, meta))


if __name__ == "__main__":
    main()
