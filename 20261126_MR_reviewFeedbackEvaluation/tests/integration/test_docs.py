# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Documents must not drift from the code (document review 2026-11-26)."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_version_badge_matches_pyproject() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"badge/version-{version}-" in readme


def test_test_names_in_documents_exist() -> None:
    defined = set()
    for path in (ROOT / "tests").rglob("test_*.py"):
        defined |= set(re.findall(r"^def (test_\w+)", path.read_text(encoding="utf-8"), re.M))
    for doc in ("docs/requirements.md", "docs/acceptance.md", "docs/review_20261126.md"):
        named = set(
            re.findall(r"`(?:[\w/.]+::)?(test_\w+)`", (ROOT / doc).read_text(encoding="utf-8"))
        )
        missing = named - defined
        assert not missing, (doc, sorted(missing))


def test_no_liquid_markers_in_markdown() -> None:
    for path in ROOT.rglob("*.md"):
        if ".venv" in path.parts or "mutants" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "{{" not in text, path
        assert "{%" not in text, path
