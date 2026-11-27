# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""User kinds, stable pseudonyms and name masking (REQ-COL-5, REQ-UI-5)."""

from __future__ import annotations

import functools
import hashlib
import secrets
import sqlite3
from collections import Counter
from collections.abc import Mapping

import regex

from mrreview.textutil import normalize

_BOT_PATTERNS = [
    regex.compile(r"^(project|group)_\d+_bot(_[0-9a-z]+)?$"),
    regex.compile(r"(^|[-_.])bot$"),
    regex.compile(r"\[bot\]$"),
    regex.compile(r"^(dependabot|renovate|gitlab-bot|support-bot|alert-bot|ci-bot)"),
]

ADJECTIVES = [
    "Amber",
    "Azure",
    "Coral",
    "Cobalt",
    "Crimson",
    "Golden",
    "Indigo",
    "Ivory",
    "Jade",
    "Lime",
    "Magenta",
    "Olive",
    "Onyx",
    "Pearl",
    "Ruby",
    "Saffron",
    "Scarlet",
    "Silver",
    "Teal",
    "Topaz",
    "Umber",
    "Violet",
    "Cyan",
    "Bronze",
    "Copper",
    "Emerald",
    "Garnet",
    "Lilac",
    "Ochre",
    "Plum",
    "Sand",
    "Slate",
]
ANIMALS = [
    "Otter",
    "Falcon",
    "Lynx",
    "Heron",
    "Badger",
    "Marten",
    "Ibex",
    "Puffin",
    "Gecko",
    "Koala",
    "Lemur",
    "Narwhal",
    "Ocelot",
    "Panda",
    "Quokka",
    "Raven",
    "Seal",
    "Tapir",
    "Urchin",
    "Vole",
    "Walrus",
    "Yak",
    "Zebra",
    "Bison",
    "Crane",
    "Dingo",
    "Egret",
    "Ferret",
    "Gazelle",
    "Hare",
    "Jackal",
    "Kiwi",
]


def user_kind(user: Mapping[str, object] | None) -> str:
    """Return 'human', 'bot' or 'deleted' for a GitLab user object."""
    if user is None:
        return "deleted"
    username = str(user.get("username", "")).lower()
    if user.get("bot") is True:
        return "bot"
    if username == "ghost" or user.get("state") == "deleted":
        return "deleted"
    if any(p.search(username) for p in _BOT_PATTERNS):
        return "bot"
    return "human"


def _salt(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT value FROM meta WHERE key='pseudonym_salt'").fetchone()
    if row:
        return str(row[0])
    salt = secrets.token_hex(16)
    conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('pseudonym_salt', ?)", (salt,))
    return str(conn.execute("SELECT value FROM meta WHERE key='pseudonym_salt'").fetchone()[0])


def label_for(conn: sqlite3.Connection, user_id: int) -> str:
    """Return the stable pseudonym of a user. It is assigned once and stored."""
    row = conn.execute("SELECT label FROM pseudonyms WHERE user_id=?", (user_id,)).fetchone()
    if row:
        return str(row[0])
    digest = hashlib.sha256(f"{_salt(conn)}:{user_id}".encode()).digest()
    base = f"{ADJECTIVES[digest[0] % len(ADJECTIVES)]} {ANIMALS[digest[1] % len(ANIMALS)]}"
    label = base
    n = 2
    while conn.execute("SELECT 1 FROM pseudonyms WHERE label=?", (label,)).fetchone():
        label = f"{base} {n}"
        n += 1
    conn.execute("INSERT INTO pseudonyms(user_id, label) VALUES (?, ?)", (user_id, label))
    return label


UNKNOWN_MENTION = "⟦u:?⟧"
_MENTION = regex.compile(r"(?<![\w.])@([A-Za-z0-9_][A-Za-z0-9_.\-]*[A-Za-z0-9_]|[A-Za-z0-9_])")
_MIN_TOKEN = 3


def _alternation(terms: list[str]) -> str:
    return "|".join(regex.escape(t) for t in sorted(set(terms), key=lambda t: (-len(t), t)))


@functools.lru_cache(maxsize=16)
def _name_masker(
    users: tuple[tuple[int, str, str], ...],
) -> tuple[dict[str, int], regex.Pattern[str] | None]:
    """One compiled pattern for all names of a user set (compiling per call was the bottleneck)."""
    lookup: dict[str, int] = {}
    for uid, username, name in sorted(users, key=lambda u: u[0]):
        clean = normalize(name).strip()
        terms = [clean] if len(clean) >= _MIN_TOKEN else []
        terms += [part for part in regex.split(r"[\s,]+", clean) if len(part) >= _MIN_TOKEN]
        if len(username) >= _MIN_TOKEN:
            terms.append(username)
        for term in terms:
            lookup.setdefault(term.casefold(), uid)
    if not lookup:
        return lookup, None
    pattern = regex.compile(
        rf"(?<![\w⟦:])(?:{_alternation(list(lookup))})(?![\w⟧])", flags=regex.IGNORECASE
    )
    return lookup, pattern


def mask_names(text: str, users: Mapping[int, tuple[str, str]]) -> str:
    """Replace names of people with tokens ⟦u:ID⟧; unknown @mentions become ⟦u:?⟧.

    Masked: @mentions (longest username first), bare usernames, full names, and name parts of
    at least three letters, all without regard to case. The dashboard swaps each token for a
    pseudonym or the real name. Limit: nicknames and misspelled names stay visible.
    """
    out = normalize(text)
    by_username = {u.casefold(): uid for uid, (u, _n) in users.items() if u}

    def mention(m: regex.Match[str]) -> str:
        handle = m.group(1)
        uid = by_username.get(handle.casefold())
        while uid is None and "." in handle:  # "@john.doe." at a sentence end
            handle = handle.rsplit(".", 1)[0]
            uid = by_username.get(handle.casefold())
        rest = m.group(1)[len(handle) :]
        return (f"⟦u:{uid}⟧" if uid is not None else UNKNOWN_MENTION) + rest

    out = _MENTION.sub(mention, out)
    lookup, pattern = _name_masker(tuple((uid, u, n) for uid, (u, n) in users.items()))
    if pattern is None:
        return out
    return pattern.sub(lambda m: f"⟦u:{lookup[m.group(0).casefold()]}⟧", out)


@functools.lru_cache(maxsize=16)
def _exact_masker(
    users: tuple[tuple[int, str, str], ...],
) -> tuple[dict[str, int], regex.Pattern[str] | None]:
    lookup: dict[str, int] = {}
    for uid, username, name in sorted(users, key=lambda u: u[0]):
        for term in (normalize(name).strip(), username):
            if len(term) >= _MIN_TOKEN:
                lookup.setdefault(term.casefold(), uid)
    if not lookup:
        return lookup, None
    pattern = regex.compile(
        rf"(?<![\w⟦:])(?:{_alternation(list(lookup))})(?![\w⟧])", flags=regex.IGNORECASE
    )
    return lookup, pattern


def mask_exact(text: str, users: Mapping[int, tuple[str, str]]) -> str:
    """Replace only whole names and usernames with ⟦u:ID⟧ (for bots: no name parts, D-019)."""
    lookup, pattern = _exact_masker(tuple((uid, u, n) for uid, (u, n) in users.items()))
    if pattern is None:
        return text
    return pattern.sub(lambda m: f"⟦u:{lookup[m.group(0).casefold()]}⟧", text)


PROJECT_WORDS = [
    "Andromeda",
    "Aquila",
    "Auriga",
    "Bootes",
    "Caelum",
    "Carina",
    "Cetus",
    "Columba",
    "Corvus",
    "Crater",
    "Crux",
    "Cygnus",
    "Delphinus",
    "Dorado",
    "Draco",
    "Fornax",
    "Gemini",
    "Grus",
    "Hydra",
    "Indus",
    "Lacerta",
    "Lepus",
    "Libra",
    "Lupus",
    "Lyra",
    "Mensa",
    "Norma",
    "Octans",
    "Orion",
    "Pavo",
    "Pegasus",
    "Perseus",
    "Phoenix",
    "Pictor",
    "Pyxis",
    "Sagitta",
    "Scutum",
    "Serpens",
    "Taurus",
    "Tucana",
    "Vela",
    "Virgo",
    "Volans",
    "Vulpecula",
]
_MIN_PROJECT_TOKEN = 4


def project_label_for(conn: sqlite3.Connection, project_id: int) -> str:
    """Stable pseudonym of a project ("Project Orion"). Assigned once and stored."""
    row = conn.execute(
        "SELECT label FROM project_pseudonyms WHERE project_id=?", (project_id,)
    ).fetchone()
    if row:
        return str(row[0])
    digest = hashlib.sha256(f"{_salt(conn)}:project:{project_id}".encode()).digest()
    base = f"Project {PROJECT_WORDS[int.from_bytes(digest[:2], 'big') % len(PROJECT_WORDS)]}"
    label = base
    n = 2
    while conn.execute("SELECT 1 FROM project_pseudonyms WHERE label=?", (label,)).fetchone():
        label = f"{base} {n}"
        n += 1
    conn.execute(
        "INSERT INTO project_pseudonyms(project_id, label) VALUES (?, ?)", (project_id, label)
    )
    return label


_GENERIC_PROJECT_WORDS = frozenset(
    [
        "linux",
        "kernel",
        "android",
        "windows",
        "docker",
        "documentation",
        "docs",
        "doc",
        "test",
        "tests",
        "testing",
        "tools",
        "utils",
        "common",
        "core",
        "config",
        "configs",
        "build",
        "builds",
        "scripts",
        "firmware",
        "bootloader",
        "uboot",
        "u-boot",
        "backend",
        "frontend",
        "server",
        "client",
        "library",
        "libs",
        "demo",
        "demos",
        "examples",
        "sandbox",
        "playground",
        "website",
        "wiki",
        "release",
        "releases",
        "images",
        "image",
        "packages",
        "infra",
        "deploy",
        "deployment",
        "pipeline",
        "pipelines",
    ]
)


@functools.lru_cache(maxsize=16)
def _project_masker(
    projects: tuple[tuple[int, str, str], ...],
) -> tuple[dict[str, int], regex.Pattern[str] | None]:
    lookup: dict[str, int] = {}
    # A short name (last path part) is masked only when exactly one project has it and it is not a
    # common word: "linux" ends five project paths and also means the operating system.
    short = Counter(name.casefold() for _pid, _path, name in projects if name)
    for pid, path, name in sorted(projects):
        if path and len(path) >= _MIN_PROJECT_TOKEN:
            lookup.setdefault(path.casefold(), pid)
        key = name.casefold() if name else ""
        if len(key) >= _MIN_PROJECT_TOKEN and short[key] == 1 and key not in _GENERIC_PROJECT_WORDS:
            lookup.setdefault(key, pid)
    if not lookup:
        return lookup, None
    pattern = regex.compile(
        rf"(?<![\w⟦:/.-])(?:{_alternation(list(lookup))})(?![\w⟧/-])", flags=regex.IGNORECASE
    )
    return lookup, pattern


def mask_projects(text: str, projects: Mapping[int, tuple[str, str]]) -> str:
    """Replace project paths and project names (4+ characters) with tokens ⟦p:ID⟧."""
    lookup, pattern = _project_masker(tuple((p, a, b) for p, (a, b) in projects.items()))
    if pattern is None:
        return text
    return pattern.sub(lambda m: f"⟦p:{lookup[m.group(0).casefold()]}⟧", text)
