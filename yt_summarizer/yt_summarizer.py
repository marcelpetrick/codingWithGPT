# -*- coding: utf-8 -*-

"""
yt_summarizer.py

A robust Python 3 script that:
1. Downloads a YouTube video using yt-dlp
2. Extracts audio using ffmpeg
3. Transcribes audio using:
   - Local Whisper (if installed)
   - Otherwise OpenAI Whisper API
4. Summarizes the transcript using:
   - Local compression (optional keyword extraction using NLTK)
   - OpenAI GPT summarization API (primary)
5. Saves intermediate files when --keep 1 is used
6. Produces human-readable progress throughout

Designed for Manjaro Linux (zsh or bash shell), with yt-dlp and ffmpeg installed.

Author: ChatGPT
"""

import argparse
import os
import sys
import subprocess
import shutil
import json
import tempfile
import datetime
from pathlib import Path

# -----------------------------
# Optional local NLP utilities
# -----------------------------
try:
    import nltk
    nltk.download("punkt", quiet=True)
    from nltk.tokenize import word_tokenize
except Exception:
    nltk = None  # We'll degrade gracefully

# -----------------------------
# OpenAI API
# -----------------------------
from openai import OpenAI
client = OpenAI()

# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------

def log(msg: str):
    """Print a stylized, timestamped log message."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_cmd(cmd: list, error_msg: str) -> bool:
    """Run a system command robustly, printing output on failure."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            log(f"ERROR: {error_msg}")
            log("Command: " + " ".join(cmd))
            log("STDOUT:\n" + result.stdout)
            log("STDERR:\n" + result.stderr)
            return False
        return True
    except FileNotFoundError:
        log(f"ERROR: System tool missing: {cmd[0]}")
        return False
    except Exception as e:
        log(f"Unexpected error running command {cmd}: {e}")
        return False


# ------------------------------------------------------------
# Step 1: Download YouTube video
# ------------------------------------------------------------

def download_video(url: str, out_dir: Path) -> Path:
    log("Starting video download with yt-dlp …")

    out_path = out_dir / "video_raw.mp4"
    cmd = [
        "yt-dlp", "-f", "bestvideo+bestaudio",
        "-o", str(out_path),
        url
    ]

    if not run_cmd(cmd, "Video download failed"):
        raise RuntimeError("Video download failed")

    if not out_path.exists():
        raise RuntimeError("yt-dlp reported success but video file not found")

    log(f"Downloaded video to: {out_path}")
    return out_path


# ------------------------------------------------------------
# Step 2: Extract audio using ffmpeg
# ------------------------------------------------------------

def extract_audio(video_file: Path, out_dir: Path) -> Path:
    log("Extracting audio track with ffmpeg …")

    audio_path = out_dir / "audio.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_file),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path)
    ]

    if not run_cmd(cmd, "Audio extraction failed"):
        raise RuntimeError("Audio extraction failed")

    if not audio_path.exists():
        raise RuntimeError("ffmpeg reported success but audio file not found")

    log(f"Extracted audio to: {audio_path}")
    return audio_path


# ------------------------------------------------------------
# Step 3A: Local Whisper transcription
# ------------------------------------------------------------

def transcribe_local_whisper(audio_file: Path, out_dir: Path) -> str:
    """
    Try to transcribe with local Whisper CLI if installed.
    """
    whisper_exe = shutil.which("whisper")
    if whisper_exe is None:
        return None

    log("Attempting local transcription using Whisper CLI …")

    transcript_path = out_dir / "transcript_local.txt"
    cmd = [
        whisper_exe,
        str(audio_file),
        "--model", "medium",
        "--language", "en",
        "--fp16", "False",
        "--output_format", "txt",
        "--output_dir", str(out_dir)
    ]

    if not run_cmd(cmd, "Local Whisper transcription failed"):
        return None

    if not transcript_path.exists():
        log("Local Whisper did not produce expected transcript file.")
        return None

    log("Local Whisper transcription completed.")
    return transcript_path.read_text(encoding="utf-8")


# ------------------------------------------------------------
# Step 3B: OpenAI Whisper API transcription
# ------------------------------------------------------------

def transcribe_openai(audio_file: Path) -> str:
    log("Transcribing audio with OpenAI Whisper API …")

    try:
        with open(audio_file, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=f,
                response_format="text"
            )
        log("OpenAI transcription completed.")
        return transcript
    except Exception as e:
        raise RuntimeError(f"OpenAI Whisper API failed: {e}")


# ------------------------------------------------------------
# Step 4: Summarization
# ------------------------------------------------------------

def local_keyword_extraction(text: str) -> list:
    """Optional local transcript compression."""
    if nltk is None:
        return []
    try:
        tokens = word_tokenize(text.lower())
        freq = {}
        for t in tokens:
            if t.isalpha():
                freq[t] = freq.get(t, 0) + 1
        # Grab the top 20 frequent words
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:20]
        return [w for w, _ in top]
    except Exception:
        return []


def summarize_openai(text: str) -> str:
    log("Summarizing transcript with OpenAI GPT …")
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a world-class summarizer."},
                {"role": "user", "content":
                 "Please summarize the following transcript in clear, structured bullet points:\n\n" + text}
            ],
            temperature=0.3,
        )
        summary = response.choices[0].message.content
        log("OpenAI summarization completed.")
        return summary
    except Exception as e:
        raise RuntimeError(f"OpenAI summarization failed: {e}")


# ------------------------------------------------------------
# Main Orchestration
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="YouTube → Transcript → Summary with OpenAI")
    parser.add_argument("--url", required=True, help="YouTube URL")
    parser.add_argument("--keep", default="0", help="1 = keep intermediate files")
    args = parser.parse_args()

    keep = args.keep == "1"

    # Working directory
    if keep:
        out_dir = Path("yt_work_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
        out_dir.mkdir(exist_ok=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="yt_tmp_"))

    log(f"Working directory: {out_dir}")

    video_path = None
    audio_path = None
    transcript_text = None
    summary_text = None

    try:
        # 1. Download
        video_path = download_video(args.url, out_dir)

        # 2. Extract audio
        audio_path = extract_audio(video_path, out_dir)

        # 3. Transcribe
        transcript_text = transcribe_local_whisper(audio_path, out_dir)
        if transcript_text is None:
            transcript_text = transcribe_openai(audio_path)

        # Save raw transcript
        transcript_file = out_dir / "transcript_raw.txt"
        transcript_file.write_text(transcript_text, encoding="utf-8")

        # 4. Optional local keyword extract
        keywords = local_keyword_extraction(transcript_text)
        if keywords:
            (out_dir / "keywords_local.txt").write_text("\n".join(keywords))

        # 5. Summarize
        summary_text = summarize_openai(transcript_text)

        summary_file = out_dir / "summary.txt"
        summary_file.write_text(summary_text, encoding="utf-8")

        log("SUMMARY:")
        print(summary_text)

        log("DONE.")

    except Exception as e:
        log(f"FATAL ERROR: {e}")
    finally:
        if not keep:
            log("Cleaning up temporary files (use --keep 1 to preserve).")
            shutil.rmtree(out_dir, ignore_errors=True)


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
