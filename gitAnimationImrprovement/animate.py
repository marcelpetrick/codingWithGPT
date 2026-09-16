#!/usr/bin/env python3
"""Rebuild the three-second farm logo GIFs from the MP4 and sheep sprite sheet."""

from pathlib import Path
import math
import subprocess

from PIL import Image, ImageDraw, ImageChops


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
ASSETS = OUT / "assets"
INPUT = ROOT / "WhatsApp Video 2026-09-16 at 10.27.58.mp4"
FRAMES = 60
DURATION_MS = 50
SCALE = 3
GREEN = (106, 158, 131, 255)


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def extract_sprites():
    sheet = Image.open(ASSETS / "sheep-walk-sheet.png").convert("RGBA")
    if sheet.getextrema()[3][0] == 255:
        # The generator sometimes bakes its transparency checkerboard into RGB.
        # Key only the connected neutral background; enclosed white wool stays.
        red, green, blue, _ = sheet.split()
        maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        minimum = ImageChops.darker(ImageChops.darker(red, green), blue)
        neutral = ImageChops.subtract(maximum, minimum).point(
            lambda difference: 255 if difference < 22 else 0)
        ImageDraw.floodfill(neutral, (0, 0), 128, thresh=0)
        alpha = neutral.point(lambda value: 0 if value == 128 else 255)
        sheet.putalpha(alpha)
        sheet.save(ASSETS / "sheep-walk-transparent.png")
    cell_width = sheet.width // 4
    cells = [sheet.crop((i * cell_width, 0, (i + 1) * cell_width, sheet.height))
             for i in range(4)]
    boxes = [cell.getbbox() for cell in cells]
    if any(box is None for box in boxes):
        raise ValueError("Expected four nonempty sheep walking poses.")
    # Use one common crop so gait changes do not change the body scale.
    common = (min(b[0] for b in boxes), min(b[1] for b in boxes),
              max(b[2] for b in boxes), max(b[3] for b in boxes))
    return [cell.crop(common) for cell in cells]


def flower(frame, x, y, radius, openness, phase):
    if openness < 0.005:
        return
    radius *= SCALE
    x, y = x * SCALE, y * SCALE
    # Petals unfurl from the center with a little natural rotation.
    petal_length = radius * openness
    draw = ImageDraw.Draw(frame)
    for i in range(5):
        angle = i * math.tau / 5 - math.pi / 2 + 0.12 * math.sin(phase)
        cx = x + math.cos(angle) * petal_length * 0.58
        cy = y + math.sin(angle) * petal_length * 0.58
        r = petal_length * 0.49
        draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                     fill=(255, 255, 255, 255), outline=GREEN,
                     width=max(1, round(0.75 * SCALE * openness)))
    r = max(0.7, 1.3 * openness) * SCALE
    draw.ellipse((x - r, y - r, x + r, y + r), fill=GREEN)


def render(base, sprites, t):
    frame = base.copy()
    for x, y, radius, delay in [(30.5, 116, 5.2, 0.25),
                                (54.5, 115, 5.0, 0.48),
                                (22.5, 128, 4.1, 0.72)]:
        openness = smooth((t - delay) / 0.8) * (1 - smooth((t - 2.25) / 0.6))
        flower(frame, x, y, radius, openness, t * 2 + delay)

    if 0.1 < t < 2.75:
        travel = max(0.0, min(1.0, (t - 0.1) / 2.3))
        center_x = 220 - 118 * travel
        entering = smooth((t - 2.35) / 0.4)
        shrink = 1 - 0.25 * entering
        sprite = sprites[int((t - 0.1) * 8) % 4]
        width = round(36 * SCALE * shrink)
        height = round(width * sprite.height / sprite.width)
        sprite = sprite.resize((width, height), Image.Resampling.LANCZOS)
        if entering:
            sprite.putalpha(sprite.getchannel("A").point(
                lambda a: round(a * (1 - entering))))
        # The changing leg poses and a gentle hop make a readable walk at 200 px.
        hop = math.sin((t - 0.1) * math.tau * 4) * 0.6 * (1 - entering)
        foot_y = 145 - 3 * entering + hop
        frame.alpha_composite(sprite, (round(center_x * SCALE - width / 2),
                                       round(foot_y * SCALE - height)))
    return frame.convert("RGB")


def save_gif(frames, path, size):
    frames = [im.resize((size, size), Image.Resampling.LANCZOS) for im in frames]
    # A shared palette prevents stationary logo pixels flickering between frames.
    atlas = Image.new("RGB", (size * 10, size * 6))
    for i, frame in enumerate(frames):
        atlas.paste(frame, ((i % 10) * size, (i // 10) * size))
    palette = atlas.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:],
                    duration=DURATION_MS, loop=0, optimize=False, disposal=1)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(INPUT),
                    str(ASSETS / "source-%02d.png")], check=True)
    source_frames = [Image.open(p).convert("RGB")
                     for p in sorted(ASSETS.glob("source-[0-9][0-9].png"))]
    source_frames[0].save(OUT / "original.gif", save_all=True,
                          append_images=source_frames[1:], duration=100, loop=0)
    base = Image.open(ASSETS / "source-01.png").convert("RGBA").resize(
        (200 * SCALE, 200 * SCALE), Image.Resampling.LANCZOS)
    sprites = extract_sprites()
    frames = [render(base, sprites, i * DURATION_MS / 1000) for i in range(FRAMES)]
    save_gif(frames, OUT / "farm-loop.gif", 200)
    save_gif(frames, OUT / "farm-loop-600.gif", 600)

    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "600x600",
               "-framerate", "20", "-i", "pipe:0", "-an", "-c:v", "libx264",
               "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               str(OUT / "farm-loop.mp4")]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        for frame in frames:
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError("FFmpeg video export failed")

    contact = Image.new("RGB", (1200, 800), "white")
    for j, i in enumerate([0, 12, 24, 36, 48, 59]):
        contact.paste(frames[i].resize((400, 400), Image.Resampling.LANCZOS),
                      ((j % 3) * 400, (j // 3) * 400))
    contact.save(OUT / "preview.png")
    print("Created farm-loop.gif, farm-loop-600.gif, farm-loop.mp4, and preview.png")


if __name__ == "__main__":
    main()
