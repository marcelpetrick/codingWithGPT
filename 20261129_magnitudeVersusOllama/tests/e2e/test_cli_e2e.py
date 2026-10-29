# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end: the CLI measures two arms on the fake engine, records a gate row, writes the report."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fake_engine import FakeEngine

from mvo import cli, dashboard
from mvo.report import _fmt, overall
from mvo.stats import Summary

ROOT = Path(__file__).resolve().parents[2]


def make_root(tmp_path: Path, url: str) -> Path:
    arms = {
        "arms": [
            {
                "label": "ollama-t",
                "engine": "ollama",
                "protocol": "ollama",
                "base_url": url,
                "version_url": url + "/api/version",
                "model": "m",
                "quant": "Q4",
                "drafter": "none",
                "family": "Fam",
                "note": "ollama note",
            },
            {
                "label": "ollama-other",
                "engine": "ollama",
                "protocol": "ollama",
                "base_url": url,
                "version_url": url + "/api/version",
                "model": "o",
                "quant": "Q4",
                "drafter": "none",
                "family": "Other",
                "note": "other family",
            },
            {
                "label": "magnitude-t",
                "engine": "magnitude",
                "protocol": "openai",
                "base_url": url + "/v1",
                "version_cmd": ["echo", "0.2.14"],
                "model": "m",
                "quant": "Q4",
                "drafter": "dflash",
                "family": "Fam",
                "note": "mag note",
            },
        ]
    }
    (tmp_path / "arms.json").write_text(json.dumps(arms))
    return tmp_path


def test_full_flow(fake: FakeEngine, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_root(tmp_path, fake.url)
    base = ["--root", str(root)]
    for label in ("ollama-t", "magnitude-t"):
        assert cli.main([*base, "run", "--arm", label, "--cells", "A:4096,B:1024,C:4096", "--reps", "5"]) == 0
    assert cli.main([*base, "run", "--arm", "ollama-other", "--cells", "B:1024", "--reps", "5"]) == 0
    assert cli.main([*base, "run", "--arm", "magnitude-t", "--cells", "V:4096", "--reps", "1"]) == 0
    assert (
        cli.main(
            [
                *base,
                "gate",
                "--site",
                "laptop",
                "--engine",
                "magnitude",
                "--model",
                "m",
                "--status",
                "loaded",
                "--detail",
                "ok",
            ]
        )
        == 0
    )
    assert cli.main([*base, "report"]) == 0
    md = (root / "report.md").read_text()
    page = (root / "dashboard.html").read_text()
    assert "magnitude-t vs ollama-t" in md
    assert "vs ollama-other" not in md  # another family never pairs
    assert "| laptop | Fam | V | 4096 | magnitude-t |" in md
    assert "| laptop | magnitude | m | loaded | ok |" in md
    assert "No verdict yet" not in md
    assert "Fam (laptop): Magnitude is not better" in md  # same fake speed -> tie
    assert "Other (laptop): no verdict yet" not in md  # no pair at all in that family
    assert "mag note" in page and "sortTable" in page
    assert 'class="bar s1"' in page and 'class="bar s2"' in page  # Magnitude+drafter blue, Ollama plain orange
    assert "Magnitude, with drafter" in page and "Tie under the rule" in page
    rows = (root / "results" / "laptop_magnitude-t.jsonl").read_text().splitlines()
    assert json.loads(rows[0])["engine_version"] == "0.2.14"
    assert "wrote" in capsys.readouterr().out


def test_cli_errors(fake: FakeEngine, tmp_path: Path) -> None:
    root = make_root(tmp_path, fake.url)
    base = ["--root", str(root)]
    assert cli.main([*base, "run", "--arm", "nope", "--cells", "A:4096"]) == 1
    assert cli.main([*base, "run", "--arm", "ollama-t", "--cells", "X:1"]) == 1
    fake.mode = "http500"
    # The warm-up gets HTTP 500: a defect of the engine, not a booked row.
    assert cli.main([*base, "run", "--arm", "magnitude-t", "--cells", "A:4096", "--reps", "1"]) == 2
    assert not (root / "results" / "laptop_magnitude-t.jsonl").exists()


def test_cli_failed_rows_exit_1(fake: FakeEngine, tmp_path: Path) -> None:
    root = make_root(tmp_path, fake.url)
    fake.mode = "thinking"
    assert cli.main(["--root", str(root), "run", "--arm", "ollama-t", "--cells", "A:4096", "--reps", "1"]) == 1


def test_cli_unreachable_exit_2(tmp_path: Path) -> None:
    root = make_root(tmp_path, "http://127.0.0.1:9")
    assert cli.main(["--root", str(root), "run", "--arm", "ollama-t", "--cells", "A:4096"]) == 2
    data = json.loads((root / "arms.json").read_text())
    data["arms"][1]["version_cmd"] = ["false"]
    (root / "arms.json").write_text(json.dumps(data))
    assert cli.main(["--root", str(root), "run", "--arm", "magnitude-t", "--cells", "A:4096"]) == 2


def test_dashboard_helpers() -> None:
    assert dashboard.role({"engine": "magnitude", "drafter": "none"}) == "magnitude-plain"
    assert dashboard.role({"engine": "ollama", "drafter": "MTP"}) == "ollama-draft"
    assert dashboard.gate_kind("loaded, 100% GPU") == "good"
    assert dashboard.gate_kind("refused: too large") == "critical"
    assert dashboard.gate_kind("blocked") == "warning"
    assert dashboard.bar_chart("t", "tok/s", []) == ""
    page = dashboard.table(
        "x", [{"status": "loaded", "decode_verdict": "b faster", "a": "1"}], ["status", "decode_verdict", "a"], {}
    )
    assert "chip good" in page and "chip critical" in page


def test_report_empty_and_helpers(tmp_path: Path) -> None:
    shutil.copy(ROOT / "arms.json", tmp_path / "arms.json")
    (tmp_path / "results").mkdir()
    assert cli.main(["--root", str(tmp_path), "report"]) == 0
    md = (tmp_path / "report.md").read_text()
    assert "No verdict yet" in md and "_No rows yet._" in md
    assert _fmt(Summary(0, 0, 0, 0)) == "–"
    fam = {"site": "s", "family": "F"}
    b_fast = {**fam, "workload": "B", "decode_verdict": "a faster"}
    c_tie = {**fam, "workload": "C", "decode_verdict": "quality: tie (10 vs 10)"}
    c_worse = {**fam, "workload": "C", "decode_verdict": "quality: b better (5 vs 15)"}
    assert overall([b_fast, c_tie]) == (
        "F (s): Magnitude is better: clearly faster on every B cell and not worse on quality."
    )
    assert "worse on quality" in overall([b_fast, c_worse])
    assert "no verdict yet" in overall([b_fast])
