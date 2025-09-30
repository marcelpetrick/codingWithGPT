# Recording Transcriber (Timestamped)

**License:** GPLv3  
**Author:** <mail@marcelpetrick.it>

This project was written to **automate extracting the spoken word from videos, with precise timestamps**. The idea is to make it simple to later **merge the transcript with extracted slides (or other artifacts)** so a full (virtual) **meetup/webinar becomes a readable document**.

---

## What it does

- Extracts audio from a video (MKV/MP4/… via FFmpeg), re-encodes to **mono CBR MP3**
- Splits audio into predictable **~5 MiB** chunks (size ≈ bitrate × duration)
- Names each chunk with **start/end timestamps** in the filename
- Transcribes every chunk with **faster-whisper**
- Produces a clean, timestamped **`transcription.md`** (absolute timestamps per line)
- Prints clear per-chunk progress (➡️ / ✅ / ❌)

---

## Requirements

**System (Manjaro/Arch)**
- FFmpeg + FFprobe

**Python**
- Python 3.10+ recommended
- Pip installation (see below)

---

## Installation

Create and activate a virtual environment (recommended), then install the Python dependencies via pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> On Manjaro/Arch, install FFmpeg system-wide:
> ```bash
> sudo pacman -S ffmpeg
> ```

---

## Usage

Basic:

```bash
python3 main.py /path/to/video.mkv
```

Common options:

- `--outdir OUTPUT_DIR` – target folder for chunks and `transcription.md`
- `--bitrate N` – MP3 bitrate in kbps (default **64**). Higher ⇒ **shorter chunks**
- `--model {tiny,base,small,medium,large-v3}` – speed vs accuracy
- `--language de|en|…` – force language (skip autodetect)
- `--device auto|cpu|cuda`
- `--compute-type auto|int8|int8_float16|float16|float32`

Show help:

```bash
python3 main.py -h
```

### Examples

**Fast CPU feedback (smaller model + shorter chunks):**
```bash
python3 main.py "recording.mkv" \
  --bitrate 192 \
  --model tiny \
  --device cpu \
  --compute-type int8
```

**Use NVIDIA GPU (if available):**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install faster-whisper ctranslate2
python3 main.py "recording.mkv" \
  --model small \
  --device cuda \
  --compute-type float16 \
  --bitrate 192
```

**German audio:**
```bash
python3 main.py "vortrag.mkv" --language de
```

---

## Output

Given `2025-09-30 11-38-31.mkv`, you’ll get:

- Working folder: `2025-09-30 11-38-31_chunks/`
  - `audio_cbr.mp3` — mono, 16 kHz, constant bitrate
  - `chunks/`
    - `chunk_[00-00-00.000]_[00-10-55.000].mp3`
    - `chunk_[00-10-55.000]_[00-21-50.000].mp3`
    - …
  - `transcription.md` — Markdown with absolute timestamps

Excerpt:

```markdown
## Chunk chunk_[00-10-55.000]_[00-21-50.000].mp3

_Time range: [00:10:55.000 → 00:21:50.000]_

[00:11:03.120] Welcome to the second part…
[00:11:45.456] Today we’ll cover…
```

---

## How chunk sizing works

- Encode to **CBR MP3** at `--bitrate` kbps  
- Bytes/sec ≈ `(bitrate_kbps * 1000) / 8`  
- Target bytes/chunk = **5 MiB** = `5 * 1024 * 1024`  
- Seconds/chunk ≈ `5 MiB / bytes_per_sec`

At **64 kbps**: ~655 s ≈ **10.9 minutes** per chunk.  
Want shorter chunks? Increase `--bitrate` (e.g., 192 kbps → ~3.6 minutes).

---

## Performance tips

- Prefer **tiny/base** for speed; larger models for accuracy
- CPU:
  ```bash
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python3 main.py input.mkv --model tiny --compute-type int8
  ```
- GPU:
  - Use `--device cuda --compute-type float16`
  - Ensure CUDA and a compatible `ctranslate2` wheel are installed

---

## Troubleshooting

- **`'ffmpeg' not found`** → Install FFmpeg (Manjaro: `sudo pacman -S ffmpeg`)
- **“Looks stuck after model download”** → It’s transcribing the first chunk. With 64 kbps, a chunk is ~11 minutes. Use `--bitrate 192` and/or a smaller `--model` for faster visible progress.
- **No chunks produced** → Check FFmpeg logs; verify the input has an audio track.

---

## Project structure

```text
.
├── main.py
└── README.md
```

---

## Contributing

Issues and PRs are welcome. Please keep dependencies minimal and the script portable across Linux distros.

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.  
See the `LICENSE` file for details.

---

## Credits

- [FFmpeg] — media Swiss army knife  
- [faster-whisper] (CTranslate2 backend) — fast, accurate transcription

[FFmpeg]: https://ffmpeg.org/  
[faster-whisper]: https://github.com/guillaumekln/faster-whisper
