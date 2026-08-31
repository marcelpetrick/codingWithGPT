#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""One command that turns this repository into a browsable congress programme.

The repo ships code only. This script provisions everything else:

    1. create .venv and install requirements.txt into it   (only when needed)
    2. download the schedule from ese-kongress.de           (cached in data/raw)
    3. build data/congress.json and web/data.js             (parse + classify)
    4. open the viewer                                      (file:// or --serve)

It uses nothing but the Python standard library, so it runs on a bare Python
3.9+ install on Linux, macOS and Windows:

    python3 run.py                 # Linux / macOS
    py run.py                      # Windows

Useful flags:

    --refresh        re-download every page instead of using data/raw
    --serve [PORT]   serve on http://localhost:PORT instead of opening file://
    --no-open        build only, do not start a browser
    --no-venv        use the current interpreter (requests + bs4 must be there)
    --clean          remove .venv and all downloaded/generated data
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP = VENV_DIR / ".requirements.sha256"
RAW_DIR = ROOT / "data" / "raw"
JSON_PATH = ROOT / "data" / "congress.json"
WEB_DIR = ROOT / "web"
WEB_DATA = WEB_DIR / "data.js"
VIEWER = WEB_DIR / "index.html"

IS_WINDOWS = os.name == "nt"


def announce(message: str) -> None:
    print(f"\n==> {message}", flush=True)


def venv_python() -> Path:
    """Interpreter inside .venv -- Windows puts it in Scripts\\, POSIX in bin/."""
    if IS_WINDOWS:
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run(command: list, description: str) -> None:
    print(f"    $ {' '.join(str(part) for part in command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"\n{description} failed (exit {result.returncode}).")


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def ensure_venv() -> Path:
    """Create .venv and install the dependencies, skipping work already done."""
    python = venv_python()

    if not python.exists():
        announce(f"creating virtual environment in {VENV_DIR.name}/")
        try:
            import venv  # stdlib, but Debian/Ubuntu split it into python3-venv

            venv.EnvBuilder(with_pip=True, clear=False).create(VENV_DIR)
        except Exception as error:  # noqa: BLE001 - the hint matters more than the type
            raise SystemExit(
                f"could not create a virtual environment: {error}\n"
                "On Debian/Ubuntu install it with:  sudo apt install python3-venv\n"
                "Or run with --no-venv if requests and beautifulsoup4 are already installed."
            )

    wanted = requirements_hash()
    if STAMP.exists() and STAMP.read_text(encoding="utf-8").strip() == wanted:
        print(f"    dependencies already installed ({VENV_DIR.name}/)")
        return python

    announce("installing dependencies")
    run([str(python), "-m", "pip", "install", "--upgrade", "--disable-pip-version-check",
         "--quiet", "-r", str(REQUIREMENTS)], "pip install")
    STAMP.write_text(wanted + "\n", encoding="utf-8")
    return python


def check_current_interpreter() -> Path:
    missing = []
    for module in ("requests", "bs4"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        raise SystemExit(
            f"--no-venv was given but {', '.join(missing)} is not importable.\n"
            f"Install them with:  {sys.executable} -m pip install -r {REQUIREMENTS}"
        )
    return Path(sys.executable)


def crawl(python: Path, args) -> None:
    have_copy = RAW_DIR.exists() and any(RAW_DIR.glob("*.html"))
    announce("refreshing the local copy of the schedule" if args.refresh
             else "downloading the schedule" if not have_copy
             else "checking the local copy of the schedule")

    command = [str(python), str(ROOT / "crawler" / "crawl.py"),
               "--start-day", str(args.start_day), "--delay", str(args.delay)]
    if args.refresh:
        command.append("--force")
    if not args.verbose:
        command.append("--quiet")

    try:
        run(command, "crawling")
    except SystemExit:
        if not have_copy:
            raise
        print("    download failed -- continuing with the copy already in data/raw/")


def build(python: Path) -> None:
    announce("building data/congress.json and web/data.js")
    run([str(python), str(ROOT / "crawler" / "parse.py")], "parsing")


def serve(port: int, open_browser: bool) -> None:
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from functools import partial

    handler = partial(SimpleHTTPRequestHandler, directory=str(WEB_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/index.html"

    announce(f"serving {url}   (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        server.server_close()


def open_viewer() -> None:
    url = VIEWER.as_uri()
    announce(f"opening {url}")
    if not webbrowser.open(url):
        print("    no browser could be started -- open this file yourself:")
        print(f"    {VIEWER}")


def clean() -> None:
    for path in (VENV_DIR, ROOT / "data", WEB_DATA):
        if path.is_dir():
            shutil.rmtree(path)
            print(f"    removed {path.relative_to(ROOT)}/")
        elif path.exists():
            path.unlink()
            print(f"    removed {path.relative_to(ROOT)}")
    print("clean.")


def main() -> int:
    # Windows consoles still default to a legacy code page; the programme is
    # full of umlauts, so make sure printing them cannot abort the run.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true",
                        help="re-download every page instead of reusing data/raw/")
    parser.add_argument("--serve", nargs="?", type=int, const=8765, metavar="PORT",
                        help="serve the viewer on http://localhost:PORT (default 8765)")
    parser.add_argument("--no-open", action="store_true", help="build only, do not open a browser")
    parser.add_argument("--no-venv", action="store_true",
                        help="use the current interpreter instead of creating .venv")
    parser.add_argument("--clean", action="store_true",
                        help="remove .venv and every downloaded or generated file")
    parser.add_argument("--start-day", type=int, default=6480,
                        help="day id to bootstrap the crawl from (default: %(default)s)")
    parser.add_argument("--delay", type=float, default=0.7,
                        help="seconds between requests (default: %(default)s)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show every cached page during the crawl")
    args = parser.parse_args()

    if args.clean:
        announce("removing generated files")
        clean()
        return 0

    if sys.version_info < (3, 9):
        raise SystemExit(f"Python 3.9+ required, this is {sys.version.split()[0]}")

    python = check_current_interpreter() if args.no_venv else ensure_venv()
    crawl(python, args)
    build(python)

    if not JSON_PATH.exists() or not WEB_DATA.exists():
        raise SystemExit("the build produced no data -- see the output above")

    if args.serve is not None:
        serve(args.serve, not args.no_open)
    elif not args.no_open:
        open_viewer()
    else:
        announce(f"ready: {VIEWER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
