"""ffmpeg/ffprobe wrappers: video probing and frame sampling.

Frames are streamed from an ``ffmpeg`` subprocess as raw RGB24 buffers rather
than written to disk, so sampling a multi-hour recording doesn't require
thousands of temporary image files.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np


class FfmpegNotFoundError(RuntimeError):
    """Raised when the ``ffmpeg``/``ffprobe`` binaries are not on PATH."""


def require_ffmpeg() -> None:
    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise FfmpegNotFoundError(
                f"'{binary}' was not found on PATH. Install ffmpeg to use this tool."
            )


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    duration_s: float
    fps: float


def probe(path: Path | str) -> VideoInfo:
    """Inspect a video file with ffprobe and return basic stream info."""
    require_ffmpeg()
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    duration = float(data["format"]["duration"])

    fps_raw = stream.get("avg_frame_rate", "0/1")
    num, _, den = fps_raw.partition("/")
    fps = float(num) / float(den) if den and float(den) != 0 else float(num or 0)

    return VideoInfo(
        width=int(stream["width"]),
        height=int(stream["height"]),
        duration_s=duration,
        fps=fps,
    )


def iter_sampled_frames(
    path: Path | str, interval_s: float, width: int, height: int
) -> Iterator[tuple[float, np.ndarray]]:
    """Yield ``(timestamp_seconds, frame)`` tuples sampled at ``interval_s``.

    ``frame`` is an ``(height, width, 3)`` uint8 RGB array. The caller must
    already know the frame dimensions (from :func:`probe`) since ffmpeg's
    rawvideo output carries no per-frame header to infer them from.
    """
    require_ffmpeg()
    frame_bytes = width * height * 3
    cmd = [
        "ffmpeg",
        "-i", str(path),
        "-vf", f"fps=1/{interval_s}",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-loglevel", "error",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    try:
        frame_index = 0
        while True:
            buf = _read_exact(proc.stdout, frame_bytes)
            if buf is None:
                break
            frame = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 3))
            yield frame_index * interval_s, frame
            frame_index += 1
    finally:
        proc.stdout.close()
        proc.wait()
        if proc.returncode not in (0, None) and proc.returncode < 0:
            # Negative return code means we killed it ourselves (generator
            # closed early) -- not an error worth surfacing.
            pass


def _read_exact(stream, n: int) -> bytes | None:
    """Read exactly ``n`` bytes from ``stream``, or ``None`` at clean EOF."""
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            if not chunks:
                return None
            # Partial trailing frame (truncated stream) -- treat as EOF.
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def extract_audio(video_path: Path | str, out_wav: Path | str, sample_rate: int = 16000) -> Path:
    """Extract mono PCM audio at ``sample_rate`` Hz to ``out_wav`` via ffmpeg."""
    require_ffmpeg()
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-loglevel", "error",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)
    return out_wav
