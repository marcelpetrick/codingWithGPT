#!/usr/bin/env python3
"""Crawl the ESE Kongress 2026 conference schedule into a local raw HTML copy.

The public schedule (Converia 9.4) is served as plain server-rendered HTML:

  * TimeTable view  -- one page per conference day, calendar grid of all events
      index.php?page_id=53095&v=TimeTable&do=0&day=<DAY_ID>
  * session detail  -- one page per session, contains every contribution
                       ("paper") of that session *including* the full abstract
                       (the "Details anzeigen" button only toggles CSS, the text
                       is already in the markup, so no JS/browser is required)
      index.php?page_id=53095&v=List&do=15&day=<DAY_ID>&ses=<SESSION_ID>
  * general event   -- breaks, keynotes-without-session, get-together, ...
      index.php?page_id=53095&v=List&do=16&day=<DAY_ID>&ev=<EVENT_ID>

This script only downloads and stores; parsing happens in parse.py so that the
raw copy stays authoritative and re-parsing never needs the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://ese-kongress.de/frontend/index.php"
PAGE_ID = 53095
DEFAULT_START_DAY = 6480  # Monday, 30.11.2026 -- the entry point given by the user

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.json"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 ese-kongress-local-copy/1.0"
)

DAY_LINK_RE = re.compile(r"v=TimeTable[^\"']*?&(?:amp;)?day=(\d+)")
SESSION_LINK_RE = re.compile(r"&(?:amp;)?ses=(\d+)")
GENERAL_EVENT_LINK_RE = re.compile(r"&(?:amp;)?ev=(\d+)")


class Crawler:
    def __init__(self, delay: float = 0.7, force: bool = False, timeout: int = 30):
        self.delay = delay
        self.force = force
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "de,en;q=0.8"})
        self.manifest: dict[str, dict] = {}
        self._last_request = 0.0

    # -- plumbing ---------------------------------------------------------
    def _throttle(self) -> None:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def fetch(self, params: dict, filename: str, attempts: int = 3) -> str:
        """Fetch one page and store it verbatim under data/raw/<filename>."""
        target = RAW_DIR / filename
        if target.exists() and not self.force:
            print(f"  cached  {filename}")
            return target.read_text(encoding="utf-8")

        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                self._throttle()
                response = self.session.get(BASE_URL, params=params, timeout=self.timeout)
                response.raise_for_status()
                # Converia declares utf-8 in <meta>; requests guesses latin-1 for
                # text/html without charset, so pin it explicitly.
                response.encoding = "utf-8"
                html = response.text
                target.write_text(html, encoding="utf-8")
                self.manifest[filename] = {
                    "url": response.url,
                    "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "status": response.status_code,
                    "bytes": len(html.encode("utf-8")),
                    "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                }
                print(f"  fetched {filename} ({len(html):,} chars)")
                return html
            except Exception as exc:  # network hiccups are expected, retry
                last_error = exc
                print(f"  retry {attempt}/{attempts} for {filename}: {exc}", file=sys.stderr)
                time.sleep(2.0 * attempt)
        raise RuntimeError(f"failed to fetch {filename}: {last_error}")

    # -- crawl steps ------------------------------------------------------
    def discover_days(self, start_day: int) -> list[int]:
        """Read the day switcher of one timetable page to learn every day id."""
        html = self.fetch(
            {"page_id": PAGE_ID, "v": "TimeTable", "do": 0, "day": start_day},
            f"timetable_day_{start_day}.html",
        )
        days: list[int] = []
        for match in DAY_LINK_RE.finditer(html):
            day_id = int(match.group(1))
            if day_id not in days:
                days.append(day_id)
        if start_day not in days:
            days.insert(0, start_day)
        return sorted(days)

    def run(self, start_day: int) -> dict:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        if MANIFEST_PATH.exists():
            self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("files", {})

        print(f"discovering conference days from day={start_day} ...")
        days = self.discover_days(start_day)
        print(f"found {len(days)} days: {days}")

        totals = {"days": len(days), "sessions": 0, "general_events": 0}
        for day_id in days:
            print(f"day {day_id}:")
            timetable = self.fetch(
                {"page_id": PAGE_ID, "v": "TimeTable", "do": 0, "day": day_id},
                f"timetable_day_{day_id}.html",
            )
            session_ids = sorted({int(m.group(1)) for m in SESSION_LINK_RE.finditer(timetable)})
            event_ids = sorted({int(m.group(1)) for m in GENERAL_EVENT_LINK_RE.finditer(timetable)})
            print(f"  {len(session_ids)} sessions, {len(event_ids)} general events")

            for session_id in session_ids:
                self.fetch(
                    {"page_id": PAGE_ID, "v": "List", "do": 15, "day": day_id, "ses": session_id},
                    f"session_{session_id}.html",
                )
                totals["sessions"] += 1
            for event_id in event_ids:
                # General events (breaks etc.) repeat across days; one copy is enough.
                self.fetch(
                    {"page_id": PAGE_ID, "v": "List", "do": 16, "day": day_id, "ev": event_id},
                    f"generalevent_{event_id}.html",
                )
                totals["general_events"] += 1

        MANIFEST_PATH.write_text(
            json.dumps(
                {
                    "source": BASE_URL,
                    "page_id": PAGE_ID,
                    "days": days,
                    "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "files": dict(sorted(self.manifest.items())),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\ndone: {totals}, manifest -> {MANIFEST_PATH.relative_to(REPO_ROOT)}")
        return totals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-day", type=int, default=DEFAULT_START_DAY,
                        help="day id to bootstrap day discovery from (default: %(default)s)")
    parser.add_argument("--delay", type=float, default=0.7,
                        help="seconds between requests, be polite (default: %(default)s)")
    parser.add_argument("--force", action="store_true",
                        help="re-download pages that already exist in data/raw/")
    args = parser.parse_args()

    Crawler(delay=args.delay, force=args.force).run(args.start_day)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
