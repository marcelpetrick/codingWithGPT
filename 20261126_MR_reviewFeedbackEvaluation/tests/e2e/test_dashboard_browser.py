# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end: build the demo through the CLI entry point, then use it in Chromium.

Covers REQ-UI-1 (offline), REQ-UI-3 (tooltips, drill-down, filters), REQ-UI-4 (numbers match the
Python metrics), REQ-UI-5 (identity toggle) and REQ-SEC-1 (no script injection).
"""

import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mrreview import dataset, db, metrics, report
from mrreview.config import Config
from mrreview.demo.fixture import HUMANS

pw = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any]]:
    out = tmp_path_factory.mktemp("demo")
    subprocess.run(
        [sys.executable, "-m", "mrreview", "demo", "--out", str(out)],
        check=True,
        capture_output=True,
        timeout=300,
    )
    conn = db.connect(out / "demo.sqlite3")
    ds = dataset.build_dataset(conn, Config())
    conn.close()
    return out / "dashboard.html", ds


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # pragma: no cover - depends on the machine
            pytest.skip(f"Chromium not available: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser: Any, built: tuple[Path, dict[str, Any]]) -> Iterator[Any]:
    ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
    pg = ctx.new_page()
    pg.requests = []  # type: ignore[attr-defined]
    pg.errors = []  # type: ignore[attr-defined]
    pg.on("request", lambda r: pg.requests.append(r.url))  # type: ignore[attr-defined]
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))  # type: ignore[attr-defined]
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)  # type: ignore[attr-defined]
    pg.goto(built[0].as_uri())
    pg.wait_for_selector(".kpi")
    yield pg
    ctx.close()


def tab(page: Any, name: str) -> None:
    page.get_by_role("tab", name=name).click()


def test_offline_and_no_errors(page: Any) -> None:
    for name in [
        "Projects",
        "Review effectiveness",
        "Participants",
        "Evidence",
        "Methodology",
        "Overview",
    ]:
        tab(page, name)
    assert all(u.startswith("file://") for u in page.requests)
    assert page.errors == []


def test_kpis_match_python_metrics(page: Any, built: tuple[Path, dict[str, Any]]) -> None:
    o = metrics.overview(built[1])
    kpi = lambda k: page.locator(f"[data-kpi={k}]")  # noqa: E731
    assert kpi("mrs").locator(".v").inner_text() == f"{o['mrs']:,}"
    assert kpi("findings").locator(".v").inner_text() == f"{o['findings']:,}"
    assert kpi("actionable").locator(".v").inner_text() == f"{o['actionable']:,}"
    vr = o["verified_rate"]
    assert kpi("verified").locator(".s").inner_text() == f"{vr['num']} of {vr['den']} actionable"
    assert kpi("open").locator(".v").inner_text() == str(o["unresolved"])
    assert kpi("rnc").locator(".v").inner_text() == str(o["resolved_without_code"])
    med = o["median_first_response_biz_h"]
    assert kpi("fr").locator(".v").inner_text() == (
        f"{med:.1f} h" if med < 10 else f"{round(med)} h"
    )


def visible_text(page: Any) -> str:
    return str(page.evaluate("document.body.innerText"))


def test_identity_toggle(page: Any) -> None:
    names = [h[2] for h in HUMANS]
    for name in ["Overview", "Participants", "Evidence"]:
        tab(page, name)
        assert not any(n in visible_text(page) for n in names), name
    page.locator("#names").check()
    text = visible_text(page)
    assert any(n in text for n in names)
    page.locator("#names").uncheck()
    assert not any(n in visible_text(page) for n in names)


def test_tooltips_everywhere(page: Any) -> None:
    for name in [
        "Overview",
        "Projects",
        "Review effectiveness",
        "Participants",
        "Evidence",
        "Methodology",
    ]:
        tab(page, name)
        missing = page.evaluate(
            """() => [...document.querySelectorAll('.kpi, th, .bar, .clue, .stack > div, svg circle, '
            + '.hist .col, .chip, .pchip, nav.tabs button, .legend .item, .tag')]
            .filter(e => !e.closest('[data-tip]')).map(e => e.className.baseVal ?? e.className)"""
        )
        assert missing == [], (name, missing[:5])
    tab(page, "Overview")
    page.locator(".kpi").first.hover()
    assert page.locator("#tip").is_visible()
    assert "MRs created" in page.locator("#tip").inner_text()


def test_clue_drills_into_evidence(page: Any, built: tuple[Path, dict[str, Any]]) -> None:
    clue = page.locator(".clue").first
    title = clue.locator(".t").inner_text()
    n = int(re.match(r"\d+", title).group(0))  # type: ignore[union-attr]
    clue.click()
    assert page.get_by_role("tab", name="Evidence").get_attribute("aria-selected") == "true"
    assert page.locator(".facet").count() == 1
    assert page.locator(".evtools .muted").inner_text() == f"{n} findings"


def test_project_filter_changes_numbers(page: Any, built: tuple[Path, dict[str, Any]]) -> None:
    ds = built[1]
    first = page.locator(".pchip").first
    path = first.inner_text()
    pid = next(p["id"] for p in ds["projects"] if p["label"] == path)
    first.click()
    remaining = sum(
        1 for f in ds["findings"] if next(t for t in ds["threads"] if t["id"] == f["t"])["p"] != pid
    )
    assert page.locator("[data-kpi=findings] .v").inner_text() == f"{remaining:,}"
    page.get_by_role("button", name="Reset").click()
    assert page.locator("[data-kpi=findings] .v").inner_text() == f"{len(ds['findings']):,}"


def test_evidence_search_and_detail(page: Any) -> None:
    tab(page, "Evidence")
    page.locator(".evtools input[type=search]").fill("EEPROM")
    rows = page.locator("tbody tr.click")
    assert rows.count() > 0
    rows.first.click()
    assert page.locator("tr.detail").count() == 1
    assert "Rationale" in page.locator("tr.detail").inner_text()
    link = page.locator("tbody tr.click a").first
    assert link.get_attribute("target") == "_blank"
    assert link.get_attribute("href").startswith("http://gitlab.invalid/")


def test_script_injection_stays_text(
    browser: Any, built: tuple[Path, dict[str, Any]], tmp_path: Path
) -> None:
    ds = json.loads(json.dumps(built[1]))
    evil = '<img src=x onerror="window.__pwned=1"></script><script>window.__pwned=2</script>'
    ds["threads"][0]["excerpt"] = evil
    for f in ds["findings"]:
        if f["t"] == ds["threads"][0]["id"]:
            f["summary"] = evil
    out = tmp_path / "evil.html"
    out.write_text(report.render_html(ds), encoding="utf-8")
    pg = browser.new_page()
    pg.goto(out.as_uri())
    pg.get_by_role("tab", name="Evidence").click()
    pg.locator(".evtools input[type=search]").fill("pwned")
    assert pg.evaluate("window.__pwned") is None
    assert "window.__pwned=1" in pg.locator("tbody").inner_text()
    pg.close()


def test_project_names_follow_the_toggle(page: Any, built: tuple[Path, dict[str, Any]]) -> None:
    paths = [p["path"] for p in built[1]["projects"]]
    for name in ["Overview", "Projects", "Evidence", "Methodology"]:
        tab(page, name)
        text = visible_text(page)
        assert not any(p in text for p in paths), name
    page.locator("#names").check()
    tab(page, "Projects")
    assert any(p in visible_text(page) for p in paths)
