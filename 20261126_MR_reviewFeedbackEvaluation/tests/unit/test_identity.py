# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for user kinds, pseudonyms and name masking (REQ-COL-5, REQ-UI-5)."""

import sqlite3

import pytest

from mrreview import db, identity


@pytest.mark.parametrize(
    ("user", "kind"),
    [
        ({"id": 1, "username": "alice", "name": "Alice"}, "human"),
        ({"id": 2, "username": "project_12_bot_ab12", "name": "x"}, "bot"),
        ({"id": 3, "username": "group_7_bot", "name": "x"}, "bot"),
        ({"id": 4, "username": "renovate-bot", "name": "Renovate"}, "bot"),
        ({"id": 5, "username": "ci[bot]", "name": "CI"}, "bot"),
        ({"id": 6, "username": "ghost", "name": "Ghost User"}, "deleted"),
        ({"id": 7, "username": "bob", "name": "Bob", "bot": True}, "bot"),
        ({"id": 8, "username": "carol", "name": "Carol", "state": "deleted"}, "deleted"),
        ({"id": 9, "username": "abbot", "name": "Abbot"}, "human"),
        (None, "deleted"),
    ],
)
def test_user_kind(user: dict[str, object] | None, kind: str) -> None:
    assert identity.user_kind(user) == kind


def test_labels_are_stable_and_unique(conn: sqlite3.Connection) -> None:
    first = identity.label_for(conn, 42)
    assert identity.label_for(conn, 42) == first
    labels = {identity.label_for(conn, uid) for uid in range(1, 400)}
    assert len(labels) == 399
    assert all(lbl.count(" ") >= 1 for lbl in labels)


def test_labels_survive_reconnect(tmp_path: object) -> None:
    path = f"{tmp_path}/x.sqlite3"
    c1 = db.connect(path)
    label = identity.label_for(c1, 7)
    c1.close()
    c2 = db.connect(path)
    assert identity.label_for(c2, 7) == label
    c2.close()


def test_mask_names_replaces_mentions_and_names() -> None:
    users = {1: ("alice", "Alice Müller"), 2: ("bo", "Bo")}
    text = "@alice said Alice Müller agrees; email alice@example.org; @alicex; Bob"
    masked = identity.mask_names(text, users)
    assert masked.startswith("⟦u:1⟧ said ⟦u:1⟧ agrees")
    assert "example.org" in masked
    assert "@alicex" not in masked
    assert "⟦u:?⟧" in masked  # unknown mention
    assert "Bob" in masked  # two-letter names are not replaced inside words
    assert identity.mask_names("plain", {}) == "plain"


def test_mask_names_handles_decomposed_input() -> None:
    users = {1: ("jose", "José Núñez")}
    assert identity.mask_names("Jose\u0301 Nu\u0301n\u0303ez wrote", users) == "⟦u:1⟧ wrote"


def test_mask_names_review_findings() -> None:
    users = {1: ("anna", "Anna Berg"), 2: ("john.doe", "Jo Do"), 3: ("john", "Johnathan Smithers")}
    masked = identity.mask_names(
        "thanks anna, see john.doe's note; @carol please check; ANNA BERG", users
    )
    assert "anna" not in masked.casefold()
    assert "john.doe" not in masked
    assert "carol" not in masked
    assert masked.count("⟦u:1⟧") == 2
    assert "⟦u:2⟧'s note" in masked
    assert identity.mask_names("ping @john.doe.", users) == "ping ⟦u:2⟧."
    assert identity.mask_names("ping @john.doe", users) == "ping ⟦u:2⟧"
    assert identity.mask_names("Smithers fixed it", users) == "⟦u:3⟧ fixed it"


def test_project_labels_are_stable_and_unique(conn: sqlite3.Connection) -> None:
    first = identity.project_label_for(conn, 11)
    assert first.startswith("Project ")
    assert identity.project_label_for(conn, 11) == first
    labels = {identity.project_label_for(conn, pid) for pid in range(1, 200)}
    assert len(labels) == 199


def test_mask_projects_in_text() -> None:
    projects = {11: ("firmware/display-controller", "display-controller"), 12: ("x/bsp", "bsp")}
    text = "See firmware/display-controller!3 and the Display-Controller repo; bsp stays."
    masked = identity.mask_projects(text, projects)
    assert masked == "See ⟦p:11⟧!3 and the ⟦p:11⟧ repo; bsp stays."
