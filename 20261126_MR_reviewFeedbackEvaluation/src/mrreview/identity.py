# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""User kinds, stable pseudonyms and name masking (REQ-COL-5, REQ-UI-5)."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
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
    patterns: list[tuple[str, int]] = []
    for uid, (username, name) in users.items():
        clean = normalize(name).strip()
        if len(clean) >= _MIN_TOKEN:
            patterns.append((clean, uid))
        patterns += [
            (part, uid) for part in regex.split(r"[\s,]+", clean) if len(part) >= _MIN_TOKEN
        ]
        if len(username) >= _MIN_TOKEN:
            patterns.append((username, uid))
    for term, uid in sorted(patterns, key=lambda p: -len(p[0])):
        out = regex.sub(
            rf"(?<![\w⟦:]){regex.escape(term)}(?![\w⟧])", f"⟦u:{uid}⟧", out, flags=regex.IGNORECASE
        )
    return out
