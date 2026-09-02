#!/usr/bin/env python3
"""Entry point: survey the agent instruction files under a directory of repositories.

    ./run.py                      # scans ~/repos, writes out/report.html
    ./run.py /path/to/repos       # scans somewhere else
    ./run.py --llm ollama         # adds the cached semantic pass

Standard library only. No install step, no virtualenv, nothing to fetch.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentsmdsurvey.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
