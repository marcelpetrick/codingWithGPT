"""Single source of truth for the project version.

``pyproject.toml`` reads ``__version__`` from here, the CLI reports it, and a
test asserts that the newest ``CHANGELOG.md`` heading matches it. Bumping this
string is therefore the only edit a release needs.
"""

from __future__ import annotations

__version__ = "0.4.0"

__all__ = ["__version__"]
