"""ffmpeg/ffprobe wrappers: video probing and frame sampling.

Frames are streamed from an ``ffmpeg`` subprocess as raw RGB24 buffers rather
than written to disk, so sampling a multi-hour recording doesn't require
thousands of temporary image files.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np


class FfmpegNotFoundError(RuntimeError):
    """Raised when the ``ffmpeg``/``ffprobe`` binaries are not on PATH."""


class InvalidVideoError(RuntimeError):
    """Raised when ``path`` exists but isn't a video ffprobe can read."""


class VideoDecodeError(RuntimeError):
    """Raised when ffmpeg exits with an error while sampling frames."""


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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise InvalidVideoError(
            f"ffprobe couldn't read {path} as a video: {result.stderr.strip()}"
        )
    try:
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
    except (json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
        raise InvalidVideoError(f"{path} has no readable video stream") from exc

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

    Raises :class:`VideoDecodeError` if ffmpeg exits with an error *after*
    the input is naturally exhausted (e.g. it crashed partway through a
    corrupt recording) -- without this check, a mid-stream ffmpeg failure
    looks identical to "no more frames" and would silently truncate the
    slide extraction instead of surfacing an error. Closing the generator
    early (e.g. via ``break`` in a caller's ``for`` loop) does not raise.
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
    with tempfile.TemporaryFile() as stderr_capture:
        # ffmpeg's stderr is captured to a real file rather than a pipe:
        # a PIPE has a small OS buffer (commonly 64KB), and since we only
        # drain stdout here, a chatty ffmpeg failure could fill that pipe
        # and deadlock both processes.
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=stderr_capture)
        assert proc.stdout is not None
        completed_naturally = False
        try:
            frame_index = 0
            while True:
                buf = _read_exact(proc.stdout, frame_bytes)
                if buf is None:
                    completed_naturally = True
                    break
                frame = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 3))
                yield frame_index * interval_s, frame
                frame_index += 1
        finally:
            proc.stdout.close()
            returncode = proc.wait()
            if completed_naturally and returncode != 0:
                stderr_capture.seek(0)
                stderr_text = stderr_capture.read().decode(errors="replace").strip()
                message = f"ffmpeg exited with status {returncode} while sampling {path}"
                if stderr_text:
                    message = f"{message}: {stderr_text}"
                raise VideoDecodeError(message)


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
