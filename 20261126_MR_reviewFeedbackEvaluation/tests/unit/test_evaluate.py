# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for outcome decisions, censoring, evidence and timings (REQ-OUT-*, REQ-TIME-1)."""

import sqlite3
from zoneinfo import ZoneInfo

import pytest

from mrreview import db
from mrreview.bizhours import BusinessCalendar
from mrreview.evaluate import Evidence, censoring, code_evidence, decide, timings

D = Evidence("direct", "2026-01-02T10:00:00+00:00")
IND = Evidence("indirect", "2026-01-02T10:00:00+00:00")
N = Evidence("none", None)
U = Evidence("unavailable", None)


@pytest.mark.parametrize(
    ("text", "ev", "expected"),
    [
        ("implemented_claimed", D, ("implemented", "direct")),
        ("implemented_claimed", IND, ("implemented", "indirect")),
        ("implemented_claimed", N, ("implemented", "textual_only")),
        ("implemented_claimed", U, ("implemented", "unavailable")),
        ("alternative_claimed", D, ("alternative_implemented", "direct")),
        ("partial_claimed", N, ("partially_implemented", "textual_only")),
        ("promised", D, ("implemented", "direct")),
        ("promised", IND, ("open", "textual_only")),
        ("promised", N, ("open", "textual_only")),
        ("justified_no_change", D, ("justified_no_change", "not_applicable")),
        ("deferred", N, ("deferred", "not_applicable")),
        ("open", D, ("open", "not_applicable")),
        ("declined_unjustified", N, ("declined_unjustified", "not_applicable")),
        ("unknown", N, ("unknown", "not_applicable")),
    ],
)
def test_decide(text: str, ev: Evidence, expected: tuple[str, str]) -> None:
    assert decide(text, False, ev) == expected


def test_abstain_gives_unknown() -> None:
    assert decide("implemented_claimed", True, D) == ("unknown", "not_applicable")


def test_censoring_recent_open_mr_only() -> None:
    cut = "2026-11-20T12:00:00+00:00"
    assert censoring("open", "opened", "2026-11-10T12:00:00+00:00", cut, 14) == "recent"
    assert censoring("open", "opened", "2026-11-06T11:59:59+00:00", cut, 14) is None
    assert censoring("open", "merged", "2026-11-19T12:00:00+00:00", cut, 14) is None
    assert censoring("implemented", "opened", "2026-11-19T12:00:00+00:00", cut, 14) is None
    assert censoring("unknown", "opened", "2026-11-19T12:00:00+00:00", cut, 14) == "recent"


def diff(lines: list[str]) -> str:
    return f"@@ -0,0 +1,{len(lines)} @@\n" + "".join(f"+{x}\n" for x in lines)


def seed(
    conn: sqlite3.Connection, versions: list[tuple[int, str, dict[str, list[str]], int]]
) -> None:
    with db.tx(conn):
        for vid, at, files, complete in versions:
            conn.execute(
                "INSERT INTO mr_versions VALUES (1, 1, ?, 'h', 'b', ?, ?)", (vid, at, complete)
            )
            for path, lines in files.items():
                conn.execute(
                    "INSERT INTO version_diffs VALUES (1, 1, ?, ?, ?, ?)",
                    (vid, path, path, diff(lines)),
                )


BASE = [f"l{i}" for i in range(1, 21)]
T = {
    "project_id": 1,
    "mr_iid": 1,
    "created_at": "2026-01-01T12:00:00+00:00",
    "new_path": "a.c",
    "new_line": 10,
}


def test_evidence_direct_line_change(conn: sqlite3.Connection) -> None:
    changed = BASE[:]
    changed[9] = "l10 fixed"
    seed(
        conn,
        [
            (1, "2026-01-01T00:00:00+00:00", {"a.c": BASE}, 1),
            (2, "2026-01-02T00:00:00+00:00", {"a.c": changed}, 1),
        ],
    )
    assert code_evidence(conn, T) == Evidence("direct", "2026-01-02T00:00:00+00:00")


def test_evidence_lines_shift_but_survive_is_indirect(conn: sqlite3.Connection) -> None:
    shifted = ["new header", *BASE]
    seed(
        conn,
        [
            (1, "2026-01-01T00:00:00+00:00", {"a.c": BASE}, 1),
            (2, "2026-01-02T00:00:00+00:00", {"a.c": shifted}, 1),
        ],
    )
    assert code_evidence(conn, T).level == "indirect"


def test_evidence_other_file_only_is_none(conn: sqlite3.Connection) -> None:
    seed(
        conn,
        [
            (1, "2026-01-01T00:00:00+00:00", {"a.c": BASE, "b.c": ["x"]}, 1),
            (2, "2026-01-02T00:00:00+00:00", {"a.c": BASE, "b.c": ["y"]}, 1),
        ],
    )
    assert code_evidence(conn, T) == Evidence("none", None)
    general = {**T, "new_path": None, "new_line": None}
    assert code_evidence(conn, general).level == "indirect"


def test_evidence_file_removed_is_indirect(conn: sqlite3.Connection) -> None:
    seed(
        conn,
        [
            (1, "2026-01-01T00:00:00+00:00", {"a.c": BASE}, 1),
            (2, "2026-01-02T00:00:00+00:00", {}, 1),
        ],
    )
    assert code_evidence(conn, T).level == "indirect"


def test_evidence_no_versions_and_no_later(conn: sqlite3.Connection) -> None:
    assert code_evidence(conn, T).level == "unavailable"
    seed(conn, [(1, "2026-01-01T00:00:00+00:00", {"a.c": BASE}, 1)])
    assert code_evidence(conn, T).level == "none"


def test_evidence_incomplete_diffs_is_unavailable(conn: sqlite3.Connection) -> None:
    seed(
        conn,
        [
            (1, "2026-01-01T00:00:00+00:00", {"a.c": BASE}, 1),
            (2, "2026-01-02T00:00:00+00:00", {"a.c": BASE}, 0),
        ],
    )
    assert code_evidence(conn, T).level == "unavailable"


def test_comment_before_first_version_uses_first(conn: sqlite3.Connection) -> None:
    changed = BASE[:]
    changed[10] = "z"
    seed(
        conn,
        [
            (1, "2026-01-01T13:00:00+00:00", {"a.c": BASE}, 1),
            (2, "2026-01-02T00:00:00+00:00", {"a.c": changed}, 1),
        ],
    )
    assert code_evidence(conn, T).level == "direct"


def test_timings_pending_is_never_zero(conn: sqlite3.Connection) -> None:
    with db.tx(conn):
        conn.execute(
            "INSERT INTO users VALUES (1, 'a', 'A', 'human', NULL), (2, 'b', 'B', 'human', NULL), (9, 'bot', 'Bot', 'bot', NULL)"
        )
        conn.execute(
            "INSERT INTO notes(id, discussion_id, project_id, mr_iid, author_id, body, created_at, system, resolvable, resolved) VALUES "
            "(1, 'd', 1, 1, 2, 'x', '2026-11-23T09:00:00+00:00', 0, 1, 0),"
            "(2, 'd', 1, 1, 9, 'bot', '2026-11-23T09:30:00+00:00', 0, 1, 0),"
            "(3, 'd', 1, 1, 1, 'ok', '2026-11-23T11:00:00+00:00', 0, 1, 0)"
        )
    cal = BusinessCalendar(ZoneInfo("UTC"))
    thread = {
        "id": "d",
        "giver_id": 2,
        "created_at": "2026-11-23T09:00:00+00:00",
        "resolved_at": None,
        "resolvable": 1,
    }
    f = {"decision_note_id": None, "responses": [{"note_id": 3, "act": "agreement"}]}
    tm = timings(conn, thread, f, cal, N, "implemented", "2026-11-24T09:00:00+00:00")  # type: ignore[arg-type]
    assert tm["first_response"] == {"state": "observed", "wall_h": 2.0, "biz_h": 2.0}
    assert tm["decision"]["state"] == "observed"
    assert tm["implementation"] == {"state": "pending", "open_h": 24.0}
    assert tm["resolution"]["state"] == "pending"
    tm2 = timings(
        conn,
        {**thread, "resolvable": 0},
        {"decision_note_id": 1, "responses": []},
        cal,
        D,  # type: ignore[arg-type]
        "open",
        "2026-11-24T09:00:00+00:00",
    )
    assert tm2["implementation"] == {"state": "n/a"}
    assert tm2["resolution"] == {"state": "n/a"}
    assert tm2["decision"]["wall_h"] == 0.0
