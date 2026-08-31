#!/usr/bin/env python3
"""Turn the raw HTML copy in data/raw/ into structured JSON.

Input : data/raw/timetable_day_<id>.html, session_<id>.html, generalevent_<id>.html
Output: data/congress.json          -- canonical, pretty printed, diff friendly
        web/data.js                 -- same payload as `window.CONGRESS_DATA`,
                                       so the viewer also works via file://
                                       (fetch() of a local .json is blocked by
                                       the browsers' CORS rules)

The timetable pages supply the grid facts (which day, which room column, start
and end time); the detail pages supply title, topic, presentation form, speakers
and the full abstract of every contribution.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
JSON_PATH = REPO_ROOT / "data" / "congress.json"
WEB_DATA_PATH = REPO_ROOT / "web" / "data.js"

BASE = "https://ese-kongress.de/frontend/index.php"
PAGE_ID = 53095

TIME_RANGE_RE = re.compile(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s*Uhr")


def text(node) -> str:
    """Collapse Converia's generous template whitespace into a single line."""
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def soup_of(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def minutes(hhmm: str) -> int | None:
    if not hhmm:
        return None
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


# --------------------------------------------------------------------------
# topics (id -> name + legend colour), read from the filter form of any page
# --------------------------------------------------------------------------
def parse_topics(soup: BeautifulSoup) -> dict[str, dict]:
    topics: dict[str, dict] = {}
    for checkbox in soup.select("input.topic_checkbox"):
        topic_id = checkbox.get("id", "").replace("topic_", "")
        label = checkbox.find_parent("label")
        if not topic_id or label is None:
            continue
        colour_div = label.select_one(".topic_color")
        colour = ""
        if colour_div is not None:
            match = re.search(r"background-color:\s*([^;\"]+)", colour_div.get("style", ""))
            colour = match.group(1).strip() if match else ""
        topics[topic_id] = {"id": topic_id, "name": text(label), "color": colour}
    return topics


# --------------------------------------------------------------------------
# timetable pages: day meta, room columns, event placement
# --------------------------------------------------------------------------
def parse_timetable(path: Path) -> dict:
    soup = soup_of(path)
    day_id = path.stem.replace("timetable_day_", "")

    date = text(soup.select_one(".stepper-label"))
    weekday = ""
    for link in soup.select("a.button-timeline"):
        if link.get("title") == date:
            weekday = text(link)
            break

    rooms = [text(node) for node in soup.select("#room_nav .room_headline")]

    placements: list[dict] = []
    for column_index, column in enumerate(soup.select(".column_wrapper > .room")):
        room = rooms[column_index] if column_index < len(rooms) else ""
        for anchor in column.select("a.event"):
            href = anchor.get("href", "")
            session = re.search(r"[?&]ses=(\d+)", href)
            general = re.search(r"[?&]ev=(\d+)", href)
            if session:
                kind, event_id = "session", session.group(1)
            elif general:
                kind, event_id = "general", general.group(1)
            else:
                continue

            block = text(anchor)
            times = TIME_RANGE_RE.search(block)
            classes = anchor.get("class", [])
            topic_id = next((c.replace("topic_", "") for c in classes if c.startswith("topic_")), "")
            event_type = next((c.replace("event_type_", "") for c in classes if c.startswith("event_type_")), "")

            placements.append({
                "kind": kind,
                "event_id": event_id,
                "room": room,
                "room_index": column_index,
                "start": times.group(1) if times else "",
                "end": times.group(2) if times else "",
                "topic_id": topic_id if topic_id not in ("0", event_id) else "",
                "event_type": event_type,
                "title": text(anchor.select_one(".headline")),
            })

    return {
        "id": day_id,
        "date": date,
        "weekday": weekday,
        "rooms": rooms,
        "placements": placements,
        "topics": parse_topics(soup),
    }


# --------------------------------------------------------------------------
# detail pages
# --------------------------------------------------------------------------
def parse_person(anchor) -> dict:
    entity = re.search(r"entity_id=(\d+)", anchor.get("href", ""))
    raw_name = text(anchor.select_one(".schedule-person-name"))
    parts = [p.strip() for p in raw_name.split("|") if p.strip()]
    return {
        "id": entity.group(1) if entity else "",
        "name": parts[0] if parts else raw_name,
        "affiliation": parts[1] if len(parts) > 1 else "",
        "country": parts[2] if len(parts) > 2 else "",
        "display": raw_name,
    }


def parse_paper(node) -> dict:
    anchor = node.select_one('a[name^="anker_paper_"]')
    paper_id = anchor.get("name").replace("anker_paper_", "") if anchor else ""
    star = node.select_one("[data-favorite-setter]")

    detail = node.select_one(".detail_window")
    abstract_html = ""
    abstract_text = ""
    if detail is not None:
        paragraph = detail.find("p")
        if paragraph is not None:
            abstract_html = paragraph.decode_contents().strip()
            abstract_text = paragraph.get_text("\n", strip=True)

    author_lines = [text(a) for a in node.select(".paper_author")]
    author_lines = [a for a in author_lines if a and not a.rstrip(":").strip().endswith(("Autor:in", "Autor:innen", "Autoren"))]

    return {
        "id": paper_id,
        "ident": star.get("data-ident", "") if star else "",
        "time": text(node.select_one(".paper_time_label")).replace(" Uhr", ""),
        "title": text(node.select_one(".paper_headline")),
        "subtitle": text(node.select_one(".paper_subtitle")),
        "persons": [parse_person(a) for a in node.select(".schedule-person-wrapper > a")],
        "authors": author_lines,
        "abstract_html": abstract_html,
        "abstract_text": abstract_text,
    }


def info_item(container, css_class: str) -> str:
    node = container.select_one(f".{css_class}")
    if node is None:
        return ""
    value = text(node)
    label = node.select_one(".info-label")
    if label is not None:
        value = value[len(text(label)):].strip()
    return value.strip(": ").strip()


def parse_session(path: Path) -> dict:
    soup = soup_of(path)
    session_id = path.stem.replace("session_", "")
    content = soup.select_one(".session_content")
    if content is None:
        return {}

    colour = ""
    match = re.search(r"solid\s*([^;\"]*)", content.get("style", ""))
    if match:
        colour = match.group(1).strip()

    return {
        "kind": "session",
        "event_id": session_id,
        "ident": f"2_{session_id}",
        "title": text(content.select_one(".session-headline")),
        "room": info_item(content, "session-info-room"),
        "topic": info_item(content, "session-info-topics"),
        "form": info_item(content, "session-info-form-of-presentation"),
        "duration": info_item(content, "session-info-duration"),
        "direction": info_item(content, "session-info-direction"),
        "color": colour,
        "papers": [parse_paper(p) for p in content.select(".paper_element")],
        "source_url": f"{BASE}?page_id={PAGE_ID}&v=List&do=15&ses={session_id}",
        "raw_file": path.name,
    }


def parse_general_event(path: Path) -> dict:
    soup = soup_of(path)
    event_id = path.stem.replace("generalevent_", "")
    content = soup.select_one(".session_content")
    if content is None:
        return {}

    room = ""
    room_node = content.select_one(".session_room")
    if room_node is not None:
        room = re.sub(r"^\s*Raum\s*:\s*", "", text(room_node)).strip()

    duration = ""
    info = content.select_one(".session_info")
    if info is not None:
        duration = re.sub(r"^\s*Dauer\s*:\s*", "", text(info)).strip()

    return {
        "kind": "general",
        "event_id": event_id,
        "ident": f"1_{event_id}",
        "title": text(content.select_one(".session-headline")),
        "room": room,
        "topic": "",
        "form": "",
        "duration": duration,
        "direction": "",
        "color": "",
        "papers": [],
        "source_url": f"{BASE}?page_id={PAGE_ID}&v=List&do=16&ev={event_id}",
        "raw_file": path.name,
    }


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------
def build() -> dict:
    timetables = [parse_timetable(p) for p in sorted(RAW_DIR.glob("timetable_day_*.html"))]
    details: dict[tuple[str, str], dict] = {}
    for path in sorted(RAW_DIR.glob("session_*.html")):
        parsed = parse_session(path)
        if parsed:
            details[("session", parsed["event_id"])] = parsed
    for path in sorted(RAW_DIR.glob("generalevent_*.html")):
        parsed = parse_general_event(path)
        if parsed:
            details[("general", parsed["event_id"])] = parsed

    # The site's own topic filter form only lists a subset (14 entries, identical
    # on every day), so the registry is built from the events themselves and the
    # form is merged in as a fallback for names/colours.
    topics: dict[str, dict] = {}
    for table in timetables:
        topics.update(table["topics"])

    days: list[dict] = []
    events: list[dict] = []
    for table in sorted(timetables, key=lambda t: tuple(reversed(t["date"].split(".")))):
        seen: dict[str, dict] = {}
        for placement in table["placements"]:
            key = (placement["kind"], placement["event_id"])
            detail = details.get(key, {})
            uid = f"{placement['kind']}_{placement['event_id']}_{table['id']}"

            if uid in seen:  # general events span several room columns
                if placement["room"] and placement["room"] not in seen[uid]["rooms"]:
                    seen[uid]["rooms"].append(placement["room"])
                continue

            topic_id = placement["topic_id"]
            event = {
                "uid": uid,
                "kind": placement["kind"],
                "event_id": placement["event_id"],
                "ident": detail.get("ident", ""),
                "day_id": table["id"],
                "date": table["date"],
                "weekday": table["weekday"],
                "rooms": [placement["room"]] if placement["room"] else [],
                "room_index": placement["room_index"],
                "start": placement["start"],
                "end": placement["end"],
                "start_min": minutes(placement["start"]),
                "end_min": minutes(placement["end"]),
                "title": detail.get("title") or placement["title"],
                "event_type": placement["event_type"],
                "topic_id": topic_id,
                "topic": detail.get("topic") or topics.get(topic_id, {}).get("name", ""),
                "topic_color": detail.get("color") or topics.get(topic_id, {}).get("color", ""),
                "form": detail.get("form", ""),
                "duration": detail.get("duration", ""),
                "direction": detail.get("direction", ""),
                "papers": detail.get("papers", []),
                "source_url": detail.get("source_url", ""),
                "raw_file": detail.get("raw_file", ""),
            }
            seen[uid] = event
            events.append(event)

        days.append({
            "id": table["id"],
            "date": table["date"],
            "weekday": table["weekday"],
            "rooms": table["rooms"],
            "event_uids": list(seen.keys()),
        })

    for event in events:
        topic_id = event["topic_id"] or event["topic"]
        if not topic_id or not event["topic"]:
            continue
        entry = topics.setdefault(topic_id, {"id": topic_id, "name": "", "color": ""})
        entry["name"] = entry["name"] or event["topic"]
        entry["color"] = entry["color"] or event["topic_color"]

    return {
        "conference": "Embedded Software Engineering Kongress 2026",
        "source": f"{BASE}?page_id={PAGE_ID}&v=TimeTable",
        "days": days,
        "topics": dict(sorted(topics.items(), key=lambda kv: kv[1]["name"])),
        "events": events,
    }


def write(data: dict) -> None:
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    WEB_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEB_DATA_PATH.write_text(
        "// Generated by crawler/parse.py -- do not edit by hand.\n"
        "window.CONGRESS_DATA = "
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    data = build()
    write(data)
    papers = sum(len(e["papers"]) for e in data["events"])
    with_abstract = sum(1 for e in data["events"] for p in e["papers"] if p["abstract_text"])
    print(f"days      : {len(data['days'])}")
    print(f"events    : {len(data['events'])}")
    print(f"papers    : {papers} ({with_abstract} with abstract)")
    print(f"topics    : {len(data['topics'])}")
    print(f"written   : {JSON_PATH.relative_to(REPO_ROOT)}, {WEB_DATA_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
