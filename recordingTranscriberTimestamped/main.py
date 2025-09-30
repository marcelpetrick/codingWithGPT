#!/usr/bin/env python3
"""
Transcribe a video's audio by ~5 MiB chunks with clear progress and speed options.

Usage:
  python3 transcribe_video.py /path/to/video.(mp4|mkv|...) \
      [--outdir OUTPUT_DIR] \
      [--bitrate 64] \
      [--model small] \
      [--language de] \
      [--device auto|cpu|cuda] \
      [--compute-type auto|int8|int8_float16|float16|float32]

Deps (system):
  - ffmpeg, ffprobe (Manjaro): sudo pacman -S ffmpeg

Deps (pip):
  - faster-whisper  (pip install faster-whisper)

Notes:
  - We re-encode audio to mono CBR MP3 so that "size ≈ bitrate * duration"
  - 5 MiB = 5 * 1024 * 1024 bytes
  - Timestamps in filenames: chunk_[HH-MM-SS.mmm]_[HH-MM-SS.mmm].mp3
  - Writes a Markdown file: transcription.md
  - For faster visible progress, you can:
      * raise --bitrate (e.g., 192) → shorter chunks (~3–4 min)
      * use a smaller model (tiny/base)
      * use --device cuda --compute-type float16 if you have an NVIDIA GPU
"""

import argparse
import math
import re
import shlex
import subprocess
import sys
from pathlib import Path

FIVE_MIB = 5 * 1024 * 1024  # bytes


# ---------------------------
# Helpers
# ---------------------------

def check_cmd(cmd: str) -> None:
    try:
        subprocess.run([cmd, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        sys.exit(f"Error: '{cmd}' not found. Please install it and ensure it's on PATH.")


def run(cmd, check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command (list or string)."""
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


# ---------------------------
# Args
# ---------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="Transcribe a video's audio by ~5 MiB chunks, with progress.")
    ap.add_argument("video", type=Path, help="Path to the video file")
    ap.add_argument("--outdir", type=Path, default=None, help="Output working directory (default: alongside video)")
    ap.add_argument("--bitrate", type=int, default=64, help="Audio bitrate kbps for chunking (default: 64)")
    ap.add_argument("--model", type=str, default="small", help="faster-whisper model size (tiny, base, small, medium, large-v3)")
    ap.add_argument("--language", type=str, default=None, help="Force language code (e.g., 'en', 'de'). Default: autodetect")
    ap.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"],
                    help="Force device for faster-whisper (auto/cpu/cuda).")
    ap.add_argument("--compute-type", type=str, default="auto",
                    help="CTranslate2 compute type (auto, int8, int8_float16, float16, float32, etc.).")
    return ap.parse_args()


# ---------------------------
# Pipeline steps
# ---------------------------

def ensure_outdir(video: Path, outdir: Path | None) -> Path:
    if outdir is None:
        outdir = video.with_suffix("").parent / f"{video.stem}_chunks"
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def extract_audio(video: Path, outdir: Path, target_kbps: int) -> Path:
    """
    Re-encode to mono CBR MP3 (target_kbps) at 16 kHz so chunk size ≈ predictable.
    Works for MKV, MP4, anything ffmpeg can decode.
    """
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
    print("   ffmpeg → audio_cbr.mp3", flush=True)
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
        # Fallback: try first stream with duration
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
    """
    Segment into numbered files; we'll rename with timestamps afterward.
    """
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
    print(f"   ffmpeg segment → {pattern}", flush=True)
    run(cmd)

    segs = sorted(seg_dir.glob("seg_*.mp3"))
    if not segs:
        raise RuntimeError("No segments produced. Check ffmpeg logs.")
    return segs


def rename_with_timestamps(segments: list[Path], chunk_dir: Path, total_duration: float, chunk_seconds: int) -> list[tuple[Path, float, float]]:
    chunk_dir.mkdir(exist_ok=True)
    renamed: list[tuple[Path, float, float]] = []
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

    # Clean up raw dir (ignore if not empty due to race/permissions)
    try:
        segments[0].parent.rmdir()
    except OSError:
        pass
    return renamed


def transcribe_chunks(
    renamed: list[tuple[Path, float, float]],
    outdir: Path,
    model_size: str,
    language: str | None,
    device: str = "auto",
    compute_type: str = "auto",
) -> Path:
    """
    Transcribe each chunk with faster-whisper, writing absolute timestamps.
    Adds clear progress logs per chunk and is resilient to failures.
    """
    print("   Loading transcription model (first time may download weights)...", flush=True)
    from faster_whisper import WhisperModel

    # The model download/output goes to stderr/stdout; after it's done, we proceed.
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    out_md = outdir / "transcription.md"
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# Transcription\n\n")
        for idx, (path, start, end) in enumerate(renamed, 1):
            print(f"➡️  Transcribing chunk {idx}/{len(renamed)}: {path.name} "
                  f"[{format_ts(start)} → {format_ts(end)}] ...", flush=True)
            try:
                # Faster settings: beam_size=1, no text conditioning
                segments, info = model.transcribe(
                    str(path),
                    language=language,
                    beam_size=1,
                    vad_filter=False,  # set True if long silences hurt accuracy
                    condition_on_previous_text=False,
                )

                # Write section header for this chunk
                f.write(f"## Chunk {path.name}\n\n")
                f.write(f"_Time range: [{format_ts(start)} → {format_ts(end)}]_\n\n")

                any_text = False
                for seg in segments:
                    abs_ts = start + seg.start  # seg.start is relative to chunk
                    line = f"[{format_ts(abs_ts)}] {seg.text.strip()}"
                    f.write(line + "\n")
                    any_text = True

                if not any_text:
                    # Extract display timestamp from filename (start) as fallback
                    m = re.search(r"\[(\d{2}-\d{2}-\d{2}\.\d{3})\]", path.name)
                    start_label = (m.group(1).replace("-", ":") if m else format_ts(start))
                    f.write(f"[{start_label}] (no speech detected)\n")

                f.write("\n")
                print(f"✅  Done {path.name}", flush=True)

            except Exception as e:
                print(f"❌  Failed {path.name}: {e}", flush=True)
                f.write(f"## Chunk {path.name}\n\n")
                f.write(f"_Time range: [{format_ts(start)} → {format_ts(end)}]_\n\n")
                f.write(f"(error: {e})\n\n")

    return out_md


# ---------------------------
# Main
# ---------------------------

def main():
    args = parse_args()
    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"Input not found: {video}")

    check_cmd("ffmpeg")
    check_cmd("ffprobe")

    outdir = ensure_outdir(video, args.outdir)
    print(f"Working in: {outdir}", flush=True)

    print("1) Extracting audio (mono CBR MP3)...", flush=True)
    audio_mp3 = extract_audio(video, outdir, args.bitrate)

    print("2) Probing audio to compute chunk size...", flush=True)
    bitrate_bps, duration = get_format_bitrate_and_duration(audio_mp3)
    bytes_per_sec = bitrate_bps / 8.0
    seconds_per_chunk = max(1, int(FIVE_MIB / bytes_per_sec))
    print(f"   Duration: {duration:.2f}s, Bitrate: {bitrate_bps/1000:.1f} kbps, "
          f"Chunk ≈ {seconds_per_chunk}s (~5 MiB)", flush=True)

    print("3) Splitting audio into chunks...", flush=True)
    segments = segment_audio(audio_mp3, outdir, seconds_per_chunk)

    print("4) Renaming chunks with timestamps in filename...", flush=True)
    chunk_dir = outdir / "chunks"
    renamed = rename_with_timestamps(segments, chunk_dir, duration, seconds_per_chunk)
    for p, s, e in renamed:
        print(f"   {p.name} [{format_ts(s)} → {format_ts(e)}]", flush=True)

    print("5) Transcribing chunks → transcription.md ...", flush=True)
    out_md = transcribe_chunks(
        renamed,
        outdir,
        args.model,
        args.language,
        device=args.device,
        compute_type=args.compute_type,
    )

    print(f"\nDone.\n- Chunks: {chunk_dir}\n- Transcription: {out_md}", flush=True)


if __name__ == "__main__":
    main()
