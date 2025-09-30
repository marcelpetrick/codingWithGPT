#!/usr/bin/env python3
"""
Transcribe a video's audio by ~5 MiB chunks.

Usage:
  python3 transcribe_video.py /path/to/video.mp4 [--outdir OUTPUT_DIR] [--bitrate 64] [--model small]

Deps:
  - ffmpeg, ffprobe (system): sudo pacman -S ffmpeg
  - Python: pip install faster-whisper

Notes:
  - We re-encode audio to mono CBR MP3 so that "size ≈ bitrate * duration"
  - 5 MiB = 5 * 1024 * 1024 bytes
  - Timestamps in filenames: chunk_[HH-MM-SS.mmm]_[HH-MM-SS.mmm].mp3
  - transcription.md lines: [HH:MM:SS.mmm] text
"""

import argparse
import math
import os
import re
import shlex
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

FIVE_MIB = 5 * 1024 * 1024  # bytes

def check_cmd(cmd):
    try:
        subprocess.run([cmd, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        sys.exit(f"Error: '{cmd}' not found. Please install it and ensure it's on PATH.")

def run(cmd, check=True, capture_output=False):
    """Run a shell command (list form)."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    res = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
    return res

def ffprobe_json(path: Path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    res = run(cmd, capture_output=True)
    import json
    return json.loads(res.stdout)

def format_ts(seconds_float: float) -> str:
    """Return HH:MM:SS.mmm"""
    ms = int(round((seconds_float - math.floor(seconds_float)) * 1000))
    t = int(seconds_float)
    h = t // 3600
    m = (t % 3600) // 60
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def format_ts_filename(seconds_float: float) -> str:
    """Return HH-MM-SS.mmm (safe for filenames)"""
    return format_ts(seconds_float).replace(":", "-")

def parse_args():
    ap = argparse.ArgumentParser(description="Transcribe a video's audio by ~5 MiB chunks.")
    ap.add_argument("video", type=Path, help="Path to the video file")
    ap.add_argument("--outdir", type=Path, default=None, help="Output working directory (default: alongside video)")
    ap.add_argument("--bitrate", type=int, default=64, help="Audio bitrate kbps for chunking (default: 64)")
    ap.add_argument("--model", type=str, default="small", help="faster-whisper model size (e.g., tiny, base, small, medium, large-v3)")
    ap.add_argument("--language", type=str, default=None, help="Force language code (e.g., 'en', 'de'). Default: autodetect")
    return ap.parse_args()

def ensure_outdir(video: Path, outdir: Path | None) -> Path:
    if outdir is None:
        outdir = video.with_suffix("").parent / f"{video.stem}_chunks"
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir

def extract_audio(video: Path, outdir: Path, target_kbps: int) -> Path:
    # Re-encode to mono CBR MP3 at target_kbps (e.g., 64 kbps), 16 kHz for speed.
    audio_mp3 = outdir / "audio_cbr.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", f"{target_kbps}k",
        "-codec:a", "libmp3lame",
        "-compression_level", "2",
        "-f", "mp3",
        str(audio_mp3),
    ]
    run(cmd)
    return audio_mp3

def get_format_bitrate_and_duration(media: Path) -> tuple[int, float]:
    info = ffprobe_json(media)
    fmt = info.get("format", {})
    # Prefer format.bit_rate and format.duration
    try:
        br = int(fmt.get("bit_rate"))
    except Exception:
        # Fallback: try first audio stream
        br = None
        for st in info.get("streams", []):
            if st.get("codec_type") == "audio" and "bit_rate" in st:
                try:
                    br = int(st["bit_rate"])
                    break
                except Exception:
                    pass
        if br is None:
            raise RuntimeError("Could not determine audio bitrate via ffprobe.")
    try:
        dur = float(fmt.get("duration"))
    except Exception:
        # Sum stream durations or fail
        dur = None
        for st in info.get("streams", []):
            if "duration" in st:
                try:
                    dur = float(st["duration"])
                    break
                except Exception:
                    pass
        if dur is None:
            raise RuntimeError("Could not determine audio duration via ffprobe.")
    return br, dur

def segment_audio(audio_mp3: Path, outdir: Path, seconds_per_chunk: int) -> list[Path]:
    # Segment into numbered files; we'll rename with timestamps afterward.
    seg_dir = outdir / "segments_raw"
    seg_dir.mkdir(exist_ok=True)
    pattern = seg_dir / "seg_%05d.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(audio_mp3),
        "-f", "segment",
        "-segment_time", str(seconds_per_chunk),
        "-reset_timestamps", "1",
        "-codec", "copy",  # keep CBR without re-encoding
        str(pattern),
    ]
    run(cmd)

    # Collect segments sorted by index
    segs = sorted(seg_dir.glob("seg_*.mp3"))
    if not segs:
        raise RuntimeError("No segments produced. Check ffmpeg logs.")
    return segs

def rename_with_timestamps(segments: list[Path], chunk_dir: Path, total_duration: float, chunk_seconds: int) -> list[tuple[Path, float, float]]:
    chunk_dir.mkdir(exist_ok=True)
    renamed = []
    for idx, seg in enumerate(segments):
        start = idx * chunk_seconds
        end = min((idx + 1) * chunk_seconds, total_duration)
        start_s = format_ts_filename(start)
        end_s = format_ts_filename(end)
        new_name = chunk_dir / f"chunk_[{start_s}]_[{end_s}].mp3"
        if new_name.exists():
            new_name.unlink()
        seg.replace(new_name)
        renamed.append((new_name, start, end))
    # Remove the raw segment directory now that we've moved files
    try:
        segments[0].parent.rmdir()
    except OSError:
        pass
    return renamed

def transcribe_chunks(renamed: list[tuple[Path, float, float]], outdir: Path, model_size: str, language: str | None):
    from faster_whisper import WhisperModel

    # Choose compute type that works broadly
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    out_md = outdir / "transcription.md"
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# Transcription\n\n")
        for path, start, end in renamed:
            # Extract display timestamp from filename (start)
            m = re.search(r"\[(\d{2}-\d{2}-\d{2}\.\d{3})\]", path.name)
            if m:
                start_label = m.group(1).replace("-", ":")
            else:
                start_label = format_ts(start)

            f.write(f"## Chunk {path.name}\n\n")
            f.write(f"_Time range: [{format_ts(start)} → {format_ts(end)}]_\n\n")

            segments, info = model.transcribe(str(path), language=language)
            lines = []
            for seg in segments:
                # Each segment has its own start time relative to the chunk
                abs_ts = start + seg.start
                lines.append(f"[{format_ts(abs_ts)}] {seg.text.strip()}")
            if lines:
                for line in lines:
                    f.write(line + "\n")
            else:
                f.write(f"[{start_label}] (no speech detected)\n")
            f.write("\n")

    return out_md

def main():
    args = parse_args()
    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"Input not found: {video}")

    check_cmd("ffmpeg")
    check_cmd("ffprobe")

    outdir = ensure_outdir(video, args.outdir)
    print(f"Working in: {outdir}")

    print("1) Extracting audio (mono CBR MP3)...")
    audio_mp3 = extract_audio(video, outdir, args.bitrate)

    print("2) Probing audio to compute chunk size...")
    bitrate_bps, duration = get_format_bitrate_and_duration(audio_mp3)
    # seconds per chunk ≈ FIVE_MIB / (bitrate_bytes_per_sec)
    bytes_per_sec = bitrate_bps / 8.0
    seconds_per_chunk = max(1, int(FIVE_MIB / bytes_per_sec))
    # Be nice and round to nearest whole second
    print(f"   Duration: {duration:.2f}s, Bitrate: {bitrate_bps/1000:.1f} kbps, Chunk ≈ {seconds_per_chunk}s (~5 MiB)")

    print("3) Splitting audio into chunks...")
    segments = segment_audio(audio_mp3, outdir, seconds_per_chunk)

    print("4) Renaming chunks with timestamps in filename...")
    chunk_dir = outdir / "chunks"
    renamed = rename_with_timestamps(segments, chunk_dir, duration, seconds_per_chunk)
    for p, s, e in renamed:
        print(f"   {p.name} [{format_ts(s)} → {format_ts(e)}]")

    print("5) Transcribing chunks → transcription.md ...")
    out_md = transcribe_chunks(renamed, outdir, args.model, args.language)

    print(f"\nDone.\n- Chunks: {chunk_dir}\n- Transcription: {out_md}")

if __name__ == "__main__":
    main()
