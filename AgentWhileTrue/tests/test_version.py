"""The version string, the changelog and the packaging metadata must agree.

Every commit in this project bumps the version, so the cheapest way to keep that
promise honest is to fail the build when the changelog forgets.
"""

from __future__ import annotations

import re
from pathlib import Path

import agent_watch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _newest_changelog_version() -> str:
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^## \[(?P<version>[^\]]+)\]", changelog, flags=re.MULTILINE)
    assert match is not None, "CHANGELOG.md has no versioned section"
    return match.group("version")


def test_version_is_semver() -> None:
    assert SEMVER.match(agent_watch.__version__), agent_watch.__version__


def test_changelog_documents_current_version() -> None:
    assert _newest_changelog_version() == agent_watch.__version__


def test_pyproject_takes_version_from_the_package() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = { attr = "agent_watch.version.__version__" }' in pyproject
