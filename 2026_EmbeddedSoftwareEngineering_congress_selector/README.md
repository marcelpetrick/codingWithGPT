# ESE Kongress 2026 – Programm-Selektor

A small tool for browsing the [Embedded Software Engineering Kongress
2026](https://ese-kongress.de/frontend/index.php?page_id=53095&v=TimeTable)
programme more comfortably than the conference website allows: every abstract on
mouseover instead of a click and a page load, a mark for the talks you want to
attend, and a highlight for the sessions about **project management**, **team
management / leadership**, **agentic AI usage** and **scaling of projects and
teams**.

The repository contains code only. Everything else — the Python packages, the
schedule data, the viewer payload — is fetched and built on first start.

## Run it

```bash
python3 run.py          # Linux, macOS
py run.py               # Windows
```

That is the whole setup. `run.py` needs nothing but a Python 3.9+ installation
and does the rest itself:

1. creates `.venv/` and installs `requirements.txt` into it,
2. downloads the schedule into `data/raw/` (~140 pages, one polite request at a
   time, roughly two minutes),
3. builds `data/congress.json` and `web/data.js`,
4. opens the viewer in your browser.

A second run does no network I/O at all and is done in about two seconds.

| flag | effect |
| --- | --- |
| `--refresh` | re-download every page instead of reusing `data/raw/` |
| `--serve [PORT]` | serve on `http://localhost:8765` instead of opening `file://` |
| `--no-open` | build only |
| `--no-venv` | use the current interpreter (needs `requests` and `beautifulsoup4`) |
| `--clean` | delete `.venv/`, `data/` and `web/data.js` — back to code only |
| `-v` | list cached pages during the crawl too |

`make run`, `make serve`, `make refresh`, `make report`, `make clean` wrap the
same commands on systems that have `make`.

### Windows

Works the same way, and needed almost no extra effort: `run.py` picks
`.venv\Scripts\python.exe` instead of `.venv/bin/python`, and forces `utf-8` on
stdout so the umlauts in the programme cannot abort a run in a legacy code page
console. Install Python from python.org (tick *Add python.exe to PATH*), then
`py run.py`. No `make`, no shell, no admin rights required.

If your browser refuses `localStorage` on `file://` — Safari does, some hardened
Chrome policies do — your marks would not survive a reload. Use
`python3 run.py --serve` in that case; the viewer then runs on
`http://localhost:8765`.

## Using the viewer

| action | effect |
| --- | --- |
| hover an event | popup with topic, format, duration, speakers and the full abstract |
| click an event | mark / unmark it (stored in `localStorage`, key `ese2026.marks`) |
| category chips | dim everything else; with *nur Treffer* the rest is hidden |
| search field | full text over title, subtitle, abstract, speakers and rooms |
| *Markierte …* | export the selection as Markdown, JSON or iCal, or import a JSON export back |
| Kalender / Liste | calendar grid per day, or a flat list (search and *nur markierte* switch to all days) |
| Esc | close the popup |

The selected day, the filters and the marks survive a reload. The marks live in
your browser only — nothing is uploaded anywhere.

## How it works

```
run.py               bootstrap: venv -> deps -> crawl -> build -> browser
crawler/crawl.py     ese-kongress.de  ->  data/raw/*.html   (verbatim copy)
crawler/parse.py     data/raw/        ->  data/congress.json + web/data.js
crawler/classify.py  keyword rules for the four highlight categories
web/                 the viewer: index.html + style.css + app.js
```

The schedule is a server-rendered Converia 9.4 frontend, so plain HTTP requests
are enough — no browser automation:

| page | URL | contains |
| --- | --- | --- |
| timetable | `v=TimeTable&do=0&day=<id>` | the calendar grid of one day: rooms, times, links to every event |
| session | `v=List&do=15&day=<id>&ses=<id>` | one session with all contributions **including the full abstract** |
| general event | `v=List&do=16&day=<id>&ev=<id>` | breaks, exhibition slots, get-together |

The *Details anzeigen* button on the site only toggles a CSS class; the abstract
is already in the delivered markup. That is why fetching the page reproduces
what a click would show. Only the day id to start from is passed in
(`--start-day`, default `6480` = Monday 30.11.2026) — the site's own day
switcher supplies the rest.

Typical result: 6 days, 133 events, 116 contributions, all with an abstract, 31
topics.

## Highlighting

`crawler/classify.py` scores every event with regex keyword rules over its
topic, title, subtitle and abstracts. Hits are weighted by where they appear —
topic 4, title 3, subtitle 2, abstract 1, counted per distinct keyword — and a
category sticks at a score of 3 or more. Below that it is kept as a *weak*
match, shown only when *schwache Treffer* is ticked.

| category | badge | events (strong / weak) |
| --- | --- | --- |
| `project-management` | Projekt | 6 / 35 |
| `team-management` | Team | 8 / 26 |
| `agentic-ai` | Agentic AI | 25 / 5 |
| `scaling` | Skalierung | 2 / 18 |

The viewer never highlights without saying why: the popup lists the matched
keywords per field. Tune the rules in `RULES` and run `make report` — it prints
every tagged event with its score.

The low `scaling` number is real, not a broken rule: nearly every other
"skalier…" in this programme is technical scalability mentioned in passing,
which lands in the weak bucket.

## Notes

* Abstracts are inserted into the popup as HTML and sanitised first
  (`script`/`style`/`iframe` elements, `on*` handlers and `javascript:` URLs are
  removed).
* The programme content belongs to the congress organisers. This tool downloads
  it for personal reading and planning; nothing of it is redistributed here,
  which is why `data/` is git-ignored.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).

Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. It is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.
