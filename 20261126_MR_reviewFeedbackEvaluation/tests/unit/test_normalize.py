# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for thread roles and the substantive criterion (REQ-UNIT-1, REQ-UNIT-2)."""

import json

from mrreview.normalize import NoteRow, classify_thread

KINDS = {1: "human", 2: "human", 3: "human", 9: "bot"}


def note(
    i: int,
    author: int | None,
    body: str,
    *,
    system: bool = False,
    resolved: bool = False,
    resolved_at: str | None = None,
    resolvable: bool = True,
) -> NoteRow:
    return NoteRow(
        i,
        author,
        body,
        f"2026-01-0{i}T10:00:00+00:00",
        None,
        system,
        resolvable,
        resolved,
        resolved_at,
        2 if resolved else None,
        "a.py",
        3,
    )


def test_system_only_is_dropped() -> None:
    assert classify_thread([note(1, 1, "added 1 commit", system=True)], 1, KINDS) is None


def test_roles_reviewer_comment_on_author_mr() -> None:
    rec = classify_thread(
        [note(1, 2, "Null check?"), note(2, 1, "Fixed."), note(3, 3, "+1")], 1, KINDS
    )
    assert rec is not None
    assert rec["giver_id"] == 2
    assert rec["recipient_id"] == 1
    assert json.loads(str(rec["responders"])) == [1, 3]
    assert rec["has_reply"] == 1
    assert rec["reason"] == "substantive"


def test_roles_author_asks_and_other_answers() -> None:
    rec = classify_thread([note(1, 1, "Is the lock needed?"), note(2, 3, "Yes, ISR.")], 1, KINDS)
    assert rec is not None
    assert rec["recipient_id"] == 3
    assert rec["reason"] == "substantive"


def test_author_self_note_and_single_comment() -> None:
    rec = classify_thread([note(1, 1, "Rebased on main.")], 1, KINDS)
    assert rec is not None
    assert rec["reason"] == "author_self_note"
    assert rec["recipient_id"] is None
    single = classify_thread([note(1, 2, "This leaks memory.")], 1, KINDS)
    assert single is not None
    assert single["substantive"] == 1
    assert single["has_reply"] == 0


def test_routine_and_bot() -> None:
    rec = classify_thread([note(1, 2, "LGTM 👍"), note(2, 1, "Thanks!")], 1, KINDS)
    assert rec is not None
    assert rec["reason"] == "routine_only"
    bot = classify_thread([note(1, 9, "Pipeline passed")], 1, KINDS)
    assert bot is not None
    assert bot["reason"] == "bot_initiated"
    assert bot["giver_kind"] == "bot"


def test_deleted_user_counts_as_human_contribution() -> None:
    rec = classify_thread([note(1, None, "Handle 4K too?")], 1, KINDS)
    assert rec is not None
    assert rec["giver_kind"] == "deleted"
    assert rec["reason"] == "substantive"


def test_resolution_requires_all_resolvable_notes() -> None:
    partly = classify_thread(
        [note(1, 2, "x?", resolved=True, resolved_at="2026-01-05T00:00:00+00:00"), note(2, 1, "y")],
        1,
        KINDS,
    )
    assert partly is not None
    assert partly["resolved"] == 0
    assert partly["resolved_at"] is None
    full = classify_thread(
        [
            note(1, 2, "x?", resolved=True, resolved_at="2026-01-05T00:00:00+00:00"),
            note(2, 1, "y", resolvable=False),
        ],
        1,
        KINDS,
    )
    assert full is not None
    assert full["resolved"] == 1
    assert full["resolved_at"] == "2026-01-05T00:00:00+00:00"
    assert full["resolved_by_id"] == 2


def test_hash_changes_with_content() -> None:
    a = classify_thread([note(1, 2, "x")], 1, KINDS)
    b = classify_thread([note(1, 2, "y")], 1, KINDS)
    assert a is not None
    assert b is not None
    assert a["input_hash"] != b["input_hash"]


def test_bot_review_with_human_reply_is_substantive() -> None:
    rec = classify_thread(
        [note(1, 9, "Possible null dereference in parse()."), note(2, 1, "Fixed.")], 1, KINDS
    )
    assert rec is not None
    assert rec["reason"] == "bot_review"
    assert rec["substantive"] == 1
    assert rec["giver_kind"] == "bot"
    assert rec["recipient_id"] == 1
    silent = classify_thread([note(1, 9, "Pipeline report: 87 % coverage.")], 1, KINDS)
    assert silent is not None
    assert silent["reason"] == "bot_initiated"
    assert silent["substantive"] == 0


def test_old_classification_key_is_upgraded(tmp_path: object) -> None:
    from mrreview import db
    from mrreview.normalize import build_threads

    conn = db.connect(f"{tmp_path}/u.sqlite3")
    with db.tx(conn):
        conn.execute("INSERT INTO users VALUES (1,'a','A','human',NULL),(2,'b','B','human',NULL)")
        conn.execute("INSERT INTO merge_requests(project_id, iid, id, title, state, author_id, created_at, "
                     "updated_at, web_url, fetched_at) VALUES (1,1,1,'t','merged',1,'x','x','u','x')")
        conn.execute("INSERT INTO discussions VALUES ('d',1,1,0)")
        conn.execute("INSERT INTO notes(id, discussion_id, project_id, mr_iid, author_id, body, created_at, "
                     "system, resolvable, resolved) VALUES (1,'d',1,1,2,'Leak?','2026-01-01T00:00:00+00:00',0,1,0)")
    build_threads(conn)
    old_hash, llm_hash = conn.execute("SELECT input_hash, llm_hash FROM threads").fetchone()
    with db.tx(conn):
        conn.execute("INSERT INTO classifications(thread_id, input_hash, prompt_version, schema_version, "
                     "model, status, attempts, created_at) VALUES ('d', ?, 'p2', 's1', 'm', 'ok', 1, 'x')",
                     (old_hash,))
    build_threads(conn)
    assert conn.execute("SELECT input_hash FROM classifications").fetchone()[0] == llm_hash
    conn.close()
