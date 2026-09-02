"""Layer 2 — segmentation and normalization.

Turns an instruction document into a list of atomic *directives*: one bullet,
one numbered item, or one imperative sentence. The directive, not the file, is
the unit of analysis — file-level statistics say almost nothing, directive-level
statistics are the actual finding.

Deterministic and testable: a parser, never a model.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# Words that make a rule binding versus merely advisory.
HARD_WORDS = re.compile(
    r"\b(must|never|always|do not|don't|shall|mandatory|required|forbidden|"
    r"prohibited|non-negotiable|under no circumstances|strictly|obey|only ever)\b",
    re.IGNORECASE,
)
SOFT_WORDS = re.compile(
    r"\b(should|prefer|preferably|consider|try to|ideally|recommended|"
    r"where possible|if possible|avoid|may)\b",
    re.IGNORECASE,
)
NEGATIVE = re.compile(r"\b(never|no |not |don't|do not|avoid|without|forbidden|prohibited)\b", re.IGNORECASE)

# A line that reads like an instruction rather than a description.
IMPERATIVE_START = re.compile(
    r"^(use|run|write|keep|do|don't|never|always|add|remove|make|ensure|check|"
    r"verify|prefer|avoid|commit|push|bump|update|read|follow|treat|put|set|"
    r"stop|start|report|ask|leave|split|merge|pin|test|build|format|lint|"
    r"document|name|store|record|apply|call|create|delete|fix|refactor|"
    r"install|install|assume|state|prove|explain|list|return|emit|include|"
    r"exclude|respect|honour|honor|obey|note that|before|after|when|if|every|"
    r"each|all|no|only)\b",
    re.IGNORECASE,
)

BULLET = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
FENCE = re.compile(r"^\s*(```|~~~)(.*)$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")

# Markdown decoration removed before hashing, so the same rule written with and
# without backticks collapses to one normalized form.
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_CODE = re.compile(r"`([^`]*)`")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_)(.+?)\1")
_HTML = re.compile(r"<[^>]+>")
_EMOJI = re.compile(
    "[\U0001f300-\U0001faff☀-➿️←-⇿⬀-⯿]", flags=re.UNICODE
)
_ORDINAL = re.compile(r"^\s*(\d+[.)]|[-*+]|\d+\.\d+\.?)\s*")
_WS = re.compile(r"\s+")

# Section roles: three different documents share the AGENTS.md filename, and
# separating them is a prerequisite for a sane template.
ROLE_RULES = "rules"
ROLE_COMMANDS = "commands"
ROLE_DESCRIPTION = "description"
ROLE_REFERENCE = "reference"


def normalize(text: str) -> str:
    """Collapse a directive to a comparable form."""
    text = _IMAGE.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _CODE.sub(r"\1", text)
    text = _EMPHASIS.sub(r"\2", text)
    text = _HTML.sub(" ", text)
    text = _EMOJI.sub("", text)
    text = _ORDINAL.sub("", text)
    text = text.replace("’", "'").replace("—", "-").replace("–", "-")
    text = _WS.sub(" ", text).strip()
    text = text.rstrip(".;:,").strip()
    return text.lower()


def hardness(text: str) -> str:
    if HARD_WORDS.search(text):
        return "hard"
    if SOFT_WORDS.search(text):
        return "soft"
    return "neutral"


@dataclass
class Directive:
    """One atomic instruction."""

    text: str  # as written, markdown stripped of list marker
    normalized: str
    fingerprint: str  # sha256 of the normalized form
    heading_path: list[str]
    line: int
    form: str  # bullet | numbered | sentence | heading
    depth: int  # list nesting depth
    hardness: str  # hard | soft | neutral
    negative: bool
    words: int
    topics: list[str] = field(default_factory=list)  # filled by the classifier
    cluster: str = ""  # filled by the optional semantic pass


@dataclass
class Section:
    """A heading and the material underneath it."""

    title: str
    level: int
    path: list[str]
    line: int
    role: str
    directive_count: int
    code_lines: int
    prose_lines: int


@dataclass
class ParsedDocument:
    directives: list[Directive]
    sections: list[Section]
    code_lines: int
    prose_lines: int
    table_lines: int
    heading_count: int
    max_heading_depth: int
    front_matter: dict[str, str]


def _split_sentences(paragraph: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z`*_\"'])", paragraph.strip())
    return [p.strip() for p in parts if p.strip()]


def _fingerprint(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _make_directive(text: str, heading_path: list[str], line: int, form: str, depth: int) -> Directive | None:
    normalized = normalize(text)
    if len(normalized) < 8 or len(normalized.split()) < 3:
        return None
    return Directive(
        text=text.strip(),
        normalized=normalized,
        fingerprint=_fingerprint(normalized),
        heading_path=list(heading_path),
        line=line,
        form=form,
        depth=depth,
        hardness=hardness(normalized),
        negative=bool(NEGATIVE.search(normalized)),
        words=len(normalized.split()),
    )


def _front_matter(lines: list[str]) -> tuple[dict[str, str], int]:
    if not lines or lines[0].strip() != "---":
        return {}, 0
    data: dict[str, str] = {}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return data, index + 1
        if ":" in lines[index]:
            key, _, value = lines[index].partition(":")
            data[key.strip()] = value.strip()
    return {}, 0


def _section_role(directives: int, code: int, prose: int, title: str) -> str:
    lowered = title.lower()
    if any(word in lowered for word in ("command", "usage", "how to run", "build", "getting started")):
        if code:
            return ROLE_COMMANDS
    if any(word in lowered for word in ("layout", "architecture", "structure", "overview", "what this", "context", "index", "file index")):
        if directives <= max(1, prose // 4):
            return ROLE_DESCRIPTION
    if directives == 0 and code > prose:
        return ROLE_COMMANDS
    if directives == 0:
        return ROLE_DESCRIPTION if prose else ROLE_REFERENCE
    return ROLE_RULES


def parse(text: str) -> ParsedDocument:
    """Segment one instruction document."""
    lines = text.splitlines()
    front, start = _front_matter(lines)

    directives: list[Directive] = []
    sections: list[Section] = []
    heading_path: list[str] = []
    heading_levels: list[int] = []

    in_fence = False
    fence_marker = ""
    code_lines = prose_lines = table_lines = heading_count = 0
    max_depth = 0

    pending: list[str] = []  # paragraph buffer
    pending_line = 0

    current: dict[str, int | str | list[str]] | None = None
    counters = {"directives": 0, "code": 0, "prose": 0}

    def close_section() -> None:
        nonlocal current
        if current is None:
            return
        sections.append(
            Section(
                title=str(current["title"]),
                level=int(current["level"]),
                path=list(current["path"]),  # type: ignore[arg-type]
                line=int(current["line"]),
                role=_section_role(
                    counters["directives"], counters["code"], counters["prose"], str(current["title"])
                ),
                directive_count=counters["directives"],
                code_lines=counters["code"],
                prose_lines=counters["prose"],
            )
        )
        counters.update(directives=0, code=0, prose=0)
        current = None

    def flush_paragraph() -> None:
        nonlocal pending
        if not pending:
            return
        paragraph = " ".join(pending).strip()
        pending = []
        if not paragraph:
            return
        for sentence in _split_sentences(paragraph):
            if IMPERATIVE_START.match(sentence) or HARD_WORDS.search(sentence):
                item = _make_directive(sentence, heading_path, pending_line, "sentence", 0)
                if item is not None:
                    directives.append(item)
                    counters["directives"] += 1

    for offset, raw in enumerate(lines[start:], start=start + 1):
        fence = FENCE.match(raw)
        if fence:
            marker = fence.group(1)
            if in_fence and marker == fence_marker:
                in_fence = False
            elif not in_fence:
                in_fence = True
                fence_marker = marker
            code_lines += 1
            counters["code"] += 1
            continue
        if in_fence:
            code_lines += 1
            counters["code"] += 1
            continue

        heading = HEADING.match(raw)
        if heading:
            flush_paragraph()
            close_section()
            level = len(heading.group(1))
            title = normalize_heading(heading.group(2))
            while heading_levels and heading_levels[-1] >= level:
                heading_levels.pop()
                heading_path.pop()
            heading_levels.append(level)
            heading_path.append(title)
            heading_count += 1
            max_depth = max(max_depth, level)
            current = {"title": title, "level": level, "path": list(heading_path), "line": offset}
            continue

        if TABLE_ROW.match(raw):
            flush_paragraph()
            table_lines += 1
            continue

        bullet = BULLET.match(raw)
        if bullet:
            flush_paragraph()
            indent, marker, body = bullet.groups()
            depth = len(indent) // 2
            form = "numbered" if marker[0].isdigit() else "bullet"
            item = _make_directive(body, heading_path, offset, form, depth)
            if item is not None:
                directives.append(item)
                counters["directives"] += 1
            prose_lines += 1
            counters["prose"] += 1
            continue

        if raw.strip():
            pending.append(raw.strip())
            if not pending_line:
                pending_line = offset
            prose_lines += 1
            counters["prose"] += 1
        else:
            flush_paragraph()
            pending_line = 0

    flush_paragraph()
    close_section()

    return ParsedDocument(
        directives=directives,
        sections=sections,
        code_lines=code_lines,
        prose_lines=prose_lines,
        table_lines=table_lines,
        heading_count=heading_count,
        max_heading_depth=max_depth,
        front_matter=front,
    )


def normalize_heading(title: str) -> str:
    title = _LINK.sub(r"\1", title)
    title = _CODE.sub(r"\1", title)
    title = _EMPHASIS.sub(r"\2", title)
    title = _EMOJI.sub("", title)
    title = _ORDINAL.sub("", title)
    return _WS.sub(" ", title).strip()
