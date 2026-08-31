#!/usr/bin/env python3
"""Tag schedule events with the four topics the local viewer highlights.

    project-management   planning, estimation, agile process, risk, roadmaps
    team-management      people, leadership, culture, collaboration, hiring
    agentic-ai           LLMs and autonomous coding agents used in engineering
    scaling              growing projects, products, teams and organisations

Every rule is a plain regular expression evaluated case insensitively against
the event's topic, title, subtitle and the abstracts of its contributions.
Hits are weighted by where they occur -- a keyword in the official topic or in
the title says far more about an event than one buried in a long abstract:

    topic 4, title 3, subtitle 2, abstract 1   (per distinct keyword, not per
                                                occurrence, so a single word
                                                repeated 20 times cannot carry
                                                an event on its own)

An event carries a tag once its score reaches MIN_SCORE. The matched keywords
are kept in the output so the viewer can explain *why* something is highlighted
instead of showing an unaccountable colour.

Usage:
    python3 crawler/classify.py            # re-tag data/congress.json in place
    python3 crawler/classify.py --report   # ... and print what was tagged
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = REPO_ROOT / "data" / "congress.json"

MIN_SCORE = 3
FIELD_WEIGHTS = {"topic": 4, "title": 3, "subtitle": 2, "abstract": 1}

# German first -- the congress is mostly German -- English variants added where
# they actually show up in this programme.
RULES: dict[str, dict] = {
    "project-management": {
        "label": "Projektmanagement",
        "patterns": [
            r"projektmanagement", r"projektleit", r"projektplan", r"projektsteuerung",
            r"project management", r"programm-?management",
            r"\bagil", r"\bscrum\b", r"\bkanban\b", r"\bsprint", r"\bbacklog",
            r"product owner", r"produktmanagement", r"product management",
            r"\broadmap", r"meilenstein", r"\bmilestone",
            r"aufwandsschätzung", r"aufwandsabschätzung", r"\bschätzung", r"\bestimation\b",
            r"projektrisik", r"risikomanagement", r"risk management",
            r"stakeholder", r"time.to.market", r"terminplan", r"\bbudget",
            r"software engineering management", r"entwicklungsprozess",
            r"prozessverbesserung", r"process improvement", r"\bspice\b", r"\bcmmi\b",
            r"lieferfähigkeit", r"projekterfolg", r"projektorganisation",
            r"projektplanung", r"ressourcenplanung", r"releaseplanung",
            r"release.?management", r"priorisier", r"\bdeadline", r"termindruck",
        ],
    },
    "team-management": {
        "label": "Teamführung",
        "patterns": [
            r"\bteam(s|arbeit|struktur|kultur|führung|entwicklung|topolog)?\b",
            r"team topolog", r"cross.functional", r"interdisziplinär",
            r"\bführung", r"\bleadership\b", r"\bleiten\b", r"\bvorgesetzt",
            r"mitarbeiter", r"personalentwicklung", r"\bcoaching\b", r"\bmentor",
            r"unternehmenskultur", r"fehlerkultur", r"\bkultur\b",
            r"zusammenarbeit", r"collaboration", r"kommunikation im team",
            r"psychologische sicherheit", r"psychological safety",
            r"\bmotivation", r"\bkonflikt", r"\bonboarding\b", r"wissenstransfer",
            r"soft.skills", r"mensch, team", r"human centricity",
            r"\brecruit", r"fachkräfte", r"\bhiring\b", r"new work",
            r"selbstorganisier", r"\bself.organi", r"verantwortungsübernahme",
        ],
    },
    "agentic-ai": {
        "label": "Agentic AI",
        "patterns": [
            r"agentic", r"\bki.agent", r"ai.agent", r"autonome(r|n)? agent",
            r"\bagenten\b", r"multi.agent",
            r"\bllm\b", r"large language model", r"sprachmodell",
            r"\bgpt\b", r"chatgpt", r"\bclaude\b", r"claude code", r"\bcopilot\b",
            r"\bcursor\b", r"openai", r"codex", r"\bgemini\b",
            r"generative ki", r"generative ai", r"\bgenai\b",
            r"\bprompt", r"vibe.coding", r"coding assistant", r"code assistant",
            r"\bmcp\b", r"model context protocol", r"retrieval.augmented", r"\brag\b",
            r"ki.gestützt", r"ki.unterstützt", r"ki.basiert", r"ki.einsatz",
            r"ki.gestützte entwicklung", r"künstliche intelligenz",
        ],
    },
    "scaling": {
        "label": "Skalierung",
        "patterns": [
            r"skalier", r"\bscaling\b", r"\bscale\b", r"scale.up", r"skalierbarkeit",
            # "SAFe"/"LeSS" only as the framework names -- matched case
            # sensitively, because a safety congress is full of the words
            # "safe" and "less" ("From Functional Safety to Safe Intelligence").
            r"(?-i:\bSAFe\b)", r"(?-i:\bLeSS\b)", r"scaled agile", r"large.scale scrum",
            r"große(n|s|r)? (projekt|team|organisation)", r"großprojekt",
            r"viele teams", r"mehrere teams", r"multi.team", r"team.of.teams",
            r"verteilte(s|n|r)? (team|entwicklung|standort)", r"standortübergreifend",
            r"\bnearshor", r"\boffshor", r"\bdistributed team",
            r"\bportfolio", r"\benterprise\b", r"unternehmensweit",
            r"wachstum", r"\bgrowth\b", r"organisationsentwicklung",
            r"plattform.team", r"platform engineering", r"\bmonorepo\b",
            r"produktlinie", r"product line", r"variantenmanagement", r"wiederverwendung",
        ],
    },
}

COMPILED = {
    key: [(pattern, re.compile(pattern, re.IGNORECASE)) for pattern in rule["patterns"]]
    for key, rule in RULES.items()
}


def event_fields(event: dict) -> dict[str, str]:
    """Flatten one event into the four weighted text fields."""
    papers = event.get("papers", [])
    return {
        "topic": " ".join(filter(None, [event.get("topic", ""), event.get("form", "")])),
        "title": " ".join(filter(None, [event.get("title", "")] + [p.get("title", "") for p in papers])),
        "subtitle": " ".join(p.get("subtitle", "") for p in papers),
        "abstract": " ".join(p.get("abstract_text", "") for p in papers),
    }


def classify_event(event: dict) -> dict:
    """Return {tag: {score, matches}} for every category that scored at all.

    Categories below MIN_SCORE are kept as well; the caller separates them into
    strong tags and weak ones, so the viewer can optionally show near misses
    without polluting the default view.
    """
    fields = event_fields(event)
    result: dict[str, dict] = {}

    for tag, patterns in COMPILED.items():
        score = 0
        matches: dict[str, list[str]] = {}
        for field, weight in FIELD_WEIGHTS.items():
            haystack = fields[field]
            if not haystack:
                continue
            hits = sorted({
                match.group(0).lower()
                for _, regex in patterns
                for match in [regex.search(haystack)]
                if match
            })
            if hits:
                score += weight * len(hits)
                matches[field] = hits
        if score > 0:
            result[tag] = {"score": score, "matches": matches}
    return result


def annotate(data: dict) -> dict:
    """Add tags + a lowercase search index to every event, in place."""
    for event in data["events"]:
        tags = classify_event(event)
        by_score = sorted(tags, key=lambda t: -tags[t]["score"])
        event["tags"] = [t for t in by_score if tags[t]["score"] >= MIN_SCORE]
        event["weak_tags"] = [t for t in by_score if tags[t]["score"] < MIN_SCORE]
        event["tag_details"] = tags
        fields = event_fields(event)
        event["search_text"] = " ".join([
            fields["topic"], fields["title"], fields["subtitle"], fields["abstract"],
            " ".join(person.get("display", "")
                     for paper in event.get("papers", [])
                     for person in paper.get("persons", [])),
            " ".join(event.get("rooms", [])),
        ]).lower()

    data["tag_definitions"] = {
        key: {"label": rule["label"], "patterns": rule["patterns"]}
        for key, rule in RULES.items()
    }
    data["tag_config"] = {"min_score": MIN_SCORE, "field_weights": FIELD_WEIGHTS}
    return data


def report(data: dict) -> None:
    counts = {key: 0 for key in RULES}
    weak = {key: 0 for key in RULES}
    for event in data["events"]:
        for tag in event["tags"]:
            counts[tag] += 1
        for tag in event["weak_tags"]:
            weak[tag] += 1
    print(f"tagged events per category (strong = score >= {MIN_SCORE}, weak = below):")
    for tag, count in counts.items():
        print(f"  {tag:<20} {count:>3} strong, {weak[tag]:>3} weak")
    print(f"  {'any tag':<20} {sum(1 for e in data['events'] if e['tags']):>3}"
          f" of {len(data['events'])}")
    print()
    for event in sorted(data["events"], key=lambda e: (e["date"], e["start"])):
        if not event["tags"]:
            continue
        tags = ", ".join(f"{t}:{event['tag_details'][t]['score']}" for t in event["tags"])
        print(f"{event['weekday']} {event['start']} [{tags}] {event['title'][:70]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", action="store_true", help="print which events were tagged")
    parser.add_argument("--dry-run", action="store_true", help="do not write data/congress.json")
    args = parser.parse_args()

    import parse  # local import: parse imports this module, so keep it lazy

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    annotate(data)
    if not args.dry_run:
        parse.write(data)  # refreshes data/congress.json *and* web/data.js
    if args.report:
        report(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
