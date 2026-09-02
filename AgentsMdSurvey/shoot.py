#!/usr/bin/env python3
"""Regenerate the screenshot collection in media/ from the report.

    ./shoot.py            # redacted report -> nine images in media/
    ./shoot.py --keep     # reuse out/report.html instead of regenerating it

Frames are defined by the heading they start and the heading they stop at, and
the offsets come from the browser's own layout — so the collection survives the
report growing a section, instead of silently cropping the wrong thing.

The report is regenerated with --redact first: everything in media/ is meant to
leave the machine. Requires chromium (or Chrome) and Pillow.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "out" / "report.html"
MEDIA = HERE / "media"

WIDTH = 1180
SCALE = 2  # retina, so the text survives LinkedIn's re-compression
CAPTURE_HEIGHT = 8000  # one screenshot cannot exceed the browser's texture limit

# name, theme, first anchor, anchor to stop before, hard height cap
FRAMES: tuple[tuple[str, str, str, str | None, int | None], ...] = (
    ("01-headline-numbers", "light", "h1:What my agent", "h2:Findings", None),
    ("02-coverage-of-active-repos", "light", "finding:actively maintained", "finding:", None),
    ("03-topic-frequency", "light", "h2:What the instructions are about", "h3:By theme", None),
    ("04-themes-and-binding", "light", "h3:By theme", "h2:The context budget", None),
    ("05-context-budget", "light", "h2:The context budget", "h2:Where the files live", None),
    ("06-canonical-agents-md", "light", "h2:The synthesized house standard", None, 1090),
    ("07-naming-inconsistency", "light", "finding:The agents file is spelled", "finding:", None),
    ("08-topic-frequency-dark", "dark", "h2:What the instructions are about", "h3:By theme", None),
    ("09-repeated-wordings", "light", "h2:Wordings carried between repositories", None, 950),
)

PROBE = """
<script>
const out = [];
document.querySelectorAll('h1,h2,h3,.finding,.tiles').forEach(el => {
  const r = el.getBoundingClientRect();
  out.push({
    kind: el.tagName.toLowerCase().startsWith('h') ? el.tagName.toLowerCase() : 'finding',
    top: Math.round(r.top + window.scrollY),
    height: Math.round(r.height),
    text: (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 80),
  });
});
document.title = 'MARKS' + JSON.stringify(out);
</script>
</body>"""

# Drops everything before a heading, so a section far down the page can be
# photographed at full resolution instead of falling outside the capture.
LIFT = """
<script>
const wanted = %s;
const wrap = document.querySelector('.wrap');
const kids = [...wrap.children];
const start = kids.findIndex(el => el.tagName === 'H2' && el.textContent.trim() === wanted);
if (start > 0) kids.forEach((el, i) => { if (i < start) el.remove(); });
</script>
</body>"""


def browser() -> str:
    for candidate in ("chromium", "chromium-browser", "google-chrome-stable", "google-chrome"):
        found = shutil.which(candidate)
        if found:
            return found
    raise SystemExit("no chromium or chrome on PATH")


def shot(binary: str, page: Path, target: Path, height: int) -> None:
    subprocess.run(
        [
            binary, "--headless", "--disable-gpu", "--hide-scrollbars",
            f"--force-device-scale-factor={SCALE}",
            f"--window-size={WIDTH},{height}",
            "--virtual-time-budget=3000",
            f"--screenshot={target}",
            page.as_uri(),
        ],
        capture_output=True,
        check=True,
        timeout=180,
    )


def measure(binary: str, page: Path) -> list[dict]:
    result = subprocess.run(
        [binary, "--headless", "--disable-gpu", "--virtual-time-budget=3000",
         f"--window-size={WIDTH},900", "--dump-dom", page.as_uri()],
        capture_output=True, text=True, check=True, timeout=180,
    )
    for line in result.stdout.splitlines():
        marker = line.find("MARKS[")
        if marker >= 0:
            payload = line[marker + 5 :]
            return json.loads(payload[: payload.rfind("]") + 1])
    raise SystemExit("the probe returned no layout information")


def find(marks: list[dict], anchor: str, after: int = -1) -> dict | None:
    """Resolve 'kind:text-prefix'. An empty prefix means 'the next one of that kind'."""
    kind, _, prefix = anchor.partition(":")
    for mark in marks:
        if mark["top"] <= after or mark["kind"] != kind:
            continue
        if not prefix or mark["text"].lower().startswith(prefix.lower()) or prefix.lower() in mark["text"].lower()[:90]:
            return mark
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep", action="store_true", help="reuse the existing out/report.html")
    args = parser.parse_args(argv)

    from PIL import Image  # imported late so --help works without Pillow

    if not args.keep:
        run = subprocess.run(
            [sys.executable, str(HERE / "run.py"), "--out", str(HERE / "out"), "--redact"],
            text=True, capture_output=True,
        )
        if run.returncode != 0:
            sys.stderr.write(run.stderr)
            return run.returncode
        sys.stderr.write(run.stderr)
    if not REPORT.exists():
        raise SystemExit(f"no report at {REPORT}")

    binary = browser()
    html = REPORT.read_text(encoding="utf-8")
    MEDIA.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        pages = {
            "light": work / "light.html",
            "dark": work / "dark.html",
            "probe": work / "probe.html",
        }
        pages["light"].write_text(html, encoding="utf-8")
        pages["dark"].write_text(
            html.replace('<html lang="en">', '<html lang="en" data-theme="dark">'), encoding="utf-8"
        )
        pages["probe"].write_text(html.replace("</body>", PROBE), encoding="utf-8")

        marks = measure(binary, pages["probe"])
        full = {}
        for theme in ("light", "dark"):
            target = work / f"full-{theme}.png"
            shot(binary, pages[theme], target, CAPTURE_HEIGHT)
            full[theme] = Image.open(target)

        written = 0
        for name, theme, start_anchor, stop_anchor, cap in FRAMES:
            start = find(marks, start_anchor)
            if start is None:
                print(f"  ! {name}: anchor {start_anchor!r} not found, skipped", file=sys.stderr)
                continue
            # Lead-in, but never far enough back to catch the tail of whatever
            # sits above: a sliver of the previous card reads as a mistake.
            above = [m for m in marks if m["top"] + m["height"] <= start["top"]]
            floor = max((m["top"] + m["height"] + 6 for m in above), default=0)
            top = max(0, floor, start["top"] - 20)

            if cap is not None or top + 200 > CAPTURE_HEIGHT:
                # Too far down to appear in a full-page capture: re-render the
                # page with everything above this heading removed.
                heading = start["text"]
                lifted = work / f"lift-{name}.html"
                lifted.write_text(
                    html.replace("</body>", LIFT % json.dumps(heading)), encoding="utf-8"
                )
                height = cap or 1200
                target = work / f"lift-{name}.png"
                shot(binary, lifted, target, height + 120)
                image = Image.open(target)
                box = (0, 60 * SCALE, image.width, min((60 + height) * SCALE, image.height))
            else:
                stop = find(marks, stop_anchor, after=start["top"]) if stop_anchor else None
                bottom = stop["top"] - 12 if stop else start["top"] + start["height"] + 20
                image = full[theme]
                box = (0, top * SCALE, image.width, min(bottom * SCALE, image.height))

            crop = image.crop(box)
            crop.save(MEDIA / f"{name}.png", optimize=True)
            print(f"  {name}.png  {crop.width}x{crop.height}")
            written += 1

    print(f"wrote {written} images to {MEDIA}", file=sys.stderr)
    return 0 if written == len(FRAMES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
