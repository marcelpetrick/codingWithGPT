# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Integration tests: dataset export and HTML report (REQ-UI-*, REQ-SEC-1, REQ-DB-3)."""

import json
import re
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from mrreview import analyze, collect, dataset, evaluate, llm, metrics, normalize, report
from mrreview.config import Config
from mrreview.demo.fake_ollama import STUB_MODEL, FakeOllama, serve
from mrreview.demo.fixture import HUMANS, REFERENCE_NOW
from mrreview.http import UrllibTransport

from .conftest import Env


def pipeline(gl: Env, conn: sqlite3.Connection, limit: int | None = None) -> Config:
    cfg = replace(gl.cfg, ollama_model=STUB_MODEL)
    collect.run_collect(gl.client, conn, cfg, REFERENCE_NOW, max_projects=2)
    normalize.build_threads(conn)
    with serve(FakeOllama()) as url:
        analyze.run_analyze(conn, cfg, llm.OllamaClient(url, UrllibTransport()), limit=limit)
    evaluate.run_evaluate(conn, cfg)
    return cfg


def test_dataset_masks_names_in_text(gl: Env, conn: sqlite3.Connection) -> None:
    cfg = pipeline(gl, conn)
    ds = dataset.build_dataset(conn, cfg)
    text_fields = json.dumps(
        [
            [t["excerpt"] for t in ds["threads"]],
            [f["why"] for f in ds["findings"]],
            [m["title"] for m in ds["mrs"]],
        ],
        ensure_ascii=False,
    )
    for _, username, name in HUMANS:
        assert name not in text_fields
        assert "@" + username not in text_fields
    people = ds["people"]
    humans = [p for p in people.values() if p["kind"] == "human"]
    assert all(p["label"] and " " in p["label"] for p in humans)
    assert {p["name"] for p in humans} <= {h[2] for h in HUMANS}
    cov = ds["meta"]["coverage"]
    assert cov["state"] == "partial"
    assert cov["partial_reasons"] == [
        "bounded sample: --max-projects or --max-mrs limited the collection"
    ]
    assert ds["meta"]["stub"] is True
    assert all(t["url"].startswith("http") and "#note_" in t["url"] for t in ds["threads"])


def test_metrics_match_dataset(gl: Env, conn: sqlite3.Connection) -> None:
    cfg = pipeline(gl, conn)
    ds = dataset.build_dataset(conn, cfg)
    o = metrics.overview(ds)
    assert o["findings"] == len(ds["findings"])
    assert o["verified_rate"]["den"] == o["actionable"]
    assert 0 < o["verified_rate"]["num"] < o["actionable"]


def test_report_discloses_partial(gl: Env, conn: sqlite3.Connection) -> None:
    cfg = pipeline(gl, conn, limit=5)
    ds = dataset.build_dataset(conn, cfg)
    cov = ds["meta"]["coverage"]
    assert cov["complete"] is False
    assert cov["classification"]["pending"] > 0
    assert cov["classification"]["ok"] == 5


def test_stale_classification_is_reported(gl: Env, conn: sqlite3.Connection) -> None:
    cfg = pipeline(gl, conn)
    tid = conn.execute("SELECT id FROM threads WHERE substantive=1 LIMIT 1").fetchone()[0]
    conn.execute("UPDATE notes SET body = body || '!' WHERE discussion_id=?", (tid,))
    normalize.build_threads(conn)
    ds = dataset.build_dataset(conn, cfg)
    assert ds["meta"]["coverage"]["classification"]["stale"] == 1


def test_write_report_is_self_contained(gl: Env, conn: sqlite3.Connection, tmp_path: Path) -> None:
    cfg = pipeline(gl, conn)
    out = report.write_report(conn, cfg, tmp_path / "r" / "dash.html", demo=True)
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "Content-Security-Policy" in html
    assert not re.search(r"(src|href)=[\"']https?://", html)
    assert "@import" not in html
    assert html.count("<script") == 2
    assert not (tmp_path / "r" / "dash.html.tmp").exists()
    for _, _, name in HUMANS:
        assert html.count(name) <= 1  # only in the people map


def test_embed_json_cannot_break_out() -> None:
    evil = {"x": "</script><script>alert(1)</script> & \u2028 <!--"}
    text = report.embed_json(evil)
    assert "<" not in text
    assert ">" not in text
    assert "&" not in text
    assert "\u2028" not in text
    assert json.loads(text) == evil


def test_html_injection(tmp_path: Path) -> None:
    ds = {"meta": {}, "evil": "<img src=x onerror=alert(1)></script>"}
    html = report.render_html(ds, title="<b>t</b>")
    assert "<img src=x" not in html
    assert "<title>&lt;b&gt;t&lt;/b&gt;</title>" in html


def test_render_refuses_closing_tag_in_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    real = report._asset
    monkeypatch.setattr(report, "_asset", lambda n: "x</script>" if n.endswith(".js") else real(n))
    with pytest.raises(ValueError, match="closing tag"):
        report.render_html({})


def test_evaluate_counts_stub_outcomes(gl: Env, conn: sqlite3.Connection) -> None:
    cfg = pipeline(gl, conn)
    counts = evaluate.run_evaluate(conn, cfg)
    assert counts.get("implemented", 0) > 0
    assert counts.get("justified_no_change", 0) > 0
    assert Config().censor_days == 14


def test_dataset_has_recipient_reply_stats(gl: Env, conn: sqlite3.Connection) -> None:
    """REQ-UI-7: per thread, the recipient's own reply words and thanks, from the stored notes."""
    from mrreview.textutil import is_thanks, reply_words

    cfg = pipeline(gl, conn)
    ds = dataset.build_dataset(conn, cfg)
    checked = 0
    for t in ds["threads"]:
        first = conn.execute("SELECT first_note_id FROM threads WHERE id=?", (t["id"],)).fetchone()[
            0
        ]
        bodies = [
            b
            for (b,) in conn.execute(
                "SELECT body FROM notes WHERE discussion_id=? AND system=0 AND author_id=? "
                "AND id != ?",
                (t["id"], t["rec"], first),
            )
        ]
        if bodies:
            assert t["rw"] == sum(reply_words(b) for b in bodies)
            assert t["rthx"] is any(is_thanks(b) for b in bodies)
            checked += 1
        else:
            assert t["rw"] is None
            assert t["rthx"] is False
    assert checked > 10


def test_recipient_reply_stats_match_known_texts(gl: Env, conn: sqlite3.Connection) -> None:
    """Review 2026-11-27 finding 9: fixed inputs and expected values, not the production query."""
    cfg = pipeline(gl, conn)
    rows = conn.execute("""SELECT t.id, n.id FROM threads t JOIN notes n ON n.discussion_id = t.id
        WHERE n.system = 0 AND n.author_id = t.recipient_id AND n.id != t.first_note_id
        GROUP BY t.id HAVING count(*) = 1 ORDER BY t.id LIMIT 2""").fetchall()
    assert len(rows) == 2
    (t_thanks, n_thanks), (t_no, n_no) = rows
    with conn:
        conn.execute(
            "UPDATE notes SET body=? WHERE id=?", ("> quoted\nThanks, fixed it now.", n_thanks)
        )
        conn.execute("UPDATE notes SET body=? WHERE id=?", ("No thanks, this stays.", n_no))
    threads = {t["id"]: t for t in dataset.build_dataset(conn, cfg)["threads"]}
    assert (threads[t_thanks]["rw"], threads[t_thanks]["rthx"]) == (4, True)
    assert (threads[t_no]["rw"], threads[t_no]["rthx"]) == (4, False)


def test_share_report_holds_no_real_names_or_links(
    gl: Env, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """REQ-UI-9: the share build leaves real names, paths and links out of the file itself."""
    cfg = pipeline(gl, conn)
    path0 = conn.execute("SELECT path FROM projects ORDER BY id LIMIT 1").fetchone()[0]
    host = gl.url.split("//", 1)[1]
    with conn:
        conn.execute(
            "UPDATE notes SET body = body || ? WHERE id IN (SELECT first_note_id FROM threads LIMIT 5)",
            (
                f"\nlog: /builds/{path0}/x.c failed; git://git@{host}/{path0}.git; {host}; a.b@corp.example.org",
            ),
        )
    evaluate.run_evaluate(conn, cfg)
    out = report.write_report(conn, cfg, tmp_path / "share.html", share=True)
    html = out.read_text(encoding="utf-8")
    for _, username, name in HUMANS:
        assert name not in html
        assert username not in html
    for (path,) in conn.execute("SELECT path FROM projects"):
        assert path not in html
    assert gl.url.split("//", 1)[1] not in html
    assert "corp.example.org" not in html
    data = json.loads(
        re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S).group(1)
    )
    assert data["meta"]["share"] is True
    assert all(p["name"] == p["label"] for p in data["people"].values() if p["label"])
