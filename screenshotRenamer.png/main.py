# main.py
#!/usr/bin/env python3
"""
Screenshot renamer tool.

Renames all PNG files in a directory, ordered by modification time,
to img00.png, img01.png, ..., up to img99.png.

The operation will abort without changing anything if:
- the directory does not exist or is not a directory
- there are no PNG files
- there are more than 100 PNG files
- any of the target names already exists for a file that is not being renamed
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


class ScreenshotRenamerError(Exception):
    """Raised when the screenshot renamer encounters a recoverable error."""


@dataclass
class RenamePlanEntry:
    """Single rename step for a file."""
    src: Path
    tmp: Path
    dst: Path


PNG_EXTENSIONS = {".png"}


def find_pngs(directory: Path) -> List[Path]:
    """
    Find all PNG files in the given directory, sorted by modification time.

    :param directory: Directory to search.
    :return: List of Paths, sorted by mtime ascending.
    :raises ScreenshotRenamerError: if directory is invalid or empty.
    """
    if not directory.exists():
        raise ScreenshotRenamerError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise ScreenshotRenamerError(f"Not a directory: {directory}")

    files: List[Path] = []
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() in PNG_EXTENSIONS:
            files.append(entry)

    if not files:
        raise ScreenshotRenamerError(f"No PNG files found in: {directory}")

    files.sort(key=lambda p: p.stat().st_mtime)
    return files


def build_rename_plan(files: Sequence[Path]) -> List[RenamePlanEntry]:
    """
    Build a two-phase rename plan for the given files.

    All files are renamed to imgNN.png (NN zero-padded, starting at 00)
    in the order given.

    :param files: Sequence of Paths to rename.
    :return: List of RenamePlanEntry objects.
    :raises ScreenshotRenamerError: if constraints are violated.
    """
    n = len(files)
    if n > 100:
        raise ScreenshotRenamerError(
            f"Too many PNG files ({n}); tool only supports up to 100 (img00.png–img99.png)."
        )

    directory = files[0].parent
    existing_names = {p.name for p in directory.iterdir() if p.is_file()}
    target_names = [f"img{i:02d}.png" for i in range(n)]
    source_names = {p.name for p in files}

    # Avoid clobbering unrelated files.
    for name in target_names:
        if name in existing_names and name not in source_names:
            raise ScreenshotRenamerError(
                f"Target file already exists and is not part of the rename set: {name}"
            )

    temp_prefix = f".tmp_screenshot_renamer_{uuid.uuid4().hex}_"
    plan: List[RenamePlanEntry] = []

    for i, src in enumerate(files):
        dst = directory / target_names[i]
        tmp = directory / f"{temp_prefix}{i}"
        plan.append(RenamePlanEntry(src=src, tmp=tmp, dst=dst))

    return plan


def execute_rename_plan(plan: Sequence[RenamePlanEntry]) -> None:
    """
    Execute a two-phase rename plan.

    Phase 1: src -> tmp
    Phase 2: tmp -> dst

    Best-effort rollback is attempted if a filesystem error occurs.

    :param plan: Rename plan entries.
    :raises ScreenshotRenamerError: if a filesystem error occurs.
    """
    try:
        # Sanity check: no temp file collisions.
        for entry in plan:
            if entry.tmp.exists():
                raise ScreenshotRenamerError(
                    f"Temporary filename already exists (refusing to overwrite): {entry.tmp}"
                )

        # Phase 1: move sources to temporary names.
        for entry in plan:
            os.rename(entry.src, entry.tmp)

        # Phase 2: move temporary files to final destinations.
        for entry in plan:
            os.rename(entry.tmp, entry.dst)

    except OSError as exc:
        # Best-effort rollback.
        for entry in plan:
            if entry.tmp.exists() and not entry.src.exists():
                try:
                    os.rename(entry.tmp, entry.src)
                except OSError:
                    # Rollback failed; nothing more we can do.
                    pass

        raise ScreenshotRenamerError(f"File system error during rename: {exc}") from exc


def rename_screenshots(directory: Path) -> None:
    """
    High-level operation: find PNGs in directory and rename them.

    :param directory: Directory containing screenshots.
    """
    files = find_pngs(directory)
    plan = build_rename_plan(files)
    execute_rename_plan(plan)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """
    Parse command-line arguments.

    :param argv: Argument list (excluding program name).
    :return: argparse.Namespace with parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Rename PNG screenshots in a directory to img00.png, img01.png, ... "
            "ordered by modification time."
        )
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory containing screenshots (default: current directory).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Entry point for the CLI.

    :param argv: Optional sequence of arguments, for testing.
    :return: Process exit code (0 on success, non-zero on error).
    """
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)
    directory = Path(args.directory).resolve()

    try:
        rename_screenshots(directory)
    except ScreenshotRenamerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
