import shutil
import subprocess

import numpy as np
import pytest

GREEN = (40, 200, 40)

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
requires_ffmpeg = pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe not available on PATH")


def draw_rect_border(frame: np.ndarray, left: int, right: int, top: int, bottom: int, color, thickness: int = 2) -> None:
    frame[top:top + thickness, left:right] = color
    frame[bottom - thickness:bottom, left:right] = color
    frame[top:bottom, left:left + thickness] = color
    frame[top:bottom, right - thickness:right] = color


def draw_filled_rect(frame: np.ndarray, left: int, right: int, top: int, bottom: int, color) -> None:
    frame[top:bottom, left:right] = color


def make_slide_frame(width: int, height: int, interior_color, text_seed: int) -> np.ndarray:
    """Build one synthetic "Zoom slide" frame: green border box + textured interior.

    Mirrors the real recording's layout (participant strip above a
    green-bordered screen share) closely enough to exercise the full
    detect -> crop -> dedup pipeline end to end.
    """
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (15, 15, 15)

    box_left, box_right = int(width * 0.06), int(width * 0.94)
    box_top, box_bottom = int(height * 0.11), int(height * 0.89)
    draw_rect_border(frame, box_left, box_right, box_top, box_bottom, GREEN, thickness=3)
    draw_filled_rect(frame, box_left + 4, box_right - 4, box_top + 4, box_bottom - 4, interior_color)

    # Small active-speaker thumbnail border above the box, touching it --
    # the same adjacency scenario that must not corrupt detection.
    draw_rect_border(frame, box_left + 20, box_left + 120, 5, box_top + 1, GREEN, thickness=2)

    # Deterministic pseudo-text texture so the crop isn't perfectly flat
    # (a flat crop has zero Laplacian variance and would be rejected as blurry).
    rng = np.random.default_rng(text_seed)
    n = 300
    ys = rng.integers(box_top + 10, box_bottom - 10, size=n)
    xs = rng.integers(box_left + 10, box_right - 10, size=n)
    frame[ys, xs] = (0, 0, 0)

    return frame


def encode_frames_to_mp4(frames: list[np.ndarray], fps: int, out_path) -> None:
    height, width = frames[0].shape[:2]
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "-",
        "-pix_fmt", "yuv420p",
        "-loglevel", "error",
        str(out_path),
    ]
    payload = b"".join(f.astype(np.uint8).tobytes() for f in frames)
    subprocess.run(cmd, input=payload, check=True)


@pytest.fixture
def synthetic_slide_recording(tmp_path):
    """A short recording with two distinct "slides" (green box, changing
    interior) followed by a talking-head segment with no green box."""
    width, height, fps = 640, 360, 5
    seconds_per_segment = 2

    slide_one = [make_slide_frame(width, height, (255, 255, 255), text_seed=1) for _ in range(fps * seconds_per_segment)]
    slide_two = [make_slide_frame(width, height, (60, 90, 220), text_seed=2) for _ in range(fps * seconds_per_segment)]

    talking_head = np.full((height, width, 3), (150, 110, 90), dtype=np.uint8)
    talking_head_frames = [talking_head.copy() for _ in range(fps * seconds_per_segment)]

    frames = slide_one + slide_two + talking_head_frames
    out_path = tmp_path / "synthetic_recording.mp4"
    encode_frames_to_mp4(frames, fps, out_path)
    return out_path
