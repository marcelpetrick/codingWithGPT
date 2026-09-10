#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Marcel Petrick
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Render the ``--demo`` dashboard to ``media/tokenusage2_demo.png``.

The frame is produced by the real renderer, its ANSI colours are translated to
HTML, and headless Chromium takes the screenshot. Demo data is synthetic, so
the image never shows a real account.
"""

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "media" / "tokenusage2_demo.png"
COLUMNS, ROWS = 150, 46
FONT_PX, LINE_PX, CHAR_PX = 14, 17, 8.43
SGR = re.compile(r"\x1b\[([0-9;]*)m")
BASE16 = (
    "#000000",
    "#cd0000",
    "#00cd00",
    "#cdcd00",
    "#0000ee",
    "#cd00cd",
    "#00cdcd",
    "#e5e5e5",
    "#7f7f7f",
    "#ff0000",
    "#00ff00",
    "#ffff00",
    "#5c5cff",
    "#ff00ff",
    "#00ffff",
    "#ffffff",
)


def xterm(index: int) -> str:
    if index < 16:
        return BASE16[index]
    if index < 232:
        index -= 16
        steps = (0, 95, 135, 175, 215, 255)
        red, green, blue = steps[index // 36], steps[index // 6 % 6], steps[index % 6]
        return f"#{red:02x}{green:02x}{blue:02x}"
    grey = 8 + (index - 232) * 10
    return f"#{grey:02x}{grey:02x}{grey:02x}"


def to_html(text: str) -> str:
    out, style = [], ""
    for line in text.splitlines():
        position = 0
        for match in SGR.finditer(line):
            chunk = line[position : match.start()]
            if chunk:
                out.append(f'<span style="{style}">{html.escape(chunk)}</span>')
            codes = [int(code) for code in match.group(1).split(";") if code] or [0]
            fg = bg = None
            bold = False
            index = 0
            while index < len(codes):
                code = codes[index]
                if code == 1:
                    bold = True
                elif code in {38, 48} and index + 2 < len(codes):
                    if code == 38:
                        fg = xterm(codes[index + 2])
                    else:
                        bg = xterm(codes[index + 2])
                    index += 2
                index += 1
            style = ";".join(
                filter(
                    None,
                    (
                        f"color:{fg}" if fg else "",
                        f"background:{bg}" if bg else "",
                        "font-weight:bold" if bold else "",
                    ),
                )
            )
            position = match.end()
        tail = line[position:]
        if tail:
            out.append(f'<span style="{style}">{html.escape(tail)}</span>')
        out.append("\n")
    return "".join(out)


def main() -> int:
    browser = shutil.which("chromium") or shutil.which("google-chrome")
    if browser is None:
        print("screenshot.py needs chromium on PATH", file=sys.stderr)
        return 1
    frame = subprocess.run(
        [
            sys.executable,
            "-m",
            "tokenusage2",
            "--demo",
            "--once",
            "--color",
            "always",
            "--theme",
            "midnight",
            "--tz",
            "Europe/Berlin",
            "--width",
            str(COLUMNS),
            "--height",
            str(ROWS),
        ],
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    page = (
        "<!doctype html><meta charset='utf-8'><style>"
        "html,body{margin:0;background:#1c1c1c}"
        f"pre{{margin:16px;font:{FONT_PX}px/{LINE_PX}px 'DejaVu Sans Mono',monospace;"
        "color:#d0d0d0}</style>"
        f"<pre>{to_html(frame)}</pre>"
    )
    width = int(COLUMNS * CHAR_PX) + 32
    height = ROWS * LINE_PX + 32
    OUTPUT.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        document = Path(scratch) / "frame.html"
        document.write_text(page, encoding="utf-8")
        subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--log-level=3",
                f"--window-size={width},{height}",
                f"--screenshot={OUTPUT}",
                document.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
