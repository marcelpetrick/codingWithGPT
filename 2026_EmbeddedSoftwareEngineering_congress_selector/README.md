# ESE Kongress 2026 – lokaler Programm-Selektor

A local, offline copy of the [Embedded Software Engineering Kongress
2026](https://ese-kongress.de/frontend/index.php?page_id=53095&v=TimeTable)
programme, plus a viewer that is fast to browse, shows every abstract on
mouseover, remembers which events you marked, and highlights the sessions about
**project management**, **team management / leadership**, **agentic AI usage**
and **scaling of projects and teams**.

```
crawler/crawl.py     ese-kongress.de  ->  data/raw/*.html      (verbatim copy)
crawler/parse.py     data/raw/        ->  data/congress.json + web/data.js
crawler/classify.py  keyword rules for the four highlight categories
web/                 the viewer: index.html + style.css + app.js + data.js
```

## Quick start

The crawled data is committed, so you can just open the viewer:

```bash
xdg-open web/index.html          # or: make open
```

`file://` is enough — the data is a plain `.js` file, not a `fetch()`. If your
browser blocks `localStorage` on `file://` (marks would not survive a reload),
serve the folder instead:

```bash
make serve                       # http://localhost:8765/index.html
```

## Re-crawling

```bash
pip install -r requirements.txt
make crawl                       # skips pages already in data/raw/
make crawl FORCE=1               # refetch everything
make parse                       # rebuild congress.json + web/data.js
```

`crawl.py` bootstraps from a single day id (`--start-day`, default `6480` =
Monday 30.11.2026); the site's day switcher lists all other days, so nothing is
hardcoded. Requests are throttled (`--delay`, default 0.7 s) and retried.

## How the site is scraped

The schedule is a server-rendered Converia 9.4 frontend — no browser automation
needed:

| page | URL | contains |
| --- | --- | --- |
| timetable | `v=TimeTable&do=0&day=<id>` | the calendar grid of one day: rooms, times, links to every event |
| session | `v=List&do=15&day=<id>&ses=<id>` | one session with all contributions **including the full abstract** |
| general event | `v=List&do=16&day=<id>&ev=<id>` | breaks, exhibition slots, get-together |

The "Details anzeigen" button on the site only toggles a CSS class; the abstract
is already in the delivered markup. That is why a plain HTTP fetch reproduces
what a click would show.

Current snapshot (crawled 2026-08-31): **6 days, 133 events, 116 contributions,
all with abstract, 31 topics**.

## Highlighting

`crawler/classify.py` scores every event with regex keyword rules over its
topic, title, subtitle and abstracts. Hits are weighted by position — topic 4,
title 3, subtitle 2, abstract 1, counted per distinct keyword — and a category
sticks at a score of 3 or more. Below that the category is kept as a *weak*
match, shown only when "schwache Treffer" is ticked.

| category | badge | events (strong / weak) |
| --- | --- | --- |
| `project-management` | Projekt | 6 / 35 |
| `team-management` | Team | 8 / 26 |
| `agentic-ai` | Agentic AI | 25 / 5 |
| `scaling` | Skalierung | 2 / 18 |

The viewer never highlights without saying why: the popup lists the matched
keywords per field. Tune the rules in `RULES` and re-run `make report` — it
prints every tagged event with its score.

Note on `scaling`: the low number is real. Almost every other "skalier…" in this
programme is technical scalability mentioned in passing, which lands in the weak
bucket.

## Using the viewer

| action | effect |
| --- | --- |
| hover an event | detail popup: topic, format, duration, speakers, full abstract, link to the original page |
| click an event | mark / unmark (stored in `localStorage`, key `ese2026.marks`) |
| category chips | dim everything else; with "nur Treffer" the rest is hidden |
| search field | full text over title, subtitle, abstract, speakers and rooms |
| "Markierte …" | export the selection as Markdown, JSON or iCal, or import a JSON export back |
| Kalender / Liste | calendar grid per day, or a flat list (searching/marked switches to all days) |
| Esc | close the popup |

Filter state, the selected day and the marks survive a reload.

## Notes

* `data/raw/` is committed on purpose: it keeps the parse reproducible and makes
  the crawler unnecessary for everyday use.
* `data/congress.json` is the canonical output; `web/data.js` is the same
  payload wrapped as `window.CONGRESS_DATA` so the viewer works without a server.
* Abstracts are inserted into the popup as HTML and are sanitised first
  (script/style/iframe elements, `on*` handlers and `javascript:` URLs removed).
* The content belongs to the congress organisers; this is a personal reading and
  planning aid, no redistribution intended.
