#!/usr/bin/env python3
"""Convert .m4a, .m4b, .webm, and .mp4 audio files to high-quality MP3 with ID3 tags."""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.id3 import (
        ID3, ID3NoHeaderError,
        TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TCON, TCOM, COMM,
    )
except ImportError:
    print("Error: mutagen not found. Install it with: pip install mutagen")
    sys.exit(1)

SUPPORTED_EXTENSIONS = {'.m4a', '.m4b', '.webm', '.mp4'}


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg)


def read_metadata(path: Path, verbose: bool) -> dict:
    """Return a dict of tag-name -> string value from any mutagen-readable file."""
    log(f"  Reading metadata ...", verbose)
    try:
        audio = MutagenFile(str(path), easy=True)
        if audio is None:
            return {}
        easy_to_id3 = {
            'title':       'title',
            'artist':      'artist',
            'albumartist': 'albumartist',
            'album':       'album',
            'date':        'date',
            'tracknumber': 'tracknumber',
            'genre':       'genre',
            'composer':    'composer',
            'comment':     'comment',
        }
        meta = {}
        for easy_key, out_key in easy_to_id3.items():
            val = audio.get(easy_key)
            if val:
                meta[out_key] = str(val[0]).strip()
        log(f"  Metadata: {meta}", verbose)
        return meta
    except Exception as exc:
        log(f"  Warning: could not read metadata: {exc}", verbose)
        return {}


def safe_filename(name: str) -> str:
    """Replace filesystem-unsafe characters."""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, '_')
    return name.strip('. ')


def output_stem(source: Path, meta: dict) -> str:
    """Build 'Artist - Title' stem from metadata, falling back to the source stem."""
    artist = meta.get('artist', '')
    title  = meta.get('title', '')
    if artist and title:
        return safe_filename(f"{artist} - {title}")
    if title:
        return safe_filename(title)
    return safe_filename(source.stem)


def unique_path(directory: Path, stem: str, suffix: str = '.mp3') -> Path:
    candidate = directory / (stem + suffix)
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def write_id3(mp3_path: Path, meta: dict, verbose: bool) -> None:
    """Write ID3v2.3 tags to the output MP3 via mutagen."""
    log("  Writing ID3 tags ...", verbose)
    try:
        try:
            tags = ID3(str(mp3_path))
        except ID3NoHeaderError:
            tags = ID3()

        mapping = {
            'title':       ('TIT2', lambda v: TIT2(encoding=3, text=v)),
            'artist':      ('TPE1', lambda v: TPE1(encoding=3, text=v)),
            'albumartist': ('TPE2', lambda v: TPE2(encoding=3, text=v)),
            'album':       ('TALB', lambda v: TALB(encoding=3, text=v)),
            'date':        ('TDRC', lambda v: TDRC(encoding=3, text=v)),
            'tracknumber': ('TRCK', lambda v: TRCK(encoding=3, text=v)),
            'genre':       ('TCON', lambda v: TCON(encoding=3, text=v)),
            'composer':    ('TCOM', lambda v: TCOM(encoding=3, text=v)),
            'comment':     ('COMM', lambda v: COMM(encoding=3, lang='eng', desc='', text=v)),
        }
        for key, (frame_id, maker) in mapping.items():
            if key in meta:
                tags[frame_id] = maker(meta[key])
                log(f"    {frame_id}: {meta[key]}", verbose)

        tags.save(str(mp3_path), v2_version=3)
        log("  ID3 tags written.", verbose)
    except Exception as exc:
        log(f"  Warning: could not write ID3 tags: {exc}", verbose)


def convert_file(source: Path, output_dir: Path, verbose: bool) -> bool:
    """Convert one file to MP3. Returns True on success."""
    meta        = read_metadata(source, verbose)
    stem        = output_stem(source, meta)
    output_path = unique_path(output_dir, stem)

    log(f"  Output: {output_path.name}", verbose)
    log("  Running ffmpeg (libmp3lame VBR V0, ~245 kbps avg) ...", verbose)

    # -q:a 0 = LAME VBR quality 0 (highest, ~245 kbps avg)
    # -map_metadata 0 = copy all source metadata streams
    # -id3v2_version 3 = write ID3v2.3 (widest compatibility)
    # -loglevel: warning in normal mode, info in verbose
    loglevel = 'info' if verbose else 'warning'
    cmd = [
        'ffmpeg',
        '-loglevel', loglevel,
        '-i', str(source),
        '-vn',
        '-codec:a', 'libmp3lame',
        '-q:a', '0',
        '-map_metadata', '0',
        '-id3v2_version', '3',
        '-y',
        str(output_path),
    ]
    log(f"  Command: {' '.join(cmd)}", verbose)

    result = subprocess.run(cmd, text=True, capture_output=not verbose)

    if result.returncode != 0:
        print(f"  ERROR: ffmpeg failed (exit {result.returncode})")
        if not verbose and result.stderr:
            print(result.stderr.strip())
        return False

    # Second pass: guarantee ID3 tags are present and correctly typed
    write_id3(output_path, meta, verbose)

    print(f"  -> {output_path.name}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Convert .m4a/.m4b/.webm/.mp4 to high-quality MP3 with ID3 tags.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--input',  '-i', required=True,
                        help='Input directory containing source audio files')
    parser.add_argument('--output', '-o',
                        help='Output directory (default: <cwd>/output/)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed step-by-step progress')
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    if not input_dir.is_dir():
        print(f"Error: input directory not found: {input_dir}")
        sys.exit(1)

    output_dir = Path(args.output).expanduser().resolve() if args.output \
                 else Path.cwd() / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input  : {input_dir}")
    print(f"Output : {output_dir}")

    files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"No supported files ({', '.join(SUPPORTED_EXTENSIONS)}) found in {input_dir}")
        sys.exit(0)

    print(f"Found  : {len(files)} file(s)\n")

    success = failed = 0
    for idx, source in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {source.name}")
        if convert_file(source, output_dir, args.verbose):
            success += 1
        else:
            failed += 1

    print(f"\n{'─' * 50}")
    print(f"Converted : {success}   Failed : {failed}")
    print(f"Output dir: {output_dir}")


if __name__ == '__main__':
    main()
