"""
dirtree.py
----------
Recursively scan a directory and show *where the disk space went*:

* a plain-text top-N list of the largest directories, printed to the console
* an interactive treemap written to ``dirtree.html`` (rectangle area == size),
  clickable to drill down, click the header bar to go back up

Usage::

    python dirtree.py .                     # current directory
    python dirtree.py C:\\                   # whole drive (Windows)
    python dirtree.py / -x                  # whole root filesystem (Linux/macOS)
    python dirtree.py / -x --min-mb 500     # hide clutter below 500 MB

Runs on Windows, Linux and macOS with CPython >= 3.7.
Only dependency is *plotly* (see requirements.txt).
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

import plotly.graph_objects as go

MEBIBYTE = 1024 * 1024


def human_size(num_bytes: float) -> str:
    """Format a byte count with binary (1024-based) units."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def scan_dir(root: str, one_filesystem: bool = False):
    """Return ``(sizes, errors)`` where *sizes* maps directory -> recursive bytes.

    Symlinks (and Windows junctions) are never followed, so no loops.
    Hardlinked files are counted once, like ``du``.
    With *one_filesystem* the scan stays on the device of *root* (like ``du -x``);
    on Windows ``st_dev`` is the volume serial, so that means "stay on this drive".
    """
    sizes: dict[str, int] = {}
    errors = 0
    walk_order: list[str] = []          # parents always before their children
    own_files: dict[str, int] = {}      # bytes of the files directly inside a dir
    children: dict[str, list[str]] = {}

    seen_dirs: set[tuple[int, int]] = set()   # (dev, ino) - loop guard
    seen_hardlinks: set[tuple[int, int]] = set()

    try:
        root_dev = os.stat(root).st_dev
    except OSError:
        root_dev = None

    def keep_dir(path: str) -> bool:
        """Decide whether to descend into *path* (also does the loop guard)."""
        nonlocal errors
        try:
            info = os.stat(path, follow_symlinks=False)
        except OSError:
            errors += 1
            return False

        if one_filesystem and root_dev is not None and info.st_dev != root_dev:
            return False

        key = (info.st_dev, info.st_ino)
        if key in seen_dirs:
            return False
        seen_dirs.add(key)
        return True

    keep_dir(root)

    stack = [root]
    while stack:
        current = stack.pop()
        walk_order.append(current)
        file_bytes = 0
        sub_dirs: list[str] = []

        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if keep_dir(entry.path):
                                sub_dirs.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            info = entry.stat(follow_symlinks=False)
                            if getattr(info, "st_nlink", 1) > 1:
                                key = (info.st_dev, info.st_ino)
                                if key in seen_hardlinks:
                                    continue
                                seen_hardlinks.add(key)
                            file_bytes += info.st_size
                    except OSError:
                        errors += 1
        except OSError:
            errors += 1

        own_files[current] = file_bytes
        children[current] = sub_dirs
        stack.extend(sub_dirs)

    # Bottom-up accumulation: reversed discovery order visits children first.
    for path in reversed(walk_order):
        sizes[path] = own_files[path] + sum(sizes.get(c, 0) for c in children[path])

    return sizes, errors


def build_treemap(root: str, sizes: dict[str, int], minimum: int) -> go.Figure:
    """Assemble the plotly treemap for all directories at or above *minimum*."""
    included = {p for p, size in sizes.items() if size >= minimum or p == root}

    ids, labels, parents, values, hover, text = [], [], [], [], [], []

    for path in included:
        if path == root:
            parent = ""
            label = os.path.basename(root.rstrip(os.sep)) or root
        else:
            parent_path = os.path.dirname(path)
            # Walk up until we hit an ancestor that survived the size filter.
            while parent_path not in included and parent_path != root:
                next_up = os.path.dirname(parent_path)
                if next_up == parent_path:      # reached the filesystem root
                    break
                parent_path = next_up
            parent = parent_path
            label = os.path.basename(path)

        ids.append(path)
        labels.append(label)
        parents.append(parent)
        values.append(sizes[path])
        hover.append(f"{path}<br><b>{human_size(sizes[path])}</b>")
        text.append(f"{label}<br>{human_size(sizes[path])}")

    figure = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            text=text,
            customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
            texttemplate="%{text}",
        )
    )
    figure.update_layout(
        title=f"Disk usage: {root} \u2014 {human_size(sizes[root])}",
        margin=dict(t=50, l=5, r=5, b=5),
    )
    return figure


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive directory disk-usage treemap (Windows/Linux/macOS)"
    )
    parser.add_argument("path", nargs="?", default=".", help="directory to scan")
    parser.add_argument(
        "--min-mb",
        type=float,
        default=10,
        help="hide directories smaller than this in the treemap (default: 10 MB)",
    )
    parser.add_argument(
        "-x",
        "--one-filesystem",
        action="store_true",
        help="do not cross mount points / drive boundaries (like 'du -x')",
    )
    parser.add_argument(
        "--top", type=int, default=25, help="how many directories to list (default: 25)"
    )
    parser.add_argument(
        "--output", default="dirtree.html", help="HTML output file (default: dirtree.html)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="do not open the result in a browser"
    )
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"Not a directory: {root}")
        sys.exit(1)

    print(f"Scanning: {root}")
    print("This may take a little while on large drives...\n")

    sizes, errors = scan_dir(root, one_filesystem=args.one_filesystem)

    total = sizes[root]
    print(f"Total: {human_size(total)}")
    print(f"Directories scanned: {len(sizes):,}")
    if errors:
        print(f"Skipped inaccessible entries: {errors:,}")

    largest = sorted(
        ((p, s) for p, s in sizes.items() if p != root), key=lambda x: x[1], reverse=True
    )[: args.top]

    if largest:
        print("\nLargest directories:")
        print("-" * 70)
        for path, size in largest:
            print(f"{human_size(size):>10}  {os.path.relpath(path, root)}")

    if total == 0:
        print("\nNothing to plot: no files found (or everything was inaccessible).")
        return

    figure = build_treemap(root, sizes, int(args.min_mb * MEBIBYTE))
    output = os.path.abspath(args.output)
    figure.write_html(output, include_plotlyjs=True)

    print("\nInteractive map written to:")
    print(output)
    print("\nClick a rectangle to zoom into that directory.")
    print("Click the top bar to go back up.")

    if not args.no_browser:
        try:
            webbrowser.open(Path(output).as_uri())
        except Exception as exc:                      # headless box, no browser, ...
            print(f"\nCould not open a browser ({exc}); open the file manually.")


if __name__ == "__main__":
    main()
