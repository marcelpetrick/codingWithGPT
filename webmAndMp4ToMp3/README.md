# webm & m4a → MP3 Converter

Batch-converts `.webm`, `.m4a`, `.m4b`, and `.mp4` audio files to high-quality MP3,
preserving all available metadata as ID3v2.3 tags and naming each output file after
its artist and title.

## Requirements

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) with `libmp3lame` support (available in most distro packages)
- [mutagen](https://mutagen.readthedocs.io/) Python library

Install mutagen:

```bash
pip install mutagen
```

## Usage

```bash
python3 convert.py --input <input-dir> [--output <output-dir>] [--verbose]
```

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--input <path>` | `-i` | Directory containing source audio files (**required**) |
| `--output <path>` | `-o` | Destination directory (default: `./output/` in the current working directory) |
| `--parallel <N>` | `-p` | Number of simultaneous conversions (default: CPU core count; `1` = sequential) |
| `--verbose` | `-v` | Show detailed step-by-step progress (output may interleave in parallel mode) |

### Examples

```bash
# Minimal — output goes to ./output/, all cores used
python3 convert.py --input ./input

# Custom output directory
python3 convert.py --input ./input --output ~/Music/converted

# Limit to 2 parallel conversions
python3 convert.py --input ./input --parallel 2

# Sequential (one at a time), verbose
python3 convert.py --input ./input --parallel 1 --verbose
```

## What it does

1. Scans the input directory for `.webm`, `.m4a`, `.m4b`, and `.mp4` files.
2. Reads embedded metadata (artist, title, album, year, track, genre, …) from each source file via `mutagen`.
3. Converts the audio to MP3 using `ffmpeg` with **LAME VBR V0** (`-q:a 0`), the highest-quality variable-bitrate preset (~200–260 kbps average). This conserves as much audio fidelity as a lossy-to-lossy transcode allows.
4. Names the output file `Artist - Title.mp3` when both tags are present, or falls back to the original filename stem.
5. Writes explicit **ID3v2.3** tags to the output MP3 via `mutagen` so the file is correctly recognised by any player or media library (artist, title, album, year, track number, genre, composer, comment).
6. Handles filename collisions by appending a numeric suffix (`_1`, `_2`, …).
7. Reports a conversion summary (converted / failed) at the end.

## Output structure

```
output/
├── Artist A - Song Title.mp3
├── Artist B - Another Song.mp3
└── ...
```

The output directory is created automatically if it does not exist.

## Notes

- Source files without embedded metadata tags are named after their original filename stem.
- The input and output directories are excluded from version control (see `.gitignore`).
