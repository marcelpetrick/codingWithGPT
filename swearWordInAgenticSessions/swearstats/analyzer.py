"""Streaming history readers and aggregate-only analysis."""

from __future__ import annotations

import csv
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
SOURCE_NAMES = {"claude": "Claude Code", "codex": "Codex CLI"}
LENGTH_BUCKETS = (
    (0, 10, "1–10"),
    (11, 30, "11–30"),
    (31, 75, "31–75"),
    (76, 150, "76–150"),
    (151, 10**18, "151+"),
)


@dataclass(frozen=True)
class Lexeme:
    canonical: str
    category: str
    severity: int


@dataclass(frozen=True)
class Prompt:
    source: str
    text: str
    timestamp: datetime | None
    session: str | None = None
    project: str | None = None


@dataclass
class Bucket:
    prompts: int = 0
    profane_prompts: int = 0
    hits: int = 0
    words: int = 0
    score: int = 0

    def add(self, word_count: int, hits: list[Lexeme]) -> None:
        self.prompts += 1
        self.words += word_count
        self.hits += len(hits)
        self.score += sum(hit.severity for hit in hits)
        self.profane_prompts += bool(hits)

    def as_dict(self) -> dict[str, int | float]:
        return {
            "prompts": self.prompts,
            "profane_prompts": self.profane_prompts,
            "hits": self.hits,
            "words": self.words,
            "score": self.score,
            "prompt_rate": round(100 * self.profane_prompts / self.prompts, 2)
            if self.prompts
            else 0,
            "hits_per_100_prompts": round(100 * self.hits / self.prompts, 2) if self.prompts else 0,
            "hits_per_1000_words": round(1000 * self.hits / self.words, 2) if self.words else 0,
        }


@dataclass
class Analysis:
    totals: dict[str, Bucket] = field(default_factory=lambda: defaultdict(Bucket))
    terms: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    categories: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    severity: dict[str, Counter[int]] = field(default_factory=lambda: defaultdict(Counter))
    daily: dict[str, dict[str, Bucket]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(Bucket))
    )
    monthly: dict[str, dict[str, Bucket]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(Bucket))
    )
    weekday: dict[str, dict[int, Bucket]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(Bucket))
    )
    hourly: dict[str, dict[int, Bucket]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(Bucket))
    )
    lengths: dict[str, dict[str, Bucket]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(Bucket))
    )
    sessions: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    profane_sessions: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    projects: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    events: list[tuple[datetime, bool, str]] = field(default_factory=list)
    malformed: Counter[str] = field(default_factory=Counter)
    missing_timestamp: Counter[str] = field(default_factory=Counter)


def load_lexicon(paths: Iterable[Path]) -> dict[str, Lexeme]:
    lexicon: dict[str, Lexeme] = {}
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = csv.reader(handle, delimiter="\t")
            for line_number, row in enumerate(rows, 1):
                if not row or row[0].lstrip().startswith("#"):
                    continue
                if len(row) != 4:
                    raise ValueError(f"{path}:{line_number}: expected 4 tab-separated fields")
                variant, canonical, category, severity_text = (cell.strip() for cell in row)
                severity = int(severity_text)
                if not variant or not canonical or not category or severity not in (1, 2, 3):
                    raise ValueError(f"{path}:{line_number}: invalid lexicon entry")
                normalized = normalize_word(variant)
                lexicon[normalized] = Lexeme(normalize_word(canonical), category, severity)
    if not lexicon:
        raise ValueError("the lexicon is empty")
    return lexicon


def normalize_word(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().replace("’", "'")


def parse_timestamp(value: Any) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)):
            seconds = float(value)
            if seconds > 10_000_000_000:
                seconds /= 1000
            return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone()
        if isinstance(value, str):
            candidate = value.strip().replace("Z", "+00:00")
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone()
    except (OverflowError, OSError, ValueError):
        return None
    return None


def read_history(path: Path, source: str, analysis: Analysis) -> Iterator[Prompt]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                analysis.malformed[source] += 1
                continue
            if not isinstance(record, dict):
                analysis.malformed[source] += 1
                continue
            if source == "codex":
                text = record.get("text")
                timestamp = parse_timestamp(record.get("ts"))
                session = record.get("session_id")
                project = None
            else:
                text = record.get("display")
                timestamp = parse_timestamp(record.get("timestamp"))
                session = record.get("sessionId") or record.get("session_id")
                project = record.get("project")
            if not isinstance(text, str):
                analysis.malformed[source] += 1
                continue
            if timestamp is None:
                analysis.missing_timestamp[source] += 1
            yield Prompt(
                source=source,
                text=text,
                timestamp=timestamp,
                session=str(session) if session else None,
                project=str(project) if project else None,
            )


def analyze(
    inputs: Iterable[tuple[str, Path]],
    lexicon: dict[str, Lexeme],
    since: datetime | None = None,
    until: datetime | None = None,
) -> Analysis:
    result = Analysis()
    for source, path in inputs:
        for prompt in read_history(path, source, result):
            if prompt.timestamp and since and prompt.timestamp < since:
                continue
            if prompt.timestamp and until and prompt.timestamp >= until:
                continue
            words = [normalize_word(match.group()) for match in WORD_RE.finditer(prompt.text)]
            hits = [lexicon[word] for word in words if word in lexicon]
            _record(result, prompt, len(words), hits)
    return result


def _record(result: Analysis, prompt: Prompt, word_count: int, hits: list[Lexeme]) -> None:
    keys = ("all", prompt.source)
    for key in keys:
        result.totals[key].add(word_count, hits)
        result.terms[key].update(hit.canonical for hit in hits)
        result.categories[key].update(hit.category for hit in hits)
        result.severity[key].update(hit.severity for hit in hits)
        result.lengths[key][_length_bucket(word_count)].add(word_count, hits)

    if prompt.session:
        result.sessions[prompt.source].add(prompt.session)
        if hits:
            result.profane_sessions[prompt.source].add(prompt.session)
    if prompt.project:
        result.projects[prompt.source].add(prompt.project)
    if not prompt.timestamp:
        return

    result.events.append((prompt.timestamp, bool(hits), prompt.source))
    day = prompt.timestamp.date().isoformat()
    month = day[:7]
    for key in keys:
        result.daily[key][day].add(word_count, hits)
        result.monthly[key][month].add(word_count, hits)
        result.weekday[key][prompt.timestamp.weekday()].add(word_count, hits)
        result.hourly[key][prompt.timestamp.hour].add(word_count, hits)


def _length_bucket(count: int) -> str:
    for low, high, label in LENGTH_BUCKETS:
        if low <= count <= high:
            return label
    raise AssertionError("unreachable")


def _date_range(first: date, last: date) -> Iterator[date]:
    current = first
    while current <= last:
        yield current
        current = date.fromordinal(current.toordinal() + 1)


def _streaks(events: list[tuple[datetime, bool, str]]) -> dict[str, int]:
    ordered = sorted(events, key=lambda event: event[0])
    longest_clean = current_clean = longest_profane = current_profane = 0
    for _, is_profane, _ in ordered:
        if is_profane:
            current_profane += 1
            longest_profane = max(longest_profane, current_profane)
            current_clean = 0
        else:
            current_clean += 1
            longest_clean = max(longest_clean, current_clean)
            current_profane = 0
    return {"longest_clean": longest_clean, "longest_profane": longest_profane}


def serialize(result: Analysis, sources: dict[str, Path], lexicon_size: int) -> dict[str, Any]:
    source_keys = [key for key in ("claude", "codex") if key in sources]
    keys = ["all", *source_keys]
    dated_events = [event for event in result.events]
    first = min((event[0] for event in dated_events), default=None)
    last = max((event[0] for event in dated_events), default=None)

    daily: dict[str, list[dict[str, Any]]] = {}
    if first and last:
        for key in keys:
            daily[key] = [
                {"date": day.isoformat(), **result.daily[key][day.isoformat()].as_dict()}
                for day in _date_range(first.date(), last.date())
            ]

    source_details: dict[str, Any] = {}
    for key in keys:
        source_events = (
            dated_events if key == "all" else [event for event in dated_events if event[2] == key]
        )
        hit_counts = [bucket.hits for bucket in result.daily[key].values() if bucket.hits]
        source_details[key] = {
            "label": "Combined" if key == "all" else SOURCE_NAMES[key],
            "totals": result.totals[key].as_dict(),
            "terms": [
                {"term": term, "count": count} for term, count in result.terms[key].most_common()
            ],
            "categories": dict(result.categories[key].most_common()),
            "severity": {str(level): result.severity[key][level] for level in (1, 2, 3)},
            "monthly": [
                {"month": month, **bucket.as_dict()}
                for month, bucket in sorted(result.monthly[key].items())
            ],
            "weekday": [result.weekday[key][index].as_dict() for index in range(7)],
            "hourly": [result.hourly[key][index].as_dict() for index in range(24)],
            "lengths": [
                {"label": label, **result.lengths[key][label].as_dict()}
                for _, _, label in LENGTH_BUCKETS
            ],
            "streaks": _streaks(source_events),
            "median_active_day_hits": statistics.median(hit_counts) if hit_counts else 0,
        }

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "period": {
            "first": first.isoformat(timespec="seconds") if first else None,
            "last": last.isoformat(timespec="seconds") if last else None,
        },
        "lexicon_size": lexicon_size,
        "sources": source_details,
        "source_meta": {
            source: {
                "label": SOURCE_NAMES[source],
                "sessions": len(result.sessions[source]),
                "profane_sessions": len(result.profane_sessions[source]),
                "projects": len(result.projects[source]),
                "malformed_lines": result.malformed[source],
                "missing_timestamps": result.missing_timestamp[source],
            }
            for source in sources
        },
        "daily": daily,
        "privacy": "Aggregate counts only; no prompt text is retained in this report.",
    }


def parse_boundary(value: str | None, *, end: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        parsed_date = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"invalid date {value!r}; use YYYY-MM-DD") from error
    boundary = datetime.combine(parsed_date, time.min).astimezone()
    if end:
        return datetime.combine(
            date.fromordinal(parsed_date.toordinal() + 1), time.min
        ).astimezone()
    return boundary
